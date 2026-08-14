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
import unicodedata

from curl_cffi import requests as cffi_requests

from app.core.i18n import _translate as _


# Endpoints (vérifiés en conditions réelles, août 2026).
_FRANCETV_SEARCH_URL = "https://api-mobile.yatta.francetv.fr/apps/search"
_FRANCETV_CATEGORY_URL = "https://api-mobile.yatta.francetv.fr/apps/categories/{slug}"
# Arte : API "web" (api.arte.tv) — pas de jeton requis, contrairement à l'API "app".
_ARTE_PAGE_URL = "https://api.arte.tv/api/emac/v4/{lang}/web/pages/{code}/"
_ARTE_LANGS = ("fr", "de", "en", "es", "it", "pl")

_TIMEOUT = 20


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
    if site_key == "francetv":
        return _page_slice(_francetv_browse_all(category), page, limit)
    if site_key == "arte":
        return _page_slice(_arte_browse_all(category, lang), page, limit)
    return {"entries": [], "page": 1, "total_pages": 1, "total_count": 0}


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
    for zone in data.get("zones", []):
        for item in _arte_zone_items(zone):
            entry = _arte_entry(item)
            if entry and entry["id"] not in seen:
                seen.add(entry["id"])
                entries.append(entry)
    return entries
