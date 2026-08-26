"""Transcription : recuperer les sous-titres d'un media et les rendre lisibles.

Une video n'est pas parcourable pour quelqu'un qui ne la voit pas : impossible
de survoler, de chercher un mot, de savoir en dix secondes si le contenu vaut
les quarante minutes. Le texte, si. On recupere donc les sous-titres du site
(manuels de preference, automatiques a defaut) et on les nettoie de tout
l'appareillage technique — index, horodatages, balises — pour n'en garder que
la parole.
"""

import glob
import html
import logging
import os
import re
import tempfile

import yt_dlp

from app.core.i18n import _translate as _
from app.core.jsruntime_utils import get_js_runtimes_opt

_log = logging.getLogger("downaccess.transcript")


class TranscriptError(Exception):
    """Aucune transcription exploitable pour ce media."""


# Une ligne d'horodatage : « 00:00:12.345 --> 00:00:15.000 » (SRT comme VTT,
# la virgule decimale du SRT comprise).
_TIMECODE_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?[.,]\d{1,3}\s*-->")
# Index de bloc SRT : une ligne qui n'est qu'un nombre.
_INDEX_RE = re.compile(r"^\d+$")
# Balises de mise en forme et de karaoke des sous-titres YouTube :
# <c>, </c>, <00:00:01.234>, <i>, <font color="...">...
_TAG_RE = re.compile(r"<[^>]*>")
# En-tetes de fichier a ignorer.
_HEADER_PREFIXES = ("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")

# Longueur visee d'un paragraphe. Les sous-titres automatiques arrivent par
# bribes de trois ou quatre mots : les recoller en paragraphes evite une
# lecture hachee au lecteur d'ecran, tout en gardant des reperes pour naviguer.
_PARAGRAPH_CHARS = 400

# Plafond dur. Les sous-titres automatiques n'ont parfois aucune ponctuation de
# toute la video : sans cette borne, tout tiendrait en un seul paragraphe.
_PARAGRAPH_MAX = 700

# Fin de phrase suivie d'une espace. Le texte est normalise avant decoupage :
# les separateurs sont toujours une espace simple.
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…]) ")


def _split_paragraphs(texte: str) -> list[str]:
    """Regroupe le texte en paragraphes commencant tous sur un debut de phrase.

    Couper au caractere pres terminait un paragraphe au milieu d'une phrase, et
    le suivant s'ouvrait sur un fragment orphelin (« bien les couleurs, ou pas
    du tout. ») : illisible au lecteur d'ecran, qui parcourt bloc par bloc.
    """
    phrases: list[str] = []
    for part in _SENTENCE_END_RE.split(texte):
        part = part.strip()
        # Une phrase un peu longue reste entiere : la couper en deux ferait
        # revenir le fragment orphelin qu'on cherche justement a eviter. Au-dela
        # du plafond, c'est que la video n'a aucune ponctuation : on decoupe
        # alors a la longueur visee, pour garder des blocs navigables.
        while len(part) > _PARAGRAPH_MAX:
            coupe = part.rfind(" ", 0, _PARAGRAPH_CHARS)
            if coupe <= 0:
                coupe = _PARAGRAPH_CHARS
            phrases.append(part[:coupe].strip())
            part = part[coupe:].strip()
        if part:
            phrases.append(part)

    paragraphs: list[str] = []
    current: list[str] = []
    length = 0
    for phrase in phrases:
        if current and length + len(phrase) + 1 > _PARAGRAPH_CHARS:
            paragraphs.append(" ".join(current))
            current, length = [], 0
        current.append(phrase)
        length += len(phrase) + 1
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def parse_subtitles(content: str) -> str:
    """Contenu brut d'un .vtt/.srt -> texte lisible.

    Deduplique au passage : les sous-titres automatiques de YouTube defilent
    en fenetre glissante et repetent chaque bribe plusieurs fois
    (« bonjour », puis « bonjour a tous », puis « bonjour a tous et »).
    """
    pieces: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or _TIMECODE_RE.match(line) or _INDEX_RE.match(line):
            continue
        if any(line.startswith(p) for p in _HEADER_PREFIXES):
            continue
        line = html.unescape(_TAG_RE.sub("", line)).strip()
        if not line:
            continue
        if pieces:
            previous = pieces[-1]
            if line == previous:
                continue
            # Fenetre glissante : la nouvelle bribe prolonge la precedente.
            if line.startswith(previous):
                pieces[-1] = line
                continue
            if previous.endswith(line):
                continue
        pieces.append(line)

    texte = " ".join(" ".join(pieces).split())
    if not texte:
        return ""
    return "\n\n".join(_split_paragraphs(texte))


