"""Recherche et parcours sur des sites sans préfixe de recherche yt-dlp (france.tv, Arte).

La recherche intégrée de DownAccess repose sur les préfixes yt-dlp
(``ytsearch:``, ``scsearch:``). france.tv et Arte n'en ont pas : on interroge
ici directement leurs API HTTP publiques, puis on normalise les résultats au
même format que les entrées yt-dlp (clés ``title``, ``id``, ``duration``,
``uploader``/``channel``, ``webpage_url``, ``_dl_type``) pour réutiliser tel
quel ``SearchResultsDialog``.

Deux modes :
- ``search(...)``  : recherche par mots-clés ;
- ``browse(...)``  : parcours d'une catégorie, sans mots-clés (demande
  utilisateur : « parcourir sans être obligée de rechercher une émission bien
  précise »). Les catégories disponibles sont données par ``categories()``.

Chaque entrée porte un résumé (``_summary``) quand le site en fournit un — les
deux API le renvoient dans la réponse de recherche, sans requête supplémentaire.

Les URL renvoyées sont des pages ``france.tv``/``arte.tv`` : elles retombent
dans le flux « sites personnalisés » (``custom_sites.is_custom_site_url`` →
choix de piste audio français / audiodescription).

Aucun `import wx` ici (règle app/core).
"""

import html
import re
import time
import unicodedata

from curl_cffi import requests as cffi_requests

from app.core.i18n import _translate as _


# Endpoints (vérifiés en conditions réelles, août 2026).
_FRANCETV_SEARCH_URL = "https://api-mobile.yatta.francetv.fr/apps/search"
_FRANCETV_CATEGORY_URL = "https://api-mobile.yatta.francetv.fr/apps/categories/{slug}"
# Arte : API "web" (api.arte.tv) — pas de jeton requis, contrairement à l'API "app".
_ARTE_PAGE_URL = "https://api.arte.tv/api/emac/v4/{lang}/web/pages/{code}/"
_ARTE_COLLECTION_URL = "https://api.arte.tv/api/emac/v4/{lang}/web/collections/{code}/"
# API « programmes » : la seule qui renvoie TOUTE la liste d'une collection
# (celle-la meme que yt-dlp utilise pour construire la playlist), mais elle
# exige un jeton — cf. `_arte_api_token`.
_ARTE_PROGRAM_URL = "https://api.arte.tv/api/opa/v3/programs/{lang}/{code}"
_ARTE_LANGS = ("fr", "de", "en", "es", "it", "pl")

_TIMEOUT = 20

# Parcours d'une categorie : nombre de requetes de pagination en plus de la
# page elle-meme. Sans elles, « Culture pop » et « Jeunesse » ne montraient que
# DIX videos sur 200 et 172 — leur page ne contient qu'un seul rail, pagine.
_ARTE_BROWSE_MAX_PAGES = 8

# Le catalogue d'une categorie ne bouge pas d'une minute a l'autre, et
# l'utilisateur qui feuillette les pages de resultats redemande la meme liste a
# chaque fois. On la garde en memoire quelques minutes.
_BROWSE_TTL = 300.0
_browse_cache: dict[tuple[str, str, str], tuple[float, list[dict]]] = {}


def clear_browse_cache() -> None:
    """Vide le cache de parcours (tests, changement de langue)."""
    _browse_cache.clear()


# --- Catégories de parcours --------------------------------------------------
#
# Codes/slugs verifies un par un : ceux qui repondent 200 mais ne contiennent
# aucun element (france.tv : info-et-societe, jeunesse, divertissements,
# vie-quotidienne) sont volontairement ABSENTS, sinon l'utilisateur choisit une
# categorie et tombe sur une liste vide.

