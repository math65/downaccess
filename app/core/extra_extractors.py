"""Extracteurs maison, pour les sites que yt-dlp ne reconnait pas.

yt-dlp refuse les contributions ecrites avec l'aide d'une IA : on ne peut pas
lui proposer ces extracteurs, on les branche donc ici, devant les siens
(`register`). Garder ce module minuscule : un site n'y entre que si sa page
donne le media sans navigateur ni jeton.
"""
import json
import re
from datetime import datetime

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    parse_duration,
    smuggle_url,
    unified_strdate,
    unsmuggle_url,
)

_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)

_EPISODE_TYPES = ("RadioEpisode", "PodcastEpisode")


def _clean(text) -> str:
    """Le site seme des espaces insecables dans ses titres."""
    return (text or "").replace("\xa0", " ").strip()


def _episodes_in(html: str):
    """Les blocs schema.org d'emission presents dans la page."""
    for raw in _LD_JSON_RE.findall(html or ""):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") in _EPISODE_TYPES:
                yield item


class IciFrIE(InfoExtractor):
    """Emissions de ici.fr (ex-France Bleu) — demande de Seb, 2026-11-17.

    La page d'une emission porte un bloc schema.org `RadioEpisode` dont
    `mainEntity.contentUrl` est le MP3 complet. Simple GET, pas d'anti-robot.
    """
    IE_NAME = "ici.fr"
    _VALID_URL = r"https?://(?:www\.)?ici\.fr/emissions/[^/?#]+/(?P<id>[^/?#]+)"

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        for episode in _episodes_in(webpage):
            audio = episode.get("mainEntity") or {}
            media_url = audio.get("contentUrl") if isinstance(audio, dict) else None
            if not media_url:
                continue
            series = episode.get("partOfSeries") or {}
            return {
                "id": video_id,
                "title": _clean(episode.get("name")) or video_id,
                "description": episode.get("description"),
                "url": media_url,
                "ext": "mp3",
                "vcodec": "none",
                "duration": parse_duration(audio.get("duration")),
                "series": series.get("name") if isinstance(series, dict) else None,
                "upload_date": unified_strdate(episode.get("dateCreated")),
            }
        # `expected=True` : pas d'invitation a ouvrir un ticket chez yt-dlp.
        raise ExtractorError("No video formats found on this ici.fr page", expected=True)


class IciFrProgrammeIE(InfoExtractor):
    """Un programme entier de ici.fr, vu comme une playlist de ses emissions.

    La page du programme ne montre en liens qu'une partie des emissions : plus
    de la moitie n'ont pas de page a elles (53 sur 87 pour le programme de
    Seb). La liste complete vient de l'API que la page interroge elle-meme,
    `/api/audio/expressions/<id>/paginated?pageNumber=N`, qui donne pour
    chaque emission son titre, sa date et son MP3.

    Une emission sans page n'a pas d'adresse. On lui en fabrique une : celle du
    programme, avec les donnees de l'emission « passees en fraude » dans le
    fragment (`smuggle_url`, le mecanisme de yt-dlp pour cela). Quand
    DownAccess redonne cette adresse pour telecharger, tout est deja dedans :
    aucun nouvel appel au site, et rien ne bouge si la liste a avance entre-temps.
    """
    IE_NAME = "ici.fr:programme"
    _VALID_URL = r"https?://(?:www\.)?ici\.fr/emissions/(?P<id>[^/?#]+)/?(?:[?#].*)?$"
    _CONCEPT_RE = r"/api/audio/expressions/([0-9a-f-]{36})/paginated"
    # Garde-fou : une API qui annoncerait toujours une page suivante ne doit
    # pas faire boucler l'analyse.
    _MAX_PAGES = 500

    @staticmethod
    def _episode_info(item: dict, series: str) -> dict | None:
        """Une emission de l'API, sous la forme attendue par yt-dlp."""
        media = item.get("media") or {}
        source = next((s.get("url") for s in media.get("sources") or []
                       if isinstance(s, dict) and s.get("url")), None)
        if not source:
            return None
        title = _clean(item.get("title"))
        start = media.get("startTime")
        # Faute de titre propre, l'API repete celui du programme : sans la
        # date, toutes ces emissions porteraient le meme nom de fichier.
        if (not title or title == series) and start:
            title = f"{series} - {datetime.fromtimestamp(start).strftime('%d-%m-%Y')}"
        return {
            "id": item.get("id") or source.rsplit("/", 1)[-1],
            "title": title or series,
            "description": _clean(item.get("standFirst")) or None,
            "url": source,
            "ext": "mp3",
            "vcodec": "none",
            "duration": media.get("duration"),
            "timestamp": start,
            "series": series,
        }

    def _entries(self, programme_id, programme_url, concept_id, series):
        for page in range(1, self._MAX_PAGES + 1):
            data = self._download_json(
                f"https://www.ici.fr/api/audio/expressions/{concept_id}/paginated",
                programme_id, query={"pageNumber": page},
                note=f"Downloading page {page}", fatal=False) or {}
            for item in data.get("results") or []:
                info = self._episode_info(item, series)
                if info is None:
                    continue
                if item.get("path"):
                    # Elle a sa page : une adresse propre, que `IciFrIE` sait lire.
                    yield self.url_result(
                        "https://www.ici.fr/" + item["path"].lstrip("/"), ie=IciFrIE,
                        video_id=info["id"], video_title=info["title"])
                else:
                    yield self.url_result(
                        smuggle_url(programme_url, {"episode": info}),
                        ie=IciFrProgrammeIE,
                        video_id=info["id"], video_title=info["title"])
            if not data.get("hasNextPage"):
                return

    def _real_extract(self, url):
        url, smuggled = unsmuggle_url(url, {})
        episode = smuggled.get("episode")
        if episode:
            return episode

        programme_id = self._match_id(url)
        programme_url = f"https://www.ici.fr/emissions/{programme_id}"
        webpage = self._download_webpage(programme_url, programme_id)
        title = _clean(self._html_search_regex(
            r"<h1[^>]*>(.+?)</h1>", webpage, "title", default=programme_id))
        concept_id = self._search_regex(
            self._CONCEPT_RE, webpage, "programme id", default=None)
        if not concept_id:
            raise ExtractorError(
                "No video formats found on this ici.fr programme page", expected=True)
        return self.playlist_result(
            self._entries(programme_id, programme_url, concept_id, title),
            programme_id, title)


_EXTRA_EXTRACTORS = (IciFrIE, IciFrProgrammeIE)


def register(ydl) -> None:
    """Place nos extracteurs DEVANT ceux de yt-dlp.

    yt-dlp prend le premier extracteur qui reconnait l'adresse, et son
    extracteur generique (le dernier) accepte tout : `add_info_extractor`, qui
    ajoute a la fin, ne suffit donc pas. `_ies` est un attribut interne —
    `tests/core/test_extra_extractors.py` casse s'il change de forme.
    """
    if not isinstance(getattr(ydl, "_ies", None), dict):
        return
    # Une INSTANCE, pas la classe : yt-dlp ne sait instancier par nom que les
    # extracteurs de son propre registre (KeyError sinon).
    for ie in _EXTRA_EXTRACTORS:
        ydl.add_info_extractor(ie())
    ours = [ie.ie_key() for ie in _EXTRA_EXTRACTORS]
    ies = ydl._ies
    ydl._ies = {k: ies[k] for k in ours} | {k: v for k, v in ies.items() if k not in ours}
