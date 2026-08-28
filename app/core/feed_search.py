"""Chercher une source a suivre par son nom, plutot que par son adresse.

S'abonner demandait jusqu'ici de connaitre l'adresse du flux. Trouver celle
d'une chaine YouTube se devine encore ; celle d'un podcast, non — et c'est
precisement ce qu'une personne aveugle ne peut pas aller pecher au fond d'une
page (remarque de Veronique, 2026-08-28). On cherche donc par mots-cles, comme
pour telecharger un media, et l'adresse est resolue toute seule.

Trois sources, choisies parce que `subscriptions.resolve_feed` sait deja les
suivre : les chaines YouTube (flux Atom), les collections Arte (API), les
podcasts (flux RSS). france.tv n'expose rien de suivable : il n'est pas propose.

**Le flux d'un podcast n'est pas dans l'API d'Apple.** Le champ `feedUrl` de
`itunes.apple.com/search` est vide pour une bonne partie du catalogue francais
(mesure du 2026-08-28 : Affaires sensibles, La Terre au carre, La Science CQFD
— l'endpoint `lookup` ne le donne pas davantage). Il figure en revanche dans la
page publique du podcast, d'ou les agregateurs le tirent. On garde donc Apple
pour ce qu'il fait de mieux — trouver et classer — et on ne va chercher
l'adresse qu'au moment ou l'utilisateur choisit un podcast : une seule page
lue, pour le seul podcast retenu.
"""

import json
import re
import urllib.parse
import urllib.request

from app.core.i18n import _translate as _

# Sources proposees : (code interne, libelle affiche construit paresseusement).
SOURCE_YOUTUBE = "youtube"
SOURCE_ARTE    = "arte"
SOURCE_PODCAST = "podcast"

SOURCE_CODES = [SOURCE_YOUTUBE, SOURCE_ARTE, SOURCE_PODCAST]

# Filtre « chaines » de la page de resultats YouTube. Meme mecanique que le
# filtre de type de la recherche de medias : c'est le seul moyen d'obtenir des
# chaines et non des videos.
_YT_CHANNELS_SP = "EgIQAg%3D%3D"

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")

_TIMEOUT = 20
# La page d'un podcast Apple pese pres d'un mega-octet : on borne la lecture
# pour qu'une page anormale ne fasse pas gonfler la memoire.
_MAX_PAGE_BYTES = 4 * 1024 * 1024

_APPLE_FEED_RE = re.compile(r'"feedUrl"\s*:\s*"([^"]+)"')


class SearchError(Exception):
    """Recherche impossible — message deja redige pour l'utilisateur."""


def source_labels() -> list[str]:
    """Libelles des sources, dans l'ordre de `SOURCE_CODES`."""
    return [
        _("Chaînes YouTube"),
        _("Collections Arte"),
        _("Podcasts"),
    ]


def search(source: str, query: str, limit: int = 20) -> list[dict]:
    """Cherche des sources a suivre.

    Retourne une liste de dictionnaires :
    ``{"title", "author", "detail", "url", "source"}``. ``url`` peut etre vide
    (podcasts) : l'adresse est alors resolue par `resolve` au moment du choix.
    """
    query = (query or "").strip()
    if not query:
        return []
    if source == SOURCE_YOUTUBE:
        return _search_youtube(query, limit)
    if source == SOURCE_ARTE:
        return _search_arte(query, limit)
    if source == SOURCE_PODCAST:
        return _search_podcasts(query, limit)
    return []


def resolve(entry: dict) -> str:
    """Adresse a suivre pour un resultat choisi.

    Immediate pour YouTube et Arte (l'adresse de la page suffit,
    `subscriptions.resolve_feed` en deduit le flux). Pour un podcast, va lire
    l'adresse du flux — appel reseau, donc a faire dans un thread de travail.
    """
    if entry.get("url"):
        return entry["url"]
    if entry.get("source") == SOURCE_PODCAST:
        return _podcast_feed_url(entry)
    raise SearchError(_("Cette source ne peut pas être suivie."))


# ------------------------------------------------------------------
# YouTube
# ------------------------------------------------------------------

def _search_youtube(query: str, limit: int) -> list[dict]:
    import yt_dlp

    url = "https://www.youtube.com/results?" + urllib.parse.urlencode(
        {"search_query": query, "sp": _YT_CHANNELS_SP})
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
            "skip_download": True, "playlistend": limit}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise SearchError(_("La recherche a échoué : {error}").format(
            error=exc)) from exc

    resultats = []
    for entry in (info.get("entries") or []) if info else []:
        if not entry or not entry.get("url"):
            continue
        resultats.append({
            "title":  entry.get("title") or entry.get("channel") or "?",
            "author": entry.get("uploader") or entry.get("channel") or "",
            "detail": _subscribers_label(entry.get("channel_follower_count")),
            "url":    entry["url"],
            "source": SOURCE_YOUTUBE,
        })
    return resultats[:limit]


