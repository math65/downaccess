"""Sites personnalisés : détection des pistes audio multiples.

Certains sites (france.tv, arte.tv) exposent plusieurs pistes audio pour une
même vidéo : français standard, audiodescription, parfois version originale.
yt-dlp prend par défaut « la meilleure » au hasard de son tri, ce qui empêche
l'utilisateur (souvent aveugle) de choisir explicitement l'audiodescription.

Ce module fournit une structure simple et extensible :
- un registre des sites concernés (hôtes + clés d'extracteur yt-dlp) ;
- une détection générique des pistes audio à partir des formats yt-dlp,
  qui fonctionne pour les deux sites malgré leurs métadonnées différentes.

Aucun `import wx` ici (règle app/core).
"""

from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.core.i18n import _translate as _


@dataclass
class AudioTrack:
    """Une piste audio proposée à l'utilisateur."""
    key: str                                  # identifiant stable interne
    label: str                                # libellé affiché (ex. « Audiodescription »)
    format_ids: list[str] = field(default_factory=list)  # ids yt-dlp (dash + hls), ordre de préférence
    is_audio_description: bool = False


# Hôtes déclenchant le choix de piste (suffixes de domaine).
_CUSTOM_SITE_HOSTS = ("france.tv", "arte.tv")

# Clés d'extracteur yt-dlp correspondantes (robustesse si l'hôte change).
_CUSTOM_SITE_EXTRACTORS = ("francetv", "francetvsite", "artetv")

# Marqueurs textuels d'audiodescription dans format_id / format_note.
_AD_MARKERS = (
    "audiodescription", "audio description", "audio_description",
    "qad", "descripti",
)


# Codes a trois lettres (ISO 639-2) vers leur equivalent a deux lettres. Les
# sites melangent les deux : M6 annonce « fra » et « eng », Arte « fr » et
# « de ». Sans cette table, une piste francaise s'afficherait « FRA ».
_LANG_ALIASES = {
    "fra": "fr", "fre": "fr", "eng": "en", "deu": "de", "ger": "de",
    "spa": "es", "ita": "it", "por": "pt", "nld": "nl", "dut": "nl",
}


def normalize_lang(code: str | None) -> str:
    """Code de langue ramene a deux lettres (« fra » -> « fr », « fr-FR » -> « fr »)."""
    base = (code or "").strip().lower().replace("_", "-").split("-")[0]
    return _LANG_ALIASES.get(base, base)


def lang_name(code: str | None) -> str:
    """Nom lisible d'un code de langue (repli : code en majuscules)."""
    names = {
        "fr": _("Français"),
        "de": _("Allemand"),
        "en": _("Anglais"),
        "es": _("Espagnol"),
        "it": _("Italien"),
        "pt": _("Portugais"),
        "nl": _("Néerlandais"),
    }
    if not code:
        return _("Audio")
    normalise = normalize_lang(code)
    return names.get(normalise, (normalise or code).upper())


def _lang_name(code: str | None) -> str:
    return lang_name(code)


def is_custom_site_url(url: str) -> bool:
    """True si l'URL appartient à un site personnalisé (avant fetch_info)."""
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in _CUSTOM_SITE_HOSTS)


def is_custom_site_extractor(extractor_key: str | None) -> bool:
    """True si la clé d'extracteur yt-dlp correspond à un site personnalisé."""
    if not extractor_key:
        return False
    key = extractor_key.lower()
    return any(e in key for e in _CUSTOM_SITE_EXTRACTORS)


def detect_audio_tracks(formats: list[dict]) -> list[AudioTrack]:
    """Regroupe les formats audio par piste (langue + audiodescription).

    Retourne une liste d'`AudioTrack`. Liste vide si 0 ou 1 piste distincte
    (rien à demander à l'utilisateur).
    """
    if not formats:
        return []

    groups: dict[tuple[bool, str | None], AudioTrack] = {}
    order: list[tuple[bool, str | None]] = []

    for fmt in formats:
        if fmt.get("vcodec") not in (None, "none"):
            continue  # on ne garde que les formats audio-only
        fmt_id = fmt.get("format_id") or ""
        if not fmt_id:
            continue
        lang = fmt.get("language")
        haystack = f"{fmt_id} {fmt.get('format_note') or ''}".lower()
        is_ad = (lang == "qad") or any(m in haystack for m in _AD_MARKERS)
        # qad est une pseudo-langue d'audiodescription sans langue de base.
        base_lang = None if lang == "qad" else lang

        gkey = (is_ad, base_lang)
        track = groups.get(gkey)
        if track is None:
            if is_ad and base_lang is None:
                label = _("Audiodescription")
            elif is_ad:
                label = _("Audiodescription ({lang})").format(lang=_lang_name(base_lang))
            else:
                label = _lang_name(base_lang)
            track = AudioTrack(
                key=f"{'ad' if is_ad else 'std'}-{base_lang or 'x'}",
                label=label,
                is_audio_description=is_ad,
            )
            groups[gkey] = track
            order.append(gkey)
        if fmt_id not in track.format_ids:
            track.format_ids.append(fmt_id)

    tracks = [groups[k] for k in order]
    if len(tracks) < 2:
        return []

    # Ordre d'affichage : pistes standard d'abord, audiodescription ensuite.
    tracks.sort(key=lambda t: (t.is_audio_description, t.key))
    return tracks
