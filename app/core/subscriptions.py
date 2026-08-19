"""Abonnements : suivre des chaines et des podcasts, et voir ce qui est nouveau.

Suivre une emission demandait jusqu'ici d'ouvrir l'application, de retaper la
recherche et de comparer de tete avec ce qu'on avait deja. On inverse : on
s'abonne une fois, et DownAccess dit ce qui est arrive depuis la derniere fois.

Le releve passe par les flux RSS/Atom, pas par une extraction complete :
YouTube publie un flux Atom par chaine et par playlist, les podcasts sont des
flux RSS par nature. Une verification coute quelques kilo-octets et une seule
requete, sans quota ni defi JavaScript. C'est ce qui rend une verification a
chaque lancement acceptable.

Stockage : subscriptions.json dans le dossier de configuration.
"""

import json
import logging
import os
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, UTC
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.i18n import _translate as _

_log = logging.getLogger("downaccess.subscriptions")

# Au-dela, on ne garde que les plus recents : un abonnement suivi pendant des
# annees ferait sinon enfler le fichier de configuration sans fin.
MAX_SEEN_IDS = 500

# Un flux honnete pese quelques dizaines de kilo-octets. Le plafond protege
# d'un serveur qui repondrait un fichier enorme.
MAX_FEED_BYTES = 5 * 1024 * 1024

HTTP_TIMEOUT = 20

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")

KIND_YOUTUBE = "youtube"
KIND_PODCAST = "podcast"

_NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "yt":    "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com")
_YT_CHANNEL_ID_RE = re.compile(r'"(?:channelId|externalId)"\s*:\s*"(UC[\w-]{16,})"')
_YT_CANONICAL_RE = re.compile(
    r'<link[^>]+rel="canonical"[^>]+href="[^"]*?/channel/(UC[\w-]{16,})"')