def _arte_categories() -> list[tuple[str, str]]:
    return [
        ("DOR", _("Documentaires")),
        ("CIN", _("Films")),
        ("SER", _("Séries et fictions")),
        ("ACT", _("Actualités et société")),
        ("SCI", _("Sciences")),
        ("HIS", _("Histoire")),
        ("EMI", _("Émissions")),
        # Le catalogue musical d'Arte (ARTE Concert) n'est pas une categorie du
        # site mais une page a part entiere — d'ou le code different. C'est la
        # que vivent les festivals (Cabaret Vert, Eurockeennes...).
        ("ARTE_CONCERT", _("Concerts et spectacles")),
        ("POP", _("Culture pop")),
        ("JUN", _("Jeunesse")),
    ]


def _francetv_categories() -> list[tuple[str, str]]:
    return [
        ("documentaires", _("Documentaires")),
        ("films", _("Cinéma")),
        ("series-et-fictions", _("Séries et fictions")),
        ("spectacles-et-culture", _("Arts et spectacles")),
        ("sport", _("Sport")),
    ]


def categories(site_key: str) -> list[tuple[str, str]]:
    """Catégories parcourables d'un site : [(code, libellé), ...].

    Liste vide si le site ne supporte pas le parcours (recherche seule).
    """
    if site_key == "arte":
        return _arte_categories()
    if site_key == "francetv":
        return _francetv_categories()
    return []


def supports_browse(site_key: str) -> bool:
    return bool(categories(site_key))


# --- Nettoyage ---------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_summary(text) -> str:
    """Resume en texte brut : france.tv renvoie du HTML (``<p>...</p>``)."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", str(text))
    text = html.unescape(text)
    # \xa0 (espace insecable) est frequent chez Arte et gene la lecture NVDA.
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _slugify(text: str) -> str:
    """Slug ASCII minimal pour l'URL france.tv (la valeur exacte est ignorée
    par le site, seul le chemin du programme + l'id numérique comptent)."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "video"