def _pick_subtitle_file(folder: str, langs: list[str]) -> str:
    """Choisit le fichier de sous-titres le plus pertinent du dossier.

    Priorite a la langue demandee dans l'ordre des preferences ; a langue
    egale, les sous-titres ecrits par un humain valent mieux que les
    automatiques, mais yt-dlp les nomme pareil — c'est lui qui a deja tranche
    en n'ecrivant qu'un fichier par langue.
    """
    files = sorted(glob.glob(os.path.join(folder, "*.vtt"))
                   + glob.glob(os.path.join(folder, "*.srt")))
    if not files:
        return ""
    for lang in langs:
        for path in files:
            # yt-dlp nomme « titre.fr.vtt », « titre.en-US.vtt »...
            stem = os.path.basename(path).rsplit(".", 2)
            if len(stem) == 3 and stem[1].lower().startswith(lang.lower()):
                return path
    return files[0]


def _language_of(path: str) -> str:
    parts = os.path.basename(path).rsplit(".", 2)
    return parts[1] if len(parts) == 3 else ""


def fetch_transcript(settings: dict, url: str,
                     cookies_file: str | None = None) -> tuple[str, str]:
    """Recupere et nettoie les sous-titres de `url`.

    Retourne `(texte, code_langue)`. Leve `TranscriptError` si le media n'a
    aucun sous-titre exploitable — c'est frequent et ce n'est pas une panne :
    l'appelant doit le dire calmement.
    """
    langs = settings.get("subtitle_langs") or ["fr", "en"]

    with tempfile.TemporaryDirectory(prefix="da_transcript_") as tmp:
        opts = {
            "skip_download":    True,
            "writesubtitles":   True,
            "writeautomaticsub": True,
            "subtitleslangs":   langs,
            "subtitlesformat":  "vtt/srt/best",
            "outtmpl":          os.path.join(tmp, "%(id)s.%(ext)s"),
            "quiet":            True,
            "no_warnings":      True,
            "js_runtimes":      get_js_runtimes_opt(),
            "socket_timeout":   30,
            "retries":          10,
        }
        if settings.get("proxy_http"):
            opts["proxy"] = settings["proxy_http"]
        if settings.get("user_agent"):
            opts["http_headers"] = {"User-Agent": settings["user_agent"]}
        if cookies_file:
            opts["cookiefile"] = cookies_file
        else:
            from app.core.cookies import apply_cookies
            from app.core.downloader import _should_use_cookies
            if _should_use_cookies(settings, url):
                apply_cookies(opts, url)

        # Un echec sur UNE langue (429 de YouTube, piste absente) interrompt
        # yt-dlp alors qu'une autre langue a peut-etre deja ete ecrite : on note
        # l'erreur et on regarde ce qui est arrive sur le disque avant de
        # declarer forfait.
        failure = ""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            failure = str(exc)
            _log.warning("Sous-titres partiellement indisponibles (%s) : %s",
                         url, failure)

        path = _pick_subtitle_file(tmp, langs)
        if not path:
            if failure:
                raise TranscriptError(failure)
            raise TranscriptError(_("Ce média ne propose aucun sous-titre."))
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = parse_subtitles(fh.read())

    if not text.strip():
        raise TranscriptError(_("Les sous-titres de ce média sont vides."))
    return text, _language_of(path)
