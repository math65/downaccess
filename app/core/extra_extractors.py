"""Extracteurs maison, pour les sites que yt-dlp ne reconnait pas.

yt-dlp refuse les contributions ecrites avec l'aide d'une IA : on ne peut pas
lui proposer ces extracteurs, on les branche donc ici, devant les siens
(`register`). Garder ce module minuscule : un site n'y entre que si sa page
donne le media sans navigateur ni jeton.
"""
import json
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, parse_duration, unified_strdate

_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)

_EPISODE_TYPES = ("RadioEpisode", "PodcastEpisode")


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
                "title": (episode.get("name") or video_id).replace("\xa0", " "),
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


_EXTRA_EXTRACTORS = (IciFrIE,)


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