_FEED_LINK_RE = re.compile(
    r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', re.IGNORECASE)
_HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
# Un flux ne devrait jamais declarer de DTD ni d'entites : les refuser coupe
# court aux bombes d'expansion sur un fichier qu'on ne controle pas.
_DOCTYPE_RE = re.compile(rb"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class FeedError(Exception):
    """Flux introuvable, illisible, ou sans la moindre entree."""


@dataclass
class FeedEntry:
    """Une video ou un episode annonce par un flux."""
    entry_id: str = ""
    title: str = ""
    url: str = ""
    published: str = ""        # ISO 8601, vide si le flux n'en donne pas
    summary: str = ""

    def published_label(self) -> str:
        """Date lisible (JJ/MM/AAAA), ou chaine vide."""
        if not self.published:
            return ""
        try:
            return datetime.fromisoformat(self.published).strftime("%d/%m/%Y")
        except ValueError:
            return ""


@dataclass
class Subscription:
    """Une chaine ou un podcast suivi."""
    sub_id: str = ""
    title: str = ""
    url: str = ""              # ce que l'utilisateur a saisi
    feed_url: str = ""         # le flux resolu
    kind: str = KIND_PODCAST
    format_spec: str = ""      # vide = format par defaut des preferences
    auto_download: bool = False
    added_at: str = ""
    last_checked: str = ""
    seen_ids: list[str] = field(default_factory=list)

    def kind_label(self) -> str:
        return _("Chaîne") if self.kind == KIND_YOUTUBE else _("Podcast")

    def last_checked_label(self) -> str:
        if not self.last_checked:
            return _("jamais")
        try:
            return datetime.fromisoformat(self.last_checked).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return ""


# ------------------------------------------------------------------
# Stockage
# ------------------------------------------------------------------

def _store_file() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    path = Path(appdata) / "DownAccess"
    path.mkdir(parents=True, exist_ok=True)
    return path / "subscriptions.json"


def load() -> list[Subscription]:
    try:
        with open(_store_file(), encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    valid = {f.name for f in fields(Subscription)}
    out: list[Subscription] = []
    for item in raw.get("subscriptions", []):
        if not isinstance(item, dict):
            continue
        sub = Subscription(**{k: v for k, v in item.items() if k in valid})
        if not sub.sub_id:
            sub.sub_id = str(uuid.uuid4())
        out.append(sub)
    return out


def save(subs: list[Subscription]) -> None:
    """Ecriture atomique : une coupure pendant la sauvegarde ne doit pas laisser
    un fichier tronque qui ferait perdre tous les abonnements."""
    payload = {"version": 1, "subscriptions": [asdict(s) for s in subs]}
    path = _store_file()
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ------------------------------------------------------------------
# Reseau
# ------------------------------------------------------------------

def _http_get(url: str) -> bytes:
    """Telecharge un flux. Toute panne reseau ressort en FeedError : l'appelant
    affiche ce message tel quel a l'utilisateur, il ne doit jamais tomber sur
    une trace HTTPError brute."""
    req = Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.read(MAX_FEED_BYTES + 1)[:MAX_FEED_BYTES]
    except HTTPError as exc:
        raise FeedError(_("Le serveur a répondu {code} ({reason}).").format(
            code=exc.code, reason=exc.reason)) from exc
    except URLError as exc:
        raise FeedError(_("Adresse injoignable : {error}").format(
            error=exc.reason)) from exc
    except OSError as exc:
        raise FeedError(_("Adresse injoignable : {error}").format(error=exc)) from exc


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise FeedError(_("Aucune adresse indiquée."))
    if "://" not in url:
        url = "https://" + url
    if urlparse(url).scheme not in ("http", "https"):
        raise FeedError(_("Seules les adresses http et https sont acceptées."))
    return url


# ------------------------------------------------------------------
# Analyse d'un flux
# ------------------------------------------------------------------

def _text(node, path: str) -> str:
    found = node.find(path, _NS)
    return (found.text or "").strip() if found is not None and found.text else ""


def _iso(value: str) -> str:
    """Date d'un flux (Atom ISO ou RSS RFC 822) -> ISO 8601, ou chaine vide."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return ""


def parse_feed(data: bytes) -> tuple[str, list[FeedEntry]]:
    """Contenu brut d'un flux Atom ou RSS -> (titre du flux, entrees).

    Leve FeedError si ce n'est pas un flux exploitable — c'est ce qui permet a
    `resolve_feed` d'essayer une adresse puis de se rabattre sur la page HTML.
    """
    if _DOCTYPE_RE.search(data):
        raise FeedError(_("Ce flux contient une déclaration non autorisée."))
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise FeedError(str(exc)) from exc

    entries: list[FeedEntry] = []

    if root.tag.endswith("}feed"):          # Atom (YouTube)
        title = _text(root, "atom:title")
        for node in root.findall("atom:entry", _NS):
            link = node.find("atom:link[@rel='alternate']", _NS)
            url = link.get("href", "") if link is not None else ""
            entries.append(FeedEntry(
                entry_id=_text(node, "yt:videoId") or _text(node, "atom:id") or url,
                title=_text(node, "atom:title"),
                url=url,
                published=_iso(_text(node, "atom:published")
                               or _text(node, "atom:updated")),
                summary=_text(node, "media:group/media:description"),
            ))
    elif root.tag == "rss" or root.find("channel") is not None:   # RSS 2.0
        channel = root.find("channel")
        if channel is None:
            raise FeedError(_("Flux RSS sans canal."))
        title = _text(channel, "title")
        for node in channel.findall("item"):
            link = _text(node, "link")
            enclosure = node.find("enclosure")
            media_url = enclosure.get("url", "") if enclosure is not None else ""
            entries.append(FeedEntry(
                entry_id=_text(node, "guid") or link or media_url,
                title=_text(node, "title"),
                # L'enclosure est le media lui-meme : c'est elle qu'il faut
                # telecharger. Le lien de l'item pointe souvent vers une page.
                url=media_url or link,
                published=_iso(_text(node, "pubDate")),
                summary=_text(node, "description"),
            ))
    else:
        raise FeedError(_("Ce document n'est pas un flux RSS ou Atom."))

    entries = [e for e in entries if e.entry_id and e.url]
    if not entries:
        raise FeedError(_("Ce flux ne contient aucune entrée exploitable."))
    return title, entries


# ------------------------------------------------------------------
# Resolution : URL saisie par l'utilisateur -> flux
# ------------------------------------------------------------------

def _youtube_feed_from_url(url: str) -> str:
    """Flux deductible sans requete reseau (identifiant deja dans l'URL)."""
    parsed = urlparse(url)
    if parsed.hostname not in _YT_HOSTS:
        return ""
    playlist = parse_qs(parsed.query).get("list", [""])[0]
    if playlist.startswith(("PL", "UU", "OL")):
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist}"
    match = re.search(r"/channel/(UC[\w-]{16,})", parsed.path)
    if match:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={match.group(1)}"
    return ""


def _feed_from_html(html: str, base_url: str) -> str:
    """Flux annonce dans l'en-tete d'une page (<link rel=alternate>)."""
    for tag in _FEED_LINK_RE.findall(html):
        href = _HREF_RE.search(tag)
        if not href:
            continue
        link = href.group(1)
        if link.startswith("//"):
            return "https:" + link
        if link.startswith("/"):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{link}"
        if link.startswith("http"):
            return link
    return ""


def resolve_feed(url: str) -> tuple[str, str, str]:
    """URL saisie -> (adresse du flux, type, titre).

    Accepte une chaine YouTube sous toutes ses formes (@identifiant, /channel/,
    /c/, /user/), une playlist, un flux RSS direct, ou n'importe quelle page
    qui declare un flux dans son en-tete.
    """
    url = _normalize_url(url)

    # 1. Identifiant deja present dans l'URL : aucune requete de decouverte.
    feed_url = _youtube_feed_from_url(url)
    if feed_url:
        title, _entries = parse_feed(_http_get(feed_url))
        return feed_url, KIND_YOUTUBE, title

    # 2. L'adresse est peut-etre deja un flux.
    data = _http_get(url)
    try:
        title, _entries = parse_feed(data)
    except FeedError:
        pass
    else:
        kind = KIND_YOUTUBE if "youtube.com" in url else KIND_PODCAST
        return url, kind, title

    # 3. Sinon c'est une page : y chercher l'identifiant de chaine, puis le
    #    flux declare dans l'en-tete.
    html = data.decode("utf-8", errors="replace")
    if urlparse(url).hostname in _YT_HOSTS:
        match = _YT_CANONICAL_RE.search(html) or _YT_CHANNEL_ID_RE.search(html)
        if match:
            feed_url = ("https://www.youtube.com/feeds/videos.xml"
                        f"?channel_id={match.group(1)}")
            title, _entries = parse_feed(_http_get(feed_url))
            return feed_url, KIND_YOUTUBE, title

    feed_url = _feed_from_html(html, url)
    if feed_url:
        title, _entries = parse_feed(_http_get(feed_url))
        return feed_url, KIND_PODCAST, title

    raise FeedError(_("Aucun flux n'a été trouvé à cette adresse."))


# ------------------------------------------------------------------
# Abonnements
# ------------------------------------------------------------------

def create(url: str, title: str = "", format_spec: str = "",
           auto_download: bool = False) -> Subscription:
    """Resout le flux et cree l'abonnement.

    Toutes les entrees deja publiees sont marquees comme vues : s'abonner
    aujourd'hui veut dire « previens-moi de ce qui arrive », pas « deverse-moi
    les quinze dernieres videos ».
    """
    feed_url, kind, feed_title = resolve_feed(url)
    _title, entries = parse_feed(_http_get(feed_url))
    now = datetime.now(UTC).isoformat()
    return Subscription(
        sub_id=str(uuid.uuid4()),
        title=(title or feed_title or url).strip(),
        url=url.strip(),
        feed_url=feed_url,
        kind=kind,
        format_spec=format_spec,
        auto_download=auto_download,
        added_at=now,
        last_checked=now,
        seen_ids=[e.entry_id for e in entries][:MAX_SEEN_IDS],
    )


def check(sub: Subscription) -> list[FeedEntry]:
    """Entrees jamais vues pour cet abonnement, la plus recente d'abord.

    Ne modifie pas l'abonnement : c'est l'appelant qui decide quand marquer
    comme vu, pour que fermer la fenetre ne fasse pas perdre les nouveautes.
    """
    _title, entries = parse_feed(_http_get(sub.feed_url))
    seen = set(sub.seen_ids)
    return [e for e in entries if e.entry_id not in seen]


def mark_seen(sub: Subscription, entries: list[FeedEntry]) -> None:
    known = set(sub.seen_ids)
    for entry in entries:
        if entry.entry_id not in known:
            sub.seen_ids.append(entry.entry_id)
            known.add(entry.entry_id)
    if len(sub.seen_ids) > MAX_SEEN_IDS:
        del sub.seen_ids[:-MAX_SEEN_IDS]


def touch(sub: Subscription) -> None:
    """Note l'instant de la derniere verification reussie."""
    sub.last_checked = datetime.now(UTC).isoformat()


def check_all(subs: list[Subscription]) -> tuple[dict[str, list[FeedEntry]], list[str]]:
    """Verifie tous les abonnements. Retourne ({sub_id: nouveautes}, erreurs).

    Un flux en panne ne doit jamais empecher les autres de remonter : chaque
    abonnement est isole, et l'echec est collecte pour information.
    """
    fresh: dict[str, list[FeedEntry]] = {}
    errors: list[str] = []
    for sub in subs:
        try:
            entries = check(sub)
        except FeedError as exc:
            _log.warning("Abonnement « %s » injoignable : %s", sub.title, exc)
            errors.append(f"{sub.title} : {exc}")
            continue
        except Exception as exc:
            _log.exception("Abonnement « %s » : erreur inattendue", sub.title)
            errors.append(f"{sub.title} : {exc}")
            continue
        touch(sub)
        if entries:
            fresh[sub.sub_id] = entries
    return fresh, errors