def _page_slice(entries: list[dict], page: int, limit: int) -> dict:
    """Decoupe cote client une liste complete en pages de `limit` elements."""
    total = len(entries)
    total_pages = max(1, (total + limit - 1) // limit)
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    return {
        "entries": entries[start:start + limit],
        "page": page,
        "total_pages": total_pages,
        "total_count": total,
    }


# --- API publique ------------------------------------------------------------

def search(site_key: str, query: str, limit: int, lang: str, page: int = 1) -> dict:
    """Recherche par mots-clés.

    Retourne ``{"entries": [...], "page": n, "total_pages": n, "total_count": n}``.
    ``total_pages`` vaut 1 quand le site ne rend qu'un seul lot (france.tv).
    """
    query = (query or "").strip()
    if not query:
        return {"entries": [], "page": 1, "total_pages": 1, "total_count": 0}
    if site_key == "francetv":
        return _page_slice(_francetv_search_all(query), page, limit)
    if site_key == "arte":
        return _arte_search(query, limit, lang, page)
    return {"entries": [], "page": 1, "total_pages": 1, "total_count": 0}


def browse(site_key: str, category: str, limit: int, lang: str, page: int = 1) -> dict:
    """Parcours d'une catégorie, sans mots-clés. Même format de retour que
    ``search``. Les deux sites renvoient tout leur catalogue de catégorie en
    une requête : la pagination est donc faite côté client."""
    if not category:
        return {"entries": [], "page": 1, "total_pages": 1, "total_count": 0}
    if site_key not in ("francetv", "arte"):
        return {"entries": [], "page": 1, "total_pages": 1, "total_count": 0}
    return _page_slice(_browse_all_cached(site_key, category, lang), page, limit)


def _browse_all_cached(site_key: str, category: str, lang: str) -> list[dict]:
    """Catalogue complet d'une categorie, garde quelques minutes.

    Chaque changement de page redemandait tout le catalogue au site : une
    requete pour france.tv, jusqu'a neuf pour Arte depuis qu'on suit la
    pagination des rails. Le cache rend le feuilletage instantane.
    """
    cle = (site_key, category, lang)
    maintenant = time.monotonic()
    garde = _browse_cache.get(cle)
    if garde and maintenant - garde[0] < _BROWSE_TTL:
        return garde[1]
    entries = (_francetv_browse_all(category) if site_key == "francetv"
               else _arte_browse_all(category, lang))
    if len(_browse_cache) >= 12:      # une poignee de categories suffit
        _browse_cache.pop(next(iter(_browse_cache)), None)
    _browse_cache[cle] = (maintenant, entries)
    return entries


# --- france.tv ---------------------------------------------------------------

def _francetv_entry(item: dict) -> dict | None:
    """Normalise un element france.tv, ou None s'il n'est pas telechargeable."""
    vid_id = item.get("id")
    si_id = item.get("si_id")
    if not vid_id and not si_id:
        return None
    program = item.get("program") or {}
    program_path = program.get("program_path") or ""
    title = item.get("title") or item.get("episode_title") or program.get("label") or "?"

    if program_path and vid_id:
        # URL web réelle : la slug est ignorée par france.tv, seuls le chemin du
        # programme et l'id numérique sont déterminants.
        url = f"https://www.france.tv/{program_path.replace('_', '/')}/{vid_id}-{_slugify(title)}.html"
    elif si_id:
        # Repli : schéma interne yt-dlp (toujours téléchargeable).
        url = f"francetv:{si_id}"
    else:
        return None

    return {
        "title": title,
        "id": str(si_id or vid_id),
        "duration": item.get("duration"),
        "uploader": program.get("label") or item.get("offer") or "france.tv",
        "webpage_url": url,
        "_dl_type": "video",
        "_has_ad": bool(item.get("is_audio_descripted")),
        "_summary": _clean_summary(
            item.get("description")
            or item.get("medium_description")
            or item.get("intro")
        ),
    }


def _francetv_search_all(query: str) -> list[dict]:
    """Recherche france.tv via l'API mobile (collection « Vidéos »).

    Seules les vidéos directement téléchargeables (type ``playlist_video``)
    sont retournées : yt-dlp ne sait pas extraire une page de programme
    (série) france.tv, on n'expose donc pas les programmes/collections.

    L'API ne pagine pas (``page``/``offset`` sont ignorés, verifie) : elle
    renvoie un lot unique d'une vingtaine de resultats.
    """
    resp = cffi_requests.get(
        _FRANCETV_SEARCH_URL,
        params={"platform": "apps", "filters": "with-collections", "term": query},
        impersonate="chrome",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    entries: list[dict] = []
    for collection in data.get("collections", []):
        if collection.get("type") != "playlist_video":
            continue
        for item in collection.get("items", []):
            entry = _francetv_entry(item)
            if entry:
                entries.append(entry)
    return entries


# Types d'elements france.tv correspondant a une video telechargeable. Les
# `collection` / `program` sont des pages de programme (yt-dlp ne sait pas les
# extraire) et `sous_categorie` est un element de navigation : on les ecarte.
_FRANCETV_VIDEO_TYPES = ("integrale", "unitaire", "extrait")


def _francetv_browse_all(slug: str) -> list[dict]:
    """Toutes les vidéos d'une catégorie france.tv (une seule requête)."""
    resp = cffi_requests.get(
        _FRANCETV_CATEGORY_URL.format(slug=slug),
        params={"platform": "apps"},
        impersonate="chrome",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    entries: list[dict] = []
    seen: set[str] = set()
    for collection in data.get("collections", []):
        for item in collection.get("items", []):
            if item.get("type") not in _FRANCETV_VIDEO_TYPES:
                continue
            entry = _francetv_entry(item)
            # Les rails editoriaux se recoupent : dedoublonner sur l'id.
            if entry and entry["id"] not in seen:
                seen.add(entry["id"])
                entries.append(entry)
    return entries


# --- Arte --------------------------------------------------------------------

def _arte_lang(lang: str) -> str:
    return lang if lang in _ARTE_LANGS else "fr"


def _arte_entry(item: dict) -> dict | None:
    """Normalise un element Arte, ou None si ce n'est pas un contenu telechargeable.

    Les pages de categorie melangent du contenu et des tuiles de NAVIGATION
    (« Histoire », « Sciences »...) : ces dernieres portent kind EXTERNAL et
    pointent vers une page de listing (``/fr/videos/histoire/``), pas vers un
    programme. Les proposer donnerait des lignes sans duree ni resume qui
    echouent au telechargement. Kinds reels du contenu : SHOW (programme),
    TV_SERIES et TOPIC (collections, developpees en playlist par yt-dlp).
    """
    url = item.get("url")
    if not url or "arte.tv" not in str(url):
        return None  # liens hors arte.tv
    kind = item.get("kind") or {}
    if kind.get("code") == "EXTERNAL":
        return None
    title = item.get("title") or "?"
    subtitle = item.get("subtitle")
    return {
        "title": f"{title} — {subtitle}" if subtitle else title,
        "id": str(item.get("id") or url),
        "duration": item.get("duration"),
        "uploader": "Arte",
        "webpage_url": url,
        "_dl_type": "playlist" if kind.get("isCollection") else "video",
        "_summary": _clean_summary(
            item.get("shortDescription") or item.get("teaserText")
        ),
    }


# Collections Arte (« RC-014468 ») : yt-dlp developpe la page en playlist mais
# ne donne AUCUN titre a ses entrees (`url_result` nu) — la fenetre de playlist
# n'avait que l'URL a afficher. L'API EMAC, elle, decrit chaque video.
_ARTE_COLLECTION_RE = re.compile(
    r"arte\.tv/(?P<lang>[a-z]{2})/videos/(?P<code>RC-\d{6})", re.I)
# Un identifiant de video Arte (« 133232-001-A ») : cle de rapprochement entre
# les entrees yt-dlp et celles de l'API, insensible a la langue et au slug.
_ARTE_VIDEO_ID_RE = re.compile(r"/videos/(\d{6}-\d{3}-[A-Z])", re.I)
# Garde-fou : une grande collection empile beaucoup de rails paginés. On borne
# le nombre de requetes pour ne pas faire attendre l'utilisateur.
_ARTE_COLLECTION_MAX_PAGES = 8


def arte_collection_id(url: str) -> tuple[str, str] | None:
    """(langue, code) si l'URL est une collection Arte, sinon None."""
    match = _ARTE_COLLECTION_RE.search(url or "")
    if not match:
        return None
    return _arte_lang(match["lang"].lower()), match["code"].upper()


def arte_video_id(url: str) -> str:
    """Identifiant de la video dans une URL Arte, ou chaine vide."""
    match = _ARTE_VIDEO_ID_RE.search(url or "")
    return match[1].upper() if match else ""


def _arte_api_token() -> str:
    """Jeton de l'API « programmes » d'Arte, emprunte a yt-dlp.

    Arte exige un Bearer sur cette API. Plutot que de figer le jeton ici — ou
    il vieillirait entre deux versions de DownAccess — on lit celui de yt-dlp,
    dont l'extracteur de collections se sert deja. DownAccess suit le canal
    nightly et met yt-dlp a jour tout seul : le jour ou Arte le renouvelle, le
    notre suit sans qu'on ait rien a publier. Et si Arte le revoquait sans
    prevenir, yt-dlp ne saurait de toute facon plus lister la collection.
    """
    try:
        from yt_dlp.extractor.arte import ArteTVPlaylistIE
        return getattr(ArteTVPlaylistIE, "_API_TOKEN", "") or ""
    except Exception:
        return ""


def _arte_program_entry(item: dict) -> dict | None:
    """Normalise une video de l'API programmes (forme differente de l'API web)."""
    url = item.get("url")
    if not url or item.get("kind") != "SHOW":
        return None
    title = item.get("title") or "?"
    subtitle = item.get("subtitle")
    duree = item.get("durationSeconds")
    return {
        "title": f"{title} — {subtitle}" if subtitle else title,
        "id": str(item.get("programId") or item.get("id") or url),
        "duration": int(duree) if str(duree or "").isdigit() else None,
        "uploader": "Arte",
        "webpage_url": url,
        "_dl_type": "video",
        "_summary": _clean_summary(item.get("shortDescription")),
    }


def arte_program_entries(url: str) -> list[dict]:
    """Videos d'une collection Arte via l'API programmes — liste COMPLETE.

    C'est la source de yt-dlp lui-meme : les entrees se rapprochent donc une a
    une, sans trou, quelle que soit la taille de la collection. Renvoie une
    liste vide (jamais d'exception) si le jeton manque ou si l'API refuse :
    l'appelant se rabat alors sur l'API web.
    """
    ident = arte_collection_id(url)
    token = _arte_api_token()
    if not ident or not token:
        return []
    lang, code = ident
    try:
        resp = cffi_requests.get(
            _ARTE_PROGRAM_URL.format(lang=lang, code=code),
            headers={"Authorization": f"Bearer {token}"},
            impersonate="chrome",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        programs = (resp.json() or {}).get("programs") or []
    except Exception:
        return []
    videos = (programs[0] if programs else {}).get("videos") or []
    return [e for e in (_arte_program_entry(v) for v in videos) if e]


def arte_collection_entries(url: str) -> list[dict]:
    """Videos d'une collection Arte, pour nommer les entrees d'une playlist.

    Deux sources, dans cet ordre :
    1. l'API « programmes » (`arte_program_entries`), qui renvoie la collection
       entiere — c'est celle que yt-dlp interroge pour construire la liste ;
    2. a defaut, l'API web des collections, sans jeton, mais qui n'expose que
       la mise en page du site : les episodes recents et quelques rails. Sur un
       magazine d'archives elle n'en couvre qu'une partie (mesure : 51 des 100
       emissions d'ARTE Reportage), l'appelant garde alors ses entrees non
       decrites.

    Meme normalisation que la recherche des deux cotes : le libelle affiche est
    le meme que dans la liste de resultats.
    """
    completes = arte_program_entries(url)
    if completes:
        return completes
    ident = arte_collection_id(url)
    if not ident:
        return []
    lang, code = ident
    resp = cffi_requests.get(
        _ARTE_COLLECTION_URL.format(lang=lang, code=code),
        impersonate="chrome",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    entries: list[dict] = []
    seen: set[str] = set()

    def _collect(items: list[dict]) -> None:
        for item in items:
            entry = _arte_entry(item)
            if entry and entry["id"] not in seen:
                seen.add(entry["id"])
                entries.append(entry)

    requests_left = _ARTE_COLLECTION_MAX_PAGES
    for zone in data.get("zones", []):
        content = zone.get("content") or {}
        _collect(content.get("data") or [])
        pagination = content.get("pagination") or {}
        next_url = (pagination.get("links") or {}).get("next") or ""
        pages = int(pagination.get("pages") or 1)
        page = 2
        while next_url and page <= pages and requests_left > 0:
            requests_left -= 1
            zone_url = re.sub(r"([?&]page=)\d+", rf"\g<1>{page}", next_url)
            try:
                more = cffi_requests.get(zone_url, impersonate="chrome",
                                         timeout=_TIMEOUT)
                more.raise_for_status()
                _collect((more.json() or {}).get("data") or [])
            except Exception:
                break   # une page manquante ne doit pas perdre les precedentes
            page += 1
    return entries


def _arte_zone_items(zone: dict) -> list[dict]:
    return (zone.get("content") or {}).get("data") or []


def _arte_search(query: str, limit: int, lang: str, page: int) -> dict:
    """Recherche Arte via l'API web EMAC v4 (zone « listing_SEARCH »).

    Les collections (séries, magazines) sont incluses : leur URL est une page
    arte.tv que yt-dlp développe en playlist. Les vidéos unitaires gardent le
    flux normal (choix de piste audio).

    Pagination : le parametre `page` de l'URL de PAGE est ignore (verifie :
    page 1 et page 2 renvoient le meme lot). La vraie pagination passe par
    l'URL de contenu de ZONE, publiee dans le bloc `pagination` de la reponse
    (jusqu'a 20 pages / 400 resultats). On lit donc la page 1 pour obtenir cette
    URL, puis on la suit pour les pages suivantes.
    """
    arte_lang = _arte_lang(lang)
    resp = cffi_requests.get(
        _ARTE_PAGE_URL.format(lang=arte_lang, code="SEARCH"),
        params={"query": query, "page": 1, "limit": max(limit, 10)},
        impersonate="chrome",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    content = {}
    for zone in data.get("zones", []):
        if zone.get("code") == "listing_SEARCH":
            content = zone.get("content") or {}
            break

    pagination = content.get("pagination") or {}
    total_pages = max(1, int(pagination.get("pages") or 1))
    total_count = int(pagination.get("totalCount") or 0)
    page = max(1, min(page, total_pages))

    items = content.get("data") or []
    if page > 1:
        next_url = ((pagination.get("links") or {}).get("next") or "")
        if not next_url:
            return {"entries": [], "page": 1, "total_pages": 1, "total_count": total_count}
        # `next` pointe sur la page 2 : on remplace le numero pour viser `page`.
        zone_url = re.sub(r"([?&]page=)\d+", rf"\g<1>{page}", next_url)
        resp2 = cffi_requests.get(zone_url, impersonate="chrome", timeout=_TIMEOUT)
        resp2.raise_for_status()
        items = (resp2.json() or {}).get("data") or []

    entries = [e for e in (_arte_entry(i) for i in items) if e][:limit]
    return {
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count,
    }


def _arte_browse_all(code: str, lang: str) -> list[dict]:
    """Toutes les vidéos d'une page de catégorie Arte.

    Une page de categorie est un empilement de rails editoriaux (« À ne pas
    manquer », « Comédie », « Portraits de femmes »...). On aplatit tous les
    rails en une liste unique, dedoublonnee : l'utilisateur veut parcourir le
    catalogue, pas la mise en page du site.
    """
    resp = cffi_requests.get(
        _ARTE_PAGE_URL.format(lang=_arte_lang(lang), code=code),
        impersonate="chrome",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    entries: list[dict] = []
    seen: set[str] = set()

    def _collect(items: list[dict]) -> None:
        for item in items:
            entry = _arte_entry(item)
            if entry and entry["id"] not in seen:
                seen.add(entry["id"])
                entries.append(entry)

    # Les rails paginés, du plus gros au plus petit : sur « Culture pop » une
    # seule zone porte les 200 vidéos de la catégorie quand les autres n'en
    # portent que dix. On dépense le budget de requêtes là où il rapporte.
    a_paginer: list[tuple[int, str, int]] = []
    for zone in data.get("zones", []):
        content = zone.get("content") or {}
        _collect(_arte_zone_items(zone))
        pagination = content.get("pagination") or {}
        next_url = (pagination.get("links") or {}).get("next") or ""
        pages = int(pagination.get("pages") or 1)
        if next_url and pages > 1:
            a_paginer.append((int(pagination.get("totalCount") or 0), next_url, pages))
    a_paginer.sort(key=lambda z: z[0], reverse=True)

    budget = _ARTE_BROWSE_MAX_PAGES
    for _total, next_url, pages in a_paginer:
        page = 2
        while page <= pages and budget > 0:
            budget -= 1
            zone_url = re.sub(r"([?&]page=)\d+", rf"\g<1>{page}", next_url)
            try:
                more = cffi_requests.get(zone_url, impersonate="chrome",
                                         timeout=_TIMEOUT)
                more.raise_for_status()
                _collect((more.json() or {}).get("data") or [])
            except Exception:
                break   # une page manquante ne doit pas perdre les precedentes
            page += 1
        if budget <= 0:
            break
    return entries