def _subscribers_label(count) -> str:
    """« 5 020 000 abonnés » — de quoi distinguer la vraie chaine des copies."""
    try:
        n = int(count or 0)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    nombre = f"{n:,}".replace(",", " ")
    if n == 1:
        return _("{n} abonné").format(n=nombre)
    return _("{n} abonnés").format(n=nombre)


# ------------------------------------------------------------------
# Arte
# ------------------------------------------------------------------

def _search_arte(query: str, limit: int) -> list[dict]:
    """Collections Arte uniquement : une video seule ne se suit pas."""
    from app.core import i18n, site_search

    lang = i18n.get_current_language_code()
    try:
        brut = site_search.search("arte", query, max(limit, 20), lang, 1)
    except Exception as exc:
        raise SearchError(_("La recherche a échoué : {error}").format(
            error=exc)) from exc

    resultats = []
    for entry in brut.get("entries") or []:
        if entry.get("_dl_type") != "playlist" or not entry.get("webpage_url"):
            continue
        resultats.append({
            "title":  entry.get("title") or "?",
            "author": "Arte",
            "detail": (entry.get("_summary") or "").split("\n")[0][:120],
            "url":    entry["webpage_url"],
            "source": SOURCE_ARTE,
        })
    return resultats[:limit]


# ------------------------------------------------------------------
# Podcasts
# ------------------------------------------------------------------

def _search_podcasts(query: str, limit: int) -> list[dict]:
    from app.core import i18n

    pays = "FR" if i18n.get_current_language_code() == "fr" else "US"
    params = urllib.parse.urlencode({
        "media": "podcast", "term": query, "limit": min(limit, 25),
        "country": pays,
    })
    donnees = _json_get("https://itunes.apple.com/search?" + params)

    resultats = []
    for item in donnees.get("results") or []:
        titre = item.get("collectionName") or item.get("trackName")
        if not titre:
            continue
        resultats.append({
            "title":  titre,
            "author": item.get("artistName") or "",
            "detail": _episodes_label(item.get("trackCount")),
            # Vide a dessein : resolu au choix (cf. l'en-tete du module).
            "url":    item.get("feedUrl") or "",
            "source": SOURCE_PODCAST,
            "_apple_id":   item.get("collectionId"),
            "_apple_page": item.get("collectionViewUrl") or "",
        })
    return resultats[:limit]


def _episodes_label(count) -> str:
    try:
        n = int(count or 0)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    if n == 1:
        return _("{n} épisode").format(n=n)
    return _("{n} épisodes").format(n=n)


def _podcast_feed_url(entry: dict) -> str:
    """Adresse du flux d'un podcast, lue dans sa page publique.

    La page liste aussi des podcasts suggeres, chacun avec son propre
    `feedUrl` : on ne prend donc pas le premier venu, mais celui du bloc qui
    porte l'identifiant du podcast choisi.
    """
    page_url = entry.get("_apple_page") or ""
    apple_id = entry.get("_apple_id")
    if not page_url or not apple_id:
        raise SearchError(_("L'adresse de ce podcast est introuvable."))

    html = _text_get(page_url)
    motif = rf'"id"\s*:\s*"?{re.escape(str(apple_id))}"?'
    for marque in re.finditer(motif, html):
        fenetre = html[marque.start():marque.start() + 4000]
        trouve = _APPLE_FEED_RE.search(fenetre)
        if trouve:
            return trouve.group(1).replace("\\/", "/")

    raise SearchError(_(
        "L'adresse du flux de ce podcast n'a pas pu être trouvée. Vous pouvez "
        "la saisir vous-même si vous la connaissez."))


# ------------------------------------------------------------------
# Reseau
# ------------------------------------------------------------------

def _open(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read(_MAX_PAGE_BYTES)
    except Exception as exc:
        raise SearchError(_("Service injoignable : {error}").format(
            error=exc)) from exc


def _json_get(url: str) -> dict:
    try:
        return json.loads(_open(url).decode("utf-8", errors="replace"))
    except SearchError:
        raise
    except ValueError as exc:
        raise SearchError(_("Réponse illisible du service de recherche.")) from exc


def _text_get(url: str) -> str:
    return _open(url).decode("utf-8", errors="replace")
