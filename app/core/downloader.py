import io
import logging
import os
import re
import shutil
import tempfile
import time
import threading
from dataclasses import dataclass, field
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import yt_dlp

from app.core.ffmpeg_utils import get_ffmpeg_path
from app.core.i18n import _translate as _
from app.core.jsruntime_utils import get_js_runtimes_opt

_log = logging.getLogger("downaccess.downloader")


def _write_cookie_jar(cookie_header: str, url: str) -> str:
    """Écrit un fichier cookie jar Netscape à partir d'un header Cookie brut.
    Retourne le chemin du fichier temporaire."""
    domain = urlparse(url).hostname or ""
    lines = ["# Netscape HTTP Cookie File"]
    for pair in cookie_header.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        lines.append(f".{domain}\tTRUE\t/\tFALSE\t0\t{name.strip()}\t{value.strip()}")
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="da_cookies_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


# Tri de sélection vidéo pour les sites à pistes audio (france.tv, arte) :
# résolution/fps/codec d'abord (qualité réelle), puis, à égalité stricte, on
# préfère le protocole DASH — téléchargeable nativement (progression segment par
# segment + annulation), contrairement au HLS de france.tv qui passe par ffmpeg.
# La résolution primant, un HLS réellement plus haut l'emporte malgré tout.
_CUSTOM_VIDEO_SORT = ["res", "fps", "vcodec", "proto:http_dash_segments"]

# Cles d'options yt-dlp construites par l'appli : les options « brutes » saisies
# par l'utilisateur (Preferences > Avance) ne doivent jamais les ecraser, sous
# peine de casser le telechargement (selection de format, dossiers, hooks...).
_PROTECTED_OPTS = frozenset({
    "format", "format_sort", "outtmpl", "paths", "trim_file_name",
    "postprocessors", "progress_hooks", "postprocessor_hooks",
    "merge_output_format", "allow_multiple_audio_streams",
    "concurrent_fragment_downloads", "js_runtimes", "extractor_args",
    "ffmpeg_location", "cookiefile", "cookiesfrombrowser",
    "writesubtitles", "writeautomaticsub", "subtitleslangs", "subtitlesformat",
    "skip_download", "outtmpl_na_placeholder",
})


# Hôtes YouTube reconnus pour la normalisation des URLs de chaîne
_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com")

# Onglets de chaîne déjà spécifiques — on ne les touche pas
_YT_CHANNEL_TABS = ("videos", "shorts", "streams", "playlists",
                    "featured", "community", "about", "live", "podcasts")


def _normalize_youtube_channel_url(url: str) -> str:
    """Réécrit les URLs de chaîne YouTube vers l'onglet « Vidéos ».

    YouTube borne l'endpoint *playlist* aux 100 dernières vidéos en accès non
    connecté (yt-dlp ne suit pas la pagination au-delà). L'onglet « Vidéos »
    d'une chaîne, lui, renvoie l'intégralité des vidéos. On réécrit donc :
      - les playlists « envois » auto-générées (list=UU…) vers /channel/UC…/videos
      - les URLs de chaîne nues (@handle, /channel/UC…, /c/…, /user/…) en y
        ajoutant /videos
    Les vraies playlists curées (list=PL…) et les onglets déjà spécifiques
    restent inchangés.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if (parsed.hostname or "").lower() not in _YT_HOSTS:
        return url

    # 1) Playlist « envois » auto-générée : list=UU… -> chaîne /videos
    list_id = (parse_qs(parsed.query).get("list") or [""])[0]
    if parsed.path.rstrip("/") == "/playlist" and list_id.startswith("UU"):
        return f"https://www.youtube.com/channel/UC{list_id[2:]}/videos"

    # 2) URL de chaîne nue (sans onglet spécifique) -> ajouter /videos
    segments = [s for s in parsed.path.split("/") if s]
    if segments:
        head, last = segments[0], segments[-1].lower()
        is_channel = head.startswith("@") or head in ("channel", "c", "user")
        if is_channel and last not in _YT_CHANNEL_TABS:
            return f"https://www.youtube.com/{'/'.join(segments)}/videos"
    return url


@dataclass
class DownloadInfo:
    download_id: str
    url: str
    title: str = ""
    site: str = ""
    fmt: str = ""
    duration: float = 0.0   # durée en secondes (estimation taille si filesize absent)
    raw_formats: list = field(default_factory=list)
    is_playlist: bool = False
    playlist_entries: list = field(default_factory=list)
    playlist_count: int = 0   # total réel annoncé par YouTube (peut dépasser
                              # len(playlist_entries) si yt-dlp est plafonné)


@dataclass
class DownloadProgress:
    download_id: str
    percent: float = 0.0
    speed: str = ""
    size: str = ""
    status: str = "downloading"  # downloading | finished | error
    filepath: str = ""           # chemin du fichier final (status=finished)


# Types de callbacks
OnInfoCallback      = Callable[[DownloadInfo], None]
OnProgressCallback  = Callable[[DownloadProgress], None]
OnErrorCallback     = Callable[[str, str], None]   # (download_id, message)


# Marqueurs (dans les messages yt-dlp) indiquant qu'une connexion au site
# règlerait le problème : contenu réservé aux adultes/membres/privé, ou
# suggestion explicite de yt-dlp d'utiliser des cookies/identifiants.
_LOGIN_REQUIRED_PATTERNS = (
    "confirm your age", "age-restricted", "sign in to confirm",
    "login_required", "this video is private", "private video",
    "members-only", "join this channel",
    "cookies-from-browser", "for the authentication", "use --cookies",
    "sign in to", "log in to",
)


def _is_login_required(msg: str) -> bool:
    """Vrai si l'erreur yt-dlp indique qu'une connexion au site aiderait."""
    low = msg.lower()
    return any(p in low for p in _LOGIN_REQUIRED_PATTERNS)


# Marqueurs d'une erreur côté serveur/réseau qu'une *nouvelle extraction*
# peut résoudre. Cas typique YouTube : l'URL signée (googlevideo.com) du
# client de repli ANDROID_VR se fait refuser par intermittence (403/Forbidden,
# durcissement SABR/PO-token). Une ré-extraction fraîche regénère une URL
# acceptée. Les 5xx transitoires entrent dans la même catégorie.
_TRANSIENT_ERROR_PATTERNS = (
    "http error 403", "forbidden",
    "unable to download video data",
    "http error 500", "http error 502", "http error 503",
    # Flux coupe en cours de route : le serveur ferme la connexion avant la fin
    # ("N bytes read, M more expected"). Les 20 reessais internes de yt-dlp
    # retapent la MEME URL signee, deja perimee -> ils echouent tous. Seule une
    # nouvelle extraction regenere une URL acceptee.
    # ("incompleteread" sans espace : c'est le nom de la classe d'exception
    # http.client telle qu'elle apparait dans le message.)
    "more expected", "incompleteread", "content too short",
    # Coupure reseau cote utilisateur : le nom de domaine ne se resout plus
    # (wifi qui saute, box qui redemarre, VPN qui bascule). C'est le cas le
    # plus manifestement reessayable qui soit : quelques secondes plus tard la
    # connexion est revenue. Errno 11001 sous Windows, -2/-3 sous Linux.
    "failed to resolve", "getaddrinfo failed", "name or service not known",
    "temporary failure in name resolution", "11001",
    "connection reset", "connection aborted", "connection refused",
    "network is unreachable",
)


# Marqueurs d'une coupure de connexion cote utilisateur, pour distinguer dans
# le message affiche « votre connexion a laché » de « le serveur a refuse ».
_NETWORK_DOWN_PATTERNS = (
    "failed to resolve", "getaddrinfo failed", "name or service not known",
    "temporary failure in name resolution", "11001",
    "network is unreachable", "connection refused",
)


def is_network_down_error(msg: str) -> bool:
    """Vrai si l'erreur traduit une connexion Internet coupee ou instable."""
    low = (msg or "").lower()
    return any(p in low for p in _NETWORK_DOWN_PATTERNS)


def is_drm_error(msg: str) -> bool:
    """Vrai si le media est protege par DRM (Netflix, Disney+, france.tv...).

    Cas sans issue : aucun reglage, aucune connexion, aucune nouvelle tentative
    n'y changera quoi que ce soit. Le dire clairement evite a l'utilisateur de
    chercher ce qu'il a mal fait.
    """
    low = (msg or "").lower()
    return "drm" in low and ("protect" in low or "protég" in low or "chiffr" in low)


def is_transient_error(msg: str) -> bool:
    """Vrai si l'erreur est probablement transitoire et qu'un nouvel essai
    (avec ré-extraction) a de bonnes chances d'aboutir. EXCLUT explicitement
    l'annulation par l'utilisateur (jamais à réessayer)."""
    low = (msg or "").lower()
    if "annul" in low or "cancel" in low:
        return False
    # Disque plein : reessayer ne fera que reremplir le disque. Garde-fou
    # explicite, pour que l'ajout d'un motif transitoire ne l'attrape jamais.
    if is_disk_full_error(low):
        return False
    return any(p in low for p in _TRANSIENT_ERROR_PATTERNS)


# ------------------------------------------------------------------
# Espace disque
# ------------------------------------------------------------------

# Marge exigee au-dessus de la taille estimee : yt-dlp ecrit aussi les
# sous-titres, la miniature et le fichier fusionne, et l'estimation elle-meme
# est approximative (debit x duree quand le serveur ne donne pas `filesize`).
# On ne bloque donc que si la place manque franchement.
_FREE_SPACE_MARGIN = 150 * 1024 * 1024

# Disque plein. yt-dlp/Python remontent l'erreur systeme en anglais
# ("[Errno 28] No space left on device"), parfois localisee par Windows.
_DISK_FULL_PATTERNS = (
    "no space left on device", "errno 28",
    "disk full", "not enough space", "espace insuffisant",
)


def is_disk_full_error(msg: str) -> bool:
    """Vrai si l'echec vient d'un disque plein (et non du site ou du reseau)."""
    return any(p in (msg or "").lower() for p in _DISK_FULL_PATTERNS)


def free_space_bytes(path: str) -> int:
    """Octets libres sur le volume de `path`. Remonte vers le premier parent
    existant (le dossier de destination n'est cree qu'au telechargement) et
    retourne -1 si le volume reste introuvable (lecteur reseau deconnecte)."""
    current = os.path.abspath(path or ".")
    while True:
        try:
            return shutil.disk_usage(current).free
        except OSError:
            parent = os.path.dirname(current)
            if not parent or parent == current:
                return -1
            current = parent


def _fmt_size(size: int) -> str:
    """Taille lisible. Volontairement duplique de `app/ui/format_dialog.py` :
    `app/core` n'importe jamais `app/ui` (meme msgid -> meme traduction)."""
    size = max(int(size), 0)
    if size >= 1_073_741_824:
        return _("{n:.1f} Go").format(n=size / 1_073_741_824)
    if size >= 1_048_576:
        return _("{n:.0f} Mo").format(n=size / 1_048_576)
    return _("{n:.0f} Ko").format(n=size / 1024)


def _space_detail(dest: str, needed: int, free: int) -> str:
    """Bloc « combien il reste / combien il faut », commun aux deux messages."""
    lines = []
    if free >= 0:
        lines.append(_("Espace libre sur « {folder} » : {size}.").format(
            folder=dest, size=_fmt_size(free)))
    if needed > 0:
        lines.append(_("Espace nécessaire : environ {size}.").format(
            size=_fmt_size(needed)))
    return "\n".join(lines)


def _free_space_advice() -> str:
    return _(
        "Libérez de l'espace sur ce disque, ou choisissez un autre dossier de "
        "téléchargement dans les Préférences (Ctrl+P)."
    )


def not_enough_space_message(dest: str, needed: int, free: int) -> str:
    """Message du garde-fou, AVANT que le telechargement ne demarre."""
    parts = [_("Il n'y a pas assez d'espace libre sur le disque pour "
               "télécharger ce fichier.")]
    detail = _space_detail(dest, needed, free)
    if detail:
        parts.append(detail)
    parts.append(_free_space_advice())
    return "\n\n".join(parts)


def disk_full_message(dest: str) -> str:
    """Message quand le disque s'est rempli PENDANT le telechargement."""
    parts = [_("Votre disque est plein : le téléchargement n'a pas pu être "
               "enregistré.")]
    detail = _space_detail(dest, 0, free_space_bytes(dest) if dest else -1)
    if detail:
        parts.append(detail)
    parts.append(_free_space_advice())
    return "\n\n".join(parts)


def _humanize_error(msg: str, dest: str = "") -> str:
    """Traduit certaines erreurs yt-dlp cryptiques en messages clairs et
    actionnables pour le grand public.

    Le texte d'origine reste disponible dans le log diagnostic ; ici on ne
    remplace que le message affiché à l'utilisateur dans le dialogue d'erreur.
    """
    low = msg.lower()

    # Disque plein. Le texte brut de yt-dlp ("unable to write data: [Errno 28]
    # No space left on device") est en anglais et incomprehensible pour le
    # grand public, alors que la cause est simple et la solution immediate.
    if is_disk_full_error(low):
        return disk_full_message(dest)

    # Contenu protege par DRM. Sans ce message, l'utilisateur lit « This video
    # is DRM protected » et cherche ce qu'il a mal regle : il n'y a rien a
    # regler, aucun telechargeur ne peut recuperer ce media.
    if is_drm_error(low):
        return _(
            "Cette vidéo est protégée contre la copie (DRM).\n\n"
            "DownAccess ne peut pas la télécharger, et aucun réglage n'y "
            "changera rien : c'est une protection posée par le site. Les "
            "plateformes par abonnement (Netflix, Disney+, Prime Video) et "
            "certaines vidéos de france.tv sont dans ce cas."
        )

    # Connexion coupee. Le texte brut (« Failed to resolve 'www.france.tv'
    # ([Errno 11001] getaddrinfo failed) ») est en anglais et designe le site,
    # ce qui fait croire a une panne du site ou de l'application alors que
    # c'est la connexion locale qui a laché.
    if is_network_down_error(low):
        return _(
            "La connexion Internet a été perdue pendant le téléchargement.\n\n"
            "DownAccess a réessayé sans succès. Vérifiez votre connexion, "
            "puis relancez le téléchargement avec la touche F2."
        )

    # Navigateur ouvert → base de cookies verrouillée (yt-dlp issue #7271).
    # Avec le parcours de connexion guidée (navigateur dédié), ce cas ne
    # devrait plus survenir, mais on garde un message clair en repli.
    if "cookie database" in low and ("could not copy" in low or "permission" in low):
        return _(
            "Impossible de lire les cookies de votre navigateur car il est "
            "actuellement ouvert.\n\n"
            "Fermez complètement votre navigateur, ou connectez-vous via le "
            "menu « Se connecter à un site », puis réessayez."
        )

    # Connexion requise : message court (le parcours de connexion guidée
    # affiche son propre dialogue détaillé ; ce texte sert de repli).
    if _is_login_required(msg):
        return _(
            "Ce contenu nécessite que vous soyez connecté au site "
            "(vidéo réservée aux adultes, privée ou réservée aux membres)."
        )

    return msg


def _raise_download_error(raw_msg: str, cause: Exception, dest: str = "") -> None:
    """Lève l'erreur du bon type : LoginRequiredError si une connexion
    aiderait, sinon DownloadError. Le message est reformulé pour l'utilisateur.
    `dest` = dossier de destination, pour chiffrer l'espace disque restant."""
    friendly = _humanize_error(raw_msg, dest)
    if _is_login_required(raw_msg):
        raise LoginRequiredError(friendly) from cause
    raise DownloadError(friendly) from cause


def _domain_from_url(url: str) -> str:
    """Extrait le domaine principal d'une URL (ex: 'youtube.com')."""
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    # Retirer le 'www.' pour normaliser
    if host.startswith("www."):
        host = host[4:]
    return host.lower()


def _should_use_cookies(settings: dict, url: str) -> bool:
    """Vérifie si le domaine de l'URL est dans la liste cookie_sites."""
    domain = _domain_from_url(url)
    return any(domain == site or domain.endswith("." + site)
               for site in settings.get("cookie_sites", []))


def _looks_already_present(*, skip_download: bool, format_spec: str,
                          section: tuple[float, float] | None,
                          completed: int, any_download: bool) -> bool:
    """Le fichier etait-il deja sur le disque avant ce telechargement ?

    yt-dlp ne le dit pas : on le deduit du hook de progression. Un 'finished'
    sans aucun 'downloading' prealable = aucun octet recu, donc fichier deja la.

    Un extrait fait exception. Il passe par ffmpeg (force_keyframes_at_cuts),
    qui n'emet jamais de 'downloading' : l'heuristique annoncerait « Deja
    telecharge » a chaque extrait, meme dans un dossier vide.
    """
    if skip_download or format_spec == "subtitles_only" or section is not None:
        return False
    return completed > 0 and not any_download


class Downloader:
    """
    Wrapper yt-dlp pour extraction d'infos et téléchargement.
    Tout s'exécute dans le thread appelant — c'est QueueManager
    qui gère le threading.
    """

    def __init__(self, settings: dict):
        self._settings = settings

    # ------------------------------------------------------------------
    # Extraction d'infos (sans télécharger)
    # ------------------------------------------------------------------

    def fetch_info(self, download_id: str, url: str,
                   use_cookies: bool = False,
                   referer: str | None = None,
                   cookies: str | None = None,
                   stop_event: threading.Event | None = None) -> DownloadInfo | None:
        """
        Retourne les métadonnées de l'URL sans télécharger.
        Détecte automatiquement les playlists.
        use_cookies : forcer l'utilisation des cookies (retry après erreur).
        referer / cookies : headers UGE (extraction guidée).
        stop_event  : permet d'interrompre l'attente entre deux tentatives.
        """
        # Une chaîne / playlist « envois » -> onglet Vidéos (récupère TOUTES
        # les vidéos ; l'endpoint playlist est plafonné à 100 par YouTube)
        norm_url = _normalize_youtube_channel_url(url)
        if norm_url != url:
            _log.info("URL chaîne normalisée vers l'onglet Vidéos : %s", norm_url)
            url = norm_url

        # Première passe légère pour détecter les playlists
        flat_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "js_runtimes": get_js_runtimes_opt(),
        }
        if self._settings.get("proxy_http"):
            flat_opts["proxy"] = self._settings["proxy_http"]

        # Headers UGE (referer du navigateur)
        headers = {}
        if self._settings.get("user_agent"):
            headers["User-Agent"] = self._settings["user_agent"]
        if referer:
            headers["Referer"] = referer
        if headers:
            flat_opts["http_headers"] = headers

        # Cookies UGE via cookie jar (inclut httpOnly)
        cookie_jar_path = None
        if cookies:
            cookie_jar_path = _write_cookie_jar(cookies, url)
            flat_opts["cookiefile"] = cookie_jar_path

        # Impersonation navigateur. youtubetab:skip=webpage force le chemin API
        # (au lieu de la page HTML), qui pagine plus loin sur les playlists
        # YouTube : ~200 entrées au lieu de 100 (limitation YouTube côté serveur
        # au-delà, cf. yt-dlp #11130 ; sans effet sur l'onglet Vidéos d'une chaîne
        # qui reste complet). skip=authcheck évite l'erreur « Playlists that
        # require authentication... » que déclenche skip=webpage sur certaines
        # playlists publiques.
        flat_opts["extractor_args"] = {
            "generic": {"impersonate": [""]},
            "youtubetab": {"skip": ["webpage", "authcheck"]},
        }

        # Cookies depuis le navigateur de l'utilisateur (si pas de cookies UGE)
        if not cookies and (use_cookies or _should_use_cookies(self._settings, url)):
            from app.core.cookies import apply_cookies
            apply_cookies(flat_opts, url)

        # Nouvelle tentative sur erreur transitoire. Sans cela, une simple
        # coupure de connexion pendant l'analyse suffisait a faire echouer le
        # telechargement, avec un message technique en anglais — alors que le
        # telechargement lui-meme, lui, retentait deja trois fois.
        _MAX_ATTEMPTS = 3
        try:
            for _attempt_no in range(1, _MAX_ATTEMPTS + 1):
                try:
                    return self._extract_info(download_id, url, flat_opts)
                except yt_dlp.utils.DownloadError as exc:
                    if (_attempt_no < _MAX_ATTEMPTS
                            and is_transient_error(str(exc))
                            and not (stop_event and stop_event.is_set())):
                        _log.warning(
                            "Analyse : erreur transitoire id=%s (tentative "
                            "%d/%d), nouvel essai : %s",
                            download_id, _attempt_no, _MAX_ATTEMPTS, exc)
                        _wait = 2.0
                        while _wait > 0 and not (stop_event and stop_event.is_set()):
                            time.sleep(0.2)
                            _wait -= 0.2
                        continue
                    _raise_download_error(
                        str(exc), exc, self._settings.get("download_folder", ""))
                except Exception as exc:
                    _raise_download_error(
                        str(exc), exc, self._settings.get("download_folder", ""))
            return None
        finally:
            if cookie_jar_path:
                try:
                    os.unlink(cookie_jar_path)
                except OSError:
                    pass

    def _extract_info(self, download_id: str, url: str,
                      flat_opts: dict) -> DownloadInfo | None:
        """Une passe d'analyse, sans nouvelle tentative ni nettoyage.

        Isole du reste pour que `fetch_info` puisse la rejouer telle quelle
        apres une coupure reseau.
        """
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None

        # Playlist détectée
        if info.get("_type") == "playlist" or info.get("entries") is not None:
            entries = list(info.get("entries") or [])
            # Filtrer les entrées None (vidéos privées/supprimées)
            entries = [e for e in entries if e]
            return DownloadInfo(
                download_id=download_id,
                url=url,
                title=info.get("title") or "Playlist",
                site=info.get("extractor_key") or "—",
                is_playlist=True,
                playlist_entries=entries,
                playlist_count=int(info.get("playlist_count") or 0),
            )

        # Vidéo unique — deuxième passe pour avoir les formats détaillés
        full_opts = dict(flat_opts)
        full_opts["extract_flat"] = False
        with yt_dlp.YoutubeDL(full_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None

        return DownloadInfo(
            download_id=download_id,
            url=url,
            title=info.get("title") or url,
            site=info.get("extractor_key") or info.get("extractor") or "—",
            fmt=_describe_format(info),
            duration=float(info.get("duration") or 0),
            raw_formats=info.get("formats") or [],
        )

    # ------------------------------------------------------------------
    # Téléchargement
    # ------------------------------------------------------------------

    def download(
        self,
        download_id: str,
        url: str,
        on_progress: OnProgressCallback,
        stop_event: threading.Event,
        pause_event: threading.Event | None = None,
        format_spec: str = "auto",
        format_id: str | None = None,
        audio_groups: list[list[str]] | None = None,
        expected_bytes: int = 0,
        title: str = "",
        referer: str | None = None,
        cookies: str | None = None,
        verbose: bool = False,
        on_verbose_log: Callable[[str], None] | None = None,
        playlist_title: str | None = None,
        playlist_number: int | None = None,
        use_cookies: bool = False,
        subtitles_override: bool | None = None,
        section: tuple[float, float] | None = None,
    ) -> str | None:
        """
        Télécharge l'URL dans le dossier configuré.
        format_spec    : "auto" | "mp4" | "mp3" | "m4a" | "manual"
        format_id      : format_id yt-dlp spécifique (mode manuel uniquement)
        verbose        : active les logs yt-dlp détaillés (mode diagnostic)
        on_verbose_log : appelé avec le log complet en fin de téléchargement
        playlist_title : titre de la playlist parente (pour l'organisation en sous-dossier)
        section        : (debut, fin) en secondes — ne telecharge que cet extrait
        """
        _log.info("Démarrage téléchargement id=%s url=%s format=%s", download_id, url, format_spec)
        dest = self._settings.get("download_folder", ".")

        # Garde-fou disque plein : inutile de telecharger vingt minutes pour
        # echouer a l'ecriture sur « No space left on device ». On refuse tout
        # de suite, avec un message qui dit ce qui manque. L'estimation
        # (`expected_bytes`) peut etre approximative : on ne bloque que si la
        # place manque franchement (taille estimee + _FREE_SPACE_MARGIN), pour
        # ne jamais refuser un telechargement qui serait passe.
        if expected_bytes > 0 and format_spec != "subtitles_only":
            _free = free_space_bytes(dest)
            _needed = expected_bytes + _FREE_SPACE_MARGIN
            if 0 <= _free < _needed:
                _log.error(
                    "Espace disque insuffisant id=%s : %d octets libres, %d requis",
                    download_id, _free, _needed)
                raise DownloadError(
                    not_enough_space_message(dest, _needed, _free))

        by_site     = self._settings.get("organize_by_site", False)
        by_playlist = self._settings.get("organize_by_playlist", False) and playlist_title

        # Sous-dossier relatif. L'outtmpl reste RELATIF (sans prefixe dest) : le
        # dossier final est passe via paths['home'] ci-dessous, ce qui permet
        # d'isoler les fichiers intermediaires (.part, fragments, .ytdl) dans
        # paths['temp'] sans que le fichier final n'y aille.
        if by_site and by_playlist:
            _rel_dir = f"%(extractor_key)s/{_sanitize_dirname(playlist_title)}"
        elif by_site:
            _rel_dir = "%(extractor_key)s"
        elif by_playlist:
            _rel_dir = _sanitize_dirname(playlist_title)
        else:
            _rel_dir = ""

        # Fichiers intermediaires isoles dans un dossier temp dedie a CE
        # telechargement, dans le dossier de destination (meme disque -> le
        # deplacement final est un renommage instantane). Supprime en fin de
        # traitement (succes, erreur OU annulation) : plus de .part orphelins.
        temp_dir = os.path.join(dest, ".da-tmp", download_id[:8])

        # Garde-fou Windows MAX_PATH (260 caracteres) : certains titres sont si
        # longs (podcasts Radio France dont le site duplique le titre,
        # descriptions completes de reels Facebook) que le chemin depasse la
        # limite et l'ecriture echoue ("Invalid argument" / Errno 22).
        #
        # On borne le TITRE directement dans l'outtmpl (`%(title).Ns`). NE PAS
        # se reposer sur la seule option `trim_file_name` de yt-dlp : elle
        # decoupe le nom avec `filename.rsplit('.', 2)` et prend donc tout ce
        # qui suit un point du titre pour une extension, qu'elle laisse
        # intacte. Un titre contenant un point (frequent : "...juste pour te.
        # #hashtag #hashtag...") n'etait donc pas tronque du tout.
        _final_prefix = os.path.join(dest, _rel_dir).replace("%(extractor_key)s", "x" * 30)
        # Le .part vit dans temp_dir : on borne selon le plus long des deux chemins.
        _eff_prefix = max(_final_prefix, temp_dir, key=len)
        _num_prefix = f"{playlist_number:02d} - " if playlist_number else ""
        _trim_len = max(
            50,
            240 - len(_eff_prefix) - len(_num_prefix) - len("/.m4a.part") - 4,
        )

        # Extrait : le suffixe evite d'ecraser un telechargement complet du meme
        # media, et distingue deux extraits differents de la meme video.
        _suffix = ""
        if section:
            _suffix = (f" [{_timecode_for_filename(section[0])}"
                       f" a {_timecode_for_filename(section[1])}]")
            _trim_len = max(50, _trim_len - len(_suffix))

        name_part = f"{_num_prefix}%(title).{_trim_len}s{_suffix}.%(ext)s"
        outtmpl = f"{_rel_dir}/{name_part}" if _rel_dir else name_part

        # Decoupe par chapitres : yt-dlp nomme les morceaux avec le gabarit
        # « chapter ». On partage le budget de caracteres entre le titre de la
        # video et celui du chapitre (meme garde-fou MAX_PATH que ci-dessus).
        # Un extrait ne se decoupe pas : l'utilisateur a deja choisi son passage.
        chapters_mode = self._settings.get("chapters_mode", "embed")
        split_chapters = chapters_mode == "split" and not section
        if split_chapters:
            _part = max(25, (_trim_len - 12) // 2)
            _chapter_name = (f"{_num_prefix}%(title).{_part}s"
                             f" - %(section_number)03d %(section_title).{_part}s.%(ext)s")
            outtmpl = {
                "default": outtmpl,
                "chapter": (f"{_rel_dir}/{_chapter_name}" if _rel_dir
                            else _chapter_name),
            }

        log_buf = io.StringIO() if verbose else None

        # yt-dlp télécharge les flux à la suite (vidéo puis audio, +1 par piste
        # audio supplémentaire) et la barre repartirait de zéro à chaque flux.
        # On estime le nombre de parties pour présenter UNE progression continue
        # 0->100 (auto-corrigée si l'estimation est trop basse). Estimation :
        #   - format manuel / sous-titres seuls : 1
        #   - audio seul (mp3/m4a) sans pistes choisies : 1
        #   - pistes audio choisies : N (audio seul) ou N+1 (avec vidéo)
        #   - vidéo standard : 2 (vidéo + audio à fusionner)
        audio_only = format_spec in ("mp3", "m4a", "amc_audio")
        if format_id or format_spec == "subtitles_only":
            total_parts = 1
        elif audio_groups:
            n = len([g for g in audio_groups if g])
            total_parts = n + (0 if audio_only else 1)
        elif audio_only:
            total_parts = 1
        else:
            total_parts = 2

        fragments = self._settings.get("concurrent_fragments", 1)

        # État partagé du hook de progression : permet de savoir, après coup, si
        # un vrai téléchargement a eu lieu (sinon = fichier déjà présent), et
        # quand le dernier événement hook a eu lieu (pour le moniteur disque).
        hook_state = {"files": set(), "completed": 0, "done_bytes": 0,
                      "any_download": False, "last_file": "", "last_hook_ts": 0.0,
                      "max_pct": 0.0, "processing": False}

        opts = {
            "outtmpl":        outtmpl,
            "paths":          {"home": dest, "temp": temp_dir},
            "trim_file_name": _trim_len,
            "quiet":          not verbose,
            "no_warnings":    not verbose,
            "verbose":        verbose,
            "progress_hooks": [self._make_hook(download_id, on_progress, stop_event,
                                               pause_event, total_parts, expected_bytes,
                                               hook_state)],
            "postprocessor_hooks": [self._make_pp_hook(download_id, on_progress, hook_state)],
            "js_runtimes":    get_js_runtimes_opt(),
            "concurrent_fragment_downloads": fragments if fragments > 1 else 1,
            # Résilience réseau : sur une connexion instable, un stall doit durer
            # 30 s avant de compter comme timeout, et yt-dlp reprend (depuis le
            # .part) jusqu'à 20 fois avant d'abandonner. Évite qu'un « Read timed
            # out » transitoire remonte comme un échec fatal.
            "socket_timeout":   30,
            "retries":          20,
            "fragment_retries": 20,
        }

        if verbose and log_buf is not None:
            opts["logger"] = _StringLogger(log_buf)

        if self._settings.get("proxy_http"):
            opts["proxy"] = self._settings["proxy_http"]

        ratelimit = self._settings.get("ratelimit_bytes", 0)
        if ratelimit and ratelimit > 0:
            opts["ratelimit"] = ratelimit

        # Headers supplémentaires (provenant de l'UGE)
        headers = {}
        if self._settings.get("user_agent"):
            headers["User-Agent"] = self._settings["user_agent"]
        if referer:
            headers["Referer"] = referer
        if headers:
            opts["http_headers"] = headers

        opts["ffmpeg_location"] = get_ffmpeg_path(self._settings)

        # Cookies UGE via cookie jar (inclut httpOnly)
        cookie_jar_path = None
        if cookies:
            cookie_jar_path = _write_cookie_jar(cookies, url)
            opts["cookiefile"] = cookie_jar_path

        # Impersonation navigateur pour contourner Cloudflare / HTTP/2 obligatoire
        opts["extractor_args"] = {"generic": {"impersonate": [""]}}

        # Cookies depuis le navigateur de l'utilisateur (si pas de cookies UGE)
        if not cookies and (use_cookies or _should_use_cookies(self._settings, url)):
            from app.core.cookies import apply_cookies
            apply_cookies(opts, url)

        # Override des sous-titres pour ce téléchargement
        eff_settings = dict(self._settings)
        if subtitles_override is not None:
            eff_settings["auto_subtitles"] = subtitles_override
        if format_spec == "subtitles_only":
            eff_settings["auto_subtitles"] = True
            opts["skip_download"] = True

        # Extrait : yt-dlp ne recupere que l'intervalle demande.
        # `force_keyframes_at_cuts` est indispensable ici — sans lui le debut
        # est recale sur l'image cle precedente (mesure : 5 s -> 12 s demandes
        # donnaient 12 s de fichier au lieu de 7). L'utilisateur qui a saisi un
        # moment precis doit obtenir ce moment ; le reencodage autour des coupes
        # coute un peu de temps, mais seule la portion extraite est traitee.
        if section:
            opts["download_ranges"] = yt_dlp.utils.download_range_func(
                [], [(section[0], section[1])])
            opts["force_keyframes_at_cuts"] = True

        _apply_format(opts, format_spec, format_id, audio_groups)
        _apply_subtitles(opts, eff_settings)
        # Apres les sous-titres : l'ordre de la liste est l'ordre d'execution,
        # et les metadonnees doivent etre ecrites une fois la conversion audio
        # et l'incrustation des sous-titres passees.
        embed_thumb, _thumb_ext = _apply_metadata(
            opts, eff_settings, format_spec, format_id)

        # Options yt-dlp supplémentaires (raw) : drapeaux booléens uniquement
        # (ex. --no-mtime, --write-thumbnail). On protege les options que l'appli
        # construit deliberement : sans ca, une saisie comme « --format » mettrait
        # opts["format"] = True et casserait le telechargement.
        for extra in self._settings.get("ytdlp_extra_opts", []):
            if extra.startswith("--"):
                key = extra.lstrip("-").replace("-", "_")
                if key in _PROTECTED_OPTS:
                    _log.warning("Option yt-dlp ignoree (protegee) : %s", extra)
                    continue
                opts[key] = True

        subtitle_warning: str | None = None

        burn_subs = (eff_settings.get("auto_subtitles") and
                     eff_settings.get("subtitle_mode") == "burn"
                     and not opts.get("skip_download"))

        def _run_download(active_opts: dict) -> None:
            with yt_dlp.YoutubeDL(active_opts) as ydl:
                if burn_subs:
                    ydl.add_post_processor(
                        _BurnSubtitlesPP(
                            downloader=ydl,
                            ffmpeg_path=get_ffmpeg_path(self._settings),
                        ),
                        when="post_process",
                    )
                if embed_thumb:
                    # Apres la conversion, les metadonnees et l'eventuelle
                    # incrustation des sous-titres (qui reencode la video) :
                    # la pochette s'ecrit dans le fichier deja finalise.
                    ydl.add_post_processor(
                        _SafeEmbedThumbnailPP(ydl, already_have_thumbnail=False),
                        when="post_process",
                    )
                if split_chapters:
                    # Tout a la fin : la decoupe copie les flux du fichier
                    # complet, donc les morceaux heritent des metadonnees et de
                    # la pochette deja ecrites. L'inverse produirait des
                    # chapitres nus.
                    ydl.add_post_processor(
                        _SplitChaptersPP(ydl), when="post_process")
                ydl.download([url])

        # Moniteur disque : filet de progression + annulation pour les flux qui
        # NE passent PAS par les progress_hooks (vidéo HLS prise en charge par
        # ffmpeg en interne = aucun hook pendant toute la vidéo). Comble la barre
        # via la taille des .part, et tue ffmpeg sur annulation.
        monitor_stop = threading.Event()
        monitor = self._make_disk_monitor(
            download_id, on_progress, temp_dir, expected_bytes,
            hook_state, stop_event, monitor_stop)
        monitor.start()

        try:
            try:
                # Réessai sur erreur transitoire : un 403/Forbidden sur une URL
                # YouTube (client de repli ANDROID_VR) est intermittent ; une
                # nouvelle extraction regénère une URL acceptée. Chaque appel à
                # _run_download relance une extraction complète et reprend le
                # .part. Borné à 3 tentatives (chaque essai = challenge JS).
                _MAX_ATTEMPTS = 3
                for _attempt_no in range(1, _MAX_ATTEMPTS + 1):
                    try:
                        _run_download(opts)
                        break
                    except yt_dlp.utils.DownloadError as exc:
                        if (_attempt_no < _MAX_ATTEMPTS
                                and is_transient_error(str(exc))
                                and not stop_event.is_set()):
                            _log.warning(
                                "Erreur transitoire id=%s (tentative %d/%d), "
                                "nouvelle extraction : %s",
                                download_id, _attempt_no, _MAX_ATTEMPTS, exc)
                            # Courte pause interruptible avant la ré-extraction
                            _wait = 2.0
                            while _wait > 0 and not stop_event.is_set():
                                time.sleep(0.2)
                                _wait -= 0.2
                            continue
                        raise
            except yt_dlp.utils.DownloadError as exc:
                err_msg = str(exc)
                if log_buf is not None and on_verbose_log is not None:
                    on_verbose_log(log_buf.getvalue())
                _log.error("Échec téléchargement id=%s url=%s — %s", download_id, url, err_msg)
                # Sous-titres inaccessibles → réessayer sans sous-titres,
                # mais conserver l'erreur comme warning reportable.
                if "subtitles" in err_msg.lower() and opts.get("writesubtitles"):
                    opts_retry = {k: v for k, v in opts.items()
                                  if k not in ("writesubtitles", "writeautomaticsub",
                                               "subtitleslangs", "subtitlesformat")}
                    if "postprocessors" in opts_retry:
                        opts_retry["postprocessors"] = [
                            pp for pp in opts_retry["postprocessors"]
                            if pp.get("key") != "FFmpegSubtitlesConvertor"
                        ]
                    try:
                        with yt_dlp.YoutubeDL(opts_retry) as ydl:
                            ydl.download([url])
                        subtitle_warning = err_msg
                    except yt_dlp.utils.DownloadError as exc2:
                        _raise_download_error(str(exc2), exc2, dest)
                    except Exception as exc2:
                        _raise_download_error(str(exc2), exc2, dest)
                else:
                    _raise_download_error(err_msg, exc, dest)
            except Exception as exc:
                if log_buf is not None and on_verbose_log is not None:
                    on_verbose_log(log_buf.getvalue())
                _log.error("Erreur inattendue id=%s url=%s — %s", download_id, url, exc)
                _raise_download_error(str(exc), exc, dest)
        finally:
            monitor_stop.set()
            if cookie_jar_path:
                try:
                    os.unlink(cookie_jar_path)
                except OSError:
                    pass
            # Menage des fichiers intermediaires (.part, fragments, .ytdl) : a ce
            # stade le telechargement est termine (succes/erreur/annulation), plus
            # rien n'ecrit dans temp_dir. Le fichier final est deja dans dest.
            shutil.rmtree(temp_dir, ignore_errors=True)
            # Retire le dossier parent .da-tmp s'il est vide (echoue sans bruit si
            # un autre telechargement concurrent y a encore un sous-dossier).
            try:
                os.rmdir(os.path.dirname(temp_dir))
            except OSError:
                pass

        if log_buf is not None and on_verbose_log is not None:
            on_verbose_log(log_buf.getvalue())

        already_present = _looks_already_present(
            skip_download=bool(opts.get("skip_download")),
            format_spec=format_spec,
            section=section,
            completed=hook_state["completed"],
            any_download=hook_state["any_download"],
        )
        if already_present:
            _log.info("Fichier déjà présent id=%s url=%s", download_id, url)
            on_progress(DownloadProgress(
                download_id=download_id,
                percent=100.0,
                status="already_downloaded",
                filepath=hook_state["last_file"],
            ))
            return subtitle_warning

        _log.info("Téléchargement terminé id=%s url=%s", download_id, url)
        return subtitle_warning

    # ------------------------------------------------------------------
    # Hook de progression
    # ------------------------------------------------------------------

    def _make_hook(
        self,
        download_id: str,
        on_progress: OnProgressCallback,
        stop_event: threading.Event,
        pause_event: threading.Event | None = None,
        total_parts: int = 1,
        expected_bytes: int = 0,
        state: dict | None = None,
    ):
        # Progression continue : yt-dlp télécharge les flux (vidéo, audio…) l'un
        # après l'autre, chacun de 0 à 100 %. Pour une barre qui se remplit UNE
        # seule fois :
        #   - si on connaît la taille totale estimée (`expected_bytes`), on
        #     pondère par les octets réels (la vidéo pesant l'essentiel, la barre
        #     colle au temps réel) ;
        #   - sinon, repli : on répartit chaque flux dans une tranche égale.
        parts = max(1, total_parts)
        if state is None:
            state = {"files": set(), "completed": 0, "done_bytes": 0}
        state.setdefault("any_download", False)
        state.setdefault("last_file", "")
        state.setdefault("last_hook_ts", 0.0)
        state.setdefault("max_pct", 0.0)

        def _monotonic(pct: float) -> float:
            # La barre ne doit jamais reculer : un flux peut se terminer sans
            # hook 'finished' (vidéo HLS via ffmpeg) → done_bytes ne le compte
            # pas et le flux suivant recalculerait un pourcentage plus bas.
            pct = max(pct, state["max_pct"])
            state["max_pct"] = pct
            return pct

        def _pct(d: dict) -> float:
            try:
                return float(d.get("_percent_str", "0%").strip().replace("%", ""))
            except ValueError:
                return 0.0

        def _part_equal_pct(d: dict) -> float:
            tmpf = d.get("tmpfilename") or d.get("filename") or ""
            if tmpf:
                state["files"].add(tmpf)
            idx = max(1, len(state["files"]))
            denom = max(parts, idx)
            return ((idx - 1) + _pct(d) / 100.0) / denom * 100.0

        def hook(d: dict) -> None:
            # Pause : bloquer jusqu'à reprise
            if pause_event:
                while pause_event.is_set():
                    if stop_event.is_set():
                        raise yt_dlp.utils.DownloadError(_("Annulé par l'utilisateur"))
                    time.sleep(0.1)
            if stop_event.is_set():
                raise yt_dlp.utils.DownloadError(_("Annulé par l'utilisateur"))

            state["last_hook_ts"] = time.monotonic()
            status = d.get("status")
            if status == "downloading":
                state["any_download"] = True
                if expected_bytes > 0:
                    cur = d.get("downloaded_bytes") or 0
                    pct = min(99.5, (state["done_bytes"] + cur) / expected_bytes * 100.0)
                else:
                    pct = _part_equal_pct(d)
                pct = _monotonic(pct)
                on_progress(DownloadProgress(
                    download_id=download_id,
                    percent=pct,
                    speed=d.get("_speed_str", "").strip(),
                    size=d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str") or "",
                    status="downloading",
                ))
            elif status == "finished":
                state["completed"] += 1
                if expected_bytes > 0:
                    state["done_bytes"] += d.get("total_bytes") or d.get("downloaded_bytes") or 0
                filename = d.get("filename", "") or ""
                if filename:
                    state["last_file"] = filename
                if state["completed"] >= parts:
                    # Toutes les parties estimées sont faites -> 100 %.
                    on_progress(DownloadProgress(
                        download_id=download_id,
                        percent=100.0,
                        status="finished",
                        filepath=filename,
                    ))
                else:
                    # Une partie finie, pas l'ensemble : la barre continue, mais on
                    # capture quand même le chemin (status=downloading + filepath).
                    if expected_bytes > 0:
                        pct = min(99.5, state["done_bytes"] / expected_bytes * 100.0)
                    else:
                        denom = max(parts, state["completed"])
                        pct = state["completed"] / denom * 100.0
                    pct = _monotonic(pct)
                    on_progress(DownloadProgress(
                        download_id=download_id,
                        percent=pct,
                        status="downloading",
                        filepath=filename,
                    ))
        return hook

    def _make_pp_hook(self, download_id: str, on_progress: OnProgressCallback,
                      hook_state: dict):
        """Hook de post-traitement : signale « Traitement » pendant la fusion /
        conversion ffmpeg (muxing), après le téléchargement des flux.

        Pose `hook_state['processing']` pour que le moniteur disque cesse
        d'emettre des evenements « telechargement » (sinon, sans hook recent, il
        re-emettrait ~99 % toutes les 0,5 s et masquerait le statut « Traitement »
        pendant toute la fusion d'un gros fichier)."""
        def pp_hook(d: dict) -> None:
            if d.get("status") == "started":
                hook_state["processing"] = True
                on_progress(DownloadProgress(
                    download_id=download_id,
                    percent=100.0,
                    status="processing",
                ))
        return pp_hook

    def _make_disk_monitor(
        self,
        download_id: str,
        on_progress: OnProgressCallback,
        temp_dir: str,
        expected_bytes: int,
        hook_state: dict,
        stop_event: threading.Event,
        monitor_stop: threading.Event,
    ) -> threading.Thread:
        """Thread de surveillance disque. Deux rôles, pour les flux qui ne
        passent PAS par les progress_hooks (ex. vidéo HLS de france.tv prise en
        charge par ffmpeg en interne — aucun hook pendant toute la vidéo) :

        1. Progression de repli : tant qu'aucun hook n'a parlé récemment, somme
           la taille des fichiers `.part` de ce téléchargement et fait avancer la
           barre (pondérée par `expected_bytes`). S'efface dès que de vrais hooks
           arrivent (ex. l'audio DASH), pour ne pas se télescoper avec eux.
        2. Annulation : `stop_event` n'interrompt pas ffmpeg (le hook ne tourne
           pas) ; on tue alors les processus ffmpeg enfants.
        """
        def _kill_ffmpeg_children() -> None:
            try:
                import psutil
                me = psutil.Process()
                for child in me.children(recursive=True):
                    try:
                        if "ffmpeg" in (child.name() or "").lower():
                            child.kill()
                    except psutil.Error:
                        pass
            except Exception:
                pass

        def _disk_bytes() -> int:
            # temp_dir est dedie a CE telechargement (paths['temp']) : on somme
            # TOUS ses fichiers, pas seulement les .part. Crucial en multi-flux
            # (video + plusieurs pistes audio) : quand un flux se termine, son
            # fichier perd le suffixe .part ; en sommant tout le dossier, le total
            # continue de monter pendant les flux suivants au lieu de figer la
            # barre au pic du premier flux. (Le dossier etant litteral, glob n'a
            # pas le souci des composants commencant par un point.)
            total = 0
            for root, _dirs, files in os.walk(temp_dir):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass
            return total

        def run() -> None:
            killed = False
            while not monitor_stop.is_set():
                monitor_stop.wait(0.5)
                if stop_event.is_set() and not killed:
                    _kill_ffmpeg_children()
                    killed = True
                    continue
                # Repli progression : seulement si aucun hook récent (<2 s), qu'on
                # connaît la taille cible, et que la fusion ffmpeg n'a pas commence
                # (sinon on masquerait le statut « Traitement »).
                if expected_bytes <= 0 or hook_state.get("processing"):
                    continue
                if time.monotonic() - hook_state.get("last_hook_ts", 0.0) < 2.0:
                    continue
                # cur = octets deja sur le disque pour ce telechargement (flux
                # termines + en cours). On ne rajoute PAS done_bytes : ce serait
                # compter deux fois les flux finis (leur fichier est encore la).
                cur = _disk_bytes()
                if cur <= 0:
                    continue
                pct = min(99.0, cur / expected_bytes * 100.0)
                # Jamais en arrière (cf. _monotonic côté hook).
                pct = max(pct, hook_state.get("max_pct", 0.0))
                hook_state["max_pct"] = pct
                on_progress(DownloadProgress(
                    download_id=download_id,
                    percent=pct,
                    status="downloading",
                ))

        return threading.Thread(target=run, daemon=True)


# ------------------------------------------------------------------
# Helpers privés
# ------------------------------------------------------------------

def _describe_format(info: dict) -> str:
    ext = info.get("ext") or info.get("format_note") or ""
    height = info.get("height")
    if height:
        return f"{height}p {ext}".strip()
    return ext


def estimate_total_bytes(formats: list[dict], format_spec: str = "auto",
                         format_id: str | None = None,
                         audio_groups: list[list[str]] | None = None,
                         duration: float = 0.0) -> int:
    """Estime la taille totale (octets) du téléchargement à partir des formats
    yt-dlp, pour pondérer la barre de progression. Retourne 0 si inconnu (le
    hook retombe alors sur une répartition par tranches égales).

    Heuristique alignée sur les sélecteurs de `_apply_format` : meilleure vidéo
    (le plus gros format vidéo seule) + audio choisi(s) ; pour l'audio seul ou
    le format manuel, uniquement la piste concernée.

    `duration` : durée de la vidéo (s). Certains sites (france.tv) n'exposent
    aucun `filesize` ; on retombe alors sur débit × durée (tbr en kbit/s) pour
    une estimation suffisante à pondérer la barre.
    """
    if not formats:
        return 0

    def sz(f: dict | None) -> int:
        if not f:
            return 0
        s = int(f.get("filesize") or f.get("filesize_approx") or 0)
        if s:
            return s
        # Pas de taille annoncée : estimer via le débit moyen et la durée.
        tbr = f.get("tbr") or f.get("vbr") or f.get("abr") or 0
        if tbr and duration:
            return int(float(tbr) * 1000 / 8 * duration)
        return 0

    by_id = {f.get("format_id"): f for f in formats}

    if format_spec == "subtitles_only":
        return 0
    if format_id:
        return sz(by_id.get(format_id))

    video_only = [f for f in formats
                  if f.get("vcodec") not in (None, "none") and f.get("acodec") in (None, "none")]
    audio_only = [f for f in formats
                  if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
    progressive = [f for f in formats
                   if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")]

    want_audio_only = format_spec in ("mp3", "m4a", "amc_audio")
    total = 0

    # Audio
    if audio_groups:
        for group in audio_groups:
            for fid in group:
                s = sz(by_id.get(fid))
                if s:
                    total += s
                    break
    elif audio_only:
        total += max((sz(f) for f in audio_only), default=0)

    # Vidéo (sauf audio seul)
    if not want_audio_only:
        if video_only:
            total += max((sz(f) for f in video_only), default=0)
        elif not audio_groups and not audio_only and progressive:
            total += max((sz(f) for f in progressive), default=0)

    return total


def _apply_format(opts: dict, format_spec: str, format_id: str | None = None,
                  audio_groups: list[list[str]] | None = None) -> None:
    """Applique le format yt-dlp et les post-processeurs selon le choix.

    `audio_groups` : pistes audio choisies par l'utilisateur (sites
    personnalisés), chaque piste étant une liste d'ids équivalents
    (repli dash/hls). Plusieurs pistes => un seul fichier contenant tous les
    flux audio (l'utilisateur change de piste dans son lecteur). On garde la
    meilleure vidéo. Ignoré en mode manuel ou sous-titres seuls.
    """
    # Une piste -> « (id1/id2) » ; plusieurs pistes -> « (..)+(..) » (multi-flux).
    ag = None
    if audio_groups:
        parts = ["(" + "/".join(ids) + ")" for ids in audio_groups if ids]
        if parts:
            ag = "+".join(parts)
            if len(parts) > 1:
                # Autoriser plusieurs flux audio dans un seul fichier.
                opts["allow_multiple_audio_streams"] = True

    if format_id:
        # Format manuel spécifique
        opts["format"] = format_id
    elif format_spec == "mp3":
        opts["format"] = ag or "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif format_spec == "m4a":
        opts["format"] = ag or "bestaudio[ext=m4a]/bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }]
    elif format_spec == "mp4":
        if ag:
            # Qualité RÉELLE maximale : tri par résolution/fps/codec d'abord, puis,
            # à qualité strictement égale, on préfère le protocole DASH (« proto:
            # http_dash_segments »). Pourquoi : sur france.tv la marche HLS et la
            # marche DASH sont le MÊME encode 1080p (HLS = +12 % d'overhead TS), et
            # le HLS passe par ffmpeg en interne (aucune progression pendant la
            # vidéo + pas d'annulation). Comme la résolution prime, si une marche
            # HLS est réellement plus haute, elle gagne quand même (et le moniteur
            # disque prend alors le relais pour la barre).
            opts["format_sort"] = _CUSTOM_VIDEO_SORT
            opts["format"] = f"bestvideo[ext=mp4]+{ag}/bestvideo+{ag}/best"
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]
    elif format_spec == "amc_audio":
        # Audio original (codec natif), SANS réencodage : Access Media Converter
        # convertira depuis la source pour éviter une double perte de qualité.
        opts["format"] = ag or "bestaudio/best"
    elif format_spec == "amc_video":
        # Meilleur original (vidéo+audio), SANS réencodage : seule la fusion des
        # flux a lieu (sans perte). AMC fera la conversion ensuite.
        if ag:
            opts["format_sort"] = _CUSTOM_VIDEO_SORT
            opts["format"] = f"bestvideo+{ag}/best"
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bestvideo+bestaudio/best"
    elif format_spec == "subtitles_only":
        # Pas de format vidéo/audio — seuls les sous-titres seront écrits.
        # skip_download est déjà mis à True par l'appelant.
        pass
    elif ag:
        # Auto avec piste(s) audio choisie(s) — conteneur mp4 pour la compat.
        # Qualité réelle max (résolution d'abord) puis DASH à qualité égale :
        # cf. le commentaire détaillé dans la branche « mp4 » ci-dessus.
        opts["format_sort"] = _CUSTOM_VIDEO_SORT
        opts["format"] = f"bestvideo+{ag}/best"
        opts["merge_output_format"] = "mp4"
    else:
        # Auto : meilleure qualité disponible
        opts["format"] = "bestvideo+bestaudio/best"


def _apply_subtitles(opts: dict, settings: dict) -> None:
    """Ajoute les options de sous-titres selon les préférences."""
    if not settings.get("auto_subtitles"):
        return
    langs = settings.get("subtitle_langs", ["fr", "en"])
    opts["writesubtitles"]   = True
    opts["writeautomaticsub"] = True
    opts["subtitleslangs"]   = langs
    subfmt = settings.get("subtitle_format", "srt")
    if subfmt != "original":
        opts["subtitlesformat"] = subfmt
        opts.setdefault("postprocessors", []).append({
            "key":    "FFmpegSubtitlesConvertor",
            "format": subfmt,
        })
    mode = settings.get("subtitle_mode", "separate")
    if mode == "embed":
        opts.setdefault("postprocessors", []).append({
            "key": "FFmpegEmbedSubtitle",
            "already_have_subtitle": False,
        })


# Extensions dont on connait le conteneur final AVEC CERTITUDE et pour
# lesquelles yt-dlp sait ecrire une pochette. On n'ajoute le post-processeur
# que dans ces cas : en « auto », le conteneur issu de la fusion depend des
# flux (webm possible), et yt-dlp leve une erreur sur un conteneur non
# supporte — ce qui ferait echouer un telechargement pourtant reussi.
_THUMBNAIL_CONTAINERS = {"mp3", "m4a", "mp4"}


class _SafeEmbedThumbnailPP(yt_dlp.postprocessor.EmbedThumbnailPP):
    """Pochette « best effort ». Une image illisible, un conteneur inattendu ou
    un ffmpeg recalcitrant ne doivent JAMAIS transformer un telechargement
    reussi en echec : on avertit dans le log et on rend la main. L'image
    temporaire est signalee comme supprimable pour ne pas laisser de .webp ou
    de .jpg trainer a cote du fichier final."""

    def run(self, info):
        try:
            return super().run(info)
        except Exception as exc:
            _log.warning("Pochette non integree (%s) : %s",
                         info.get("ext", "?"), exc)
            leftovers = [
                t["filepath"] for t in (info.get("thumbnails") or [])
                if t.get("filepath") and os.path.exists(t["filepath"])
            ]
            return leftovers, info


def _target_ext(format_spec: str, format_id: str | None) -> str:
    """Extension du fichier final quand elle est certaine, sinon "". """
    if format_id or format_spec in ("subtitles_only", "amc_audio", "amc_video"):
        return ""
    if format_spec in ("mp3", "m4a", "mp4"):
        return format_spec
    # « auto » : conteneur decide a la fusion (mkv/webm/mp4) -> inconnu.
    return ""


def _apply_metadata(opts: dict, settings: dict, format_spec: str,
                    format_id: str | None) -> tuple[bool, str]:
    """Ecrit les metadonnees (titre, artiste, album, chapitres) et la pochette
    dans le fichier produit. Sans ca, un MP3 tire de YouTube arrive nu : le
    lecteur de l'utilisateur n'a que le nom de fichier a annoncer, et la
    bibliotheque ne peut ni trier ni regrouper.

    Retourne `(pochette_demandee, extension_cible)` — l'appelant instancie le
    post-processeur de pochette, qui doit passer APRES la conversion audio.
    """
    if not settings.get("embed_metadata", True) or opts.get("skip_download"):
        return False, ""

    # Metadonnees : toujours possibles, ffmpeg seul suffit (pas de ffprobe).
    # `add_chapters` pose les reperes de chapitres, precieux sur les longs
    # formats (conferences, concerts, emissions) : le lecteur annonce alors le
    # chapitre et permet d'y sauter. On les pose aussi avant une decoupe, pour
    # que chaque morceau connaisse le titre du chapitre dont il vient.
    opts.setdefault("postprocessors", []).append({
        "key": "FFmpegMetadata",
        "add_metadata": True,
        "add_chapters": settings.get("chapters_mode", "embed") != "ignore",
        "add_infojson": False,
    })

    ext = _target_ext(format_spec, format_id)
    if ext not in _THUMBNAIL_CONTAINERS:
        return False, ext
    # Il faut recuperer l'image pour pouvoir l'integrer. Elle est ecrite dans
    # le dossier temporaire du telechargement et supprimee apres integration.
    opts["writethumbnail"] = True
    return True, ext


def format_timecode(seconds: float) -> str:
    """Secondes -> "h:mm:ss" (ou "m:ss" en dessous d'une heure)."""
    total = round(max(seconds, 0.0))
    h, rest = divmod(total, 3600)
    m, sec = divmod(rest, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def parse_timecode(text: str) -> float:
    """ "1:23:45", "12:30", "90" -> secondes. Leve ValueError si illisible."""
    parts = (text or "").strip().replace(",", ".").split(":")
    if not 1 <= len(parts) <= 3 or any(not p.strip() for p in parts):
        raise ValueError(text)
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    if total < 0:
        raise ValueError(text)
    return total


def _timecode_for_filename(seconds: float) -> str:
    """Timecode utilisable dans un nom de fichier Windows (pas de « : »).
    Une fin non bornee (extrait « jusqu'au bout ») se lit « fin »."""
    if seconds == float("inf"):
        return _("fin")
    return format_timecode(seconds).replace(":", "-")


def _retag_chapters(chapters: list[dict], album: str) -> int:
    """Donne son propre titre a chaque fichier de chapitre.

    yt-dlp decoupe par copie de flux : chaque morceau hérite tel quel des tags
    du fichier entier, donc les onze chapitres s'annoncent tous sous le titre de
    la video. Au lecteur d'ecran, « un fichier par chapitre » perd alors tout
    son interet — le lecteur repete onze fois la meme chose.

    On rétablit une structure d'album : titre = nom du chapitre, album = titre
    de la video, piste = rang du chapitre. Le lecteur annonce alors « piste 5
    sur 11, L'interface de NotebookLM ».

    Les conteneurs Matroska/WebM ne sont pas réinscriptibles par mutagen : ils
    sont ignorés en silence (la video garde le nom de chapitre dans son nom de
    fichier). Retourne le nombre de fichiers effectivement retagues.
    """
    from mutagen.easyid3 import EasyID3
    from mutagen.easymp4 import EasyMP4
    from mutagen.id3 import ID3NoHeaderError

    lecteurs = {".mp3": EasyID3, ".m4a": EasyMP4, ".mp4": EasyMP4,
                ".m4b": EasyMP4}
    total = len(chapters)
    retagues = 0
    for rang, chapitre in enumerate(chapters, start=1):
        chemin = chapitre.get("filepath")
        titre = (chapitre.get("title") or "").strip()
        if not chemin or not titre or not os.path.exists(chemin):
            continue
        lecteur = lecteurs.get(os.path.splitext(chemin)[1].lower())
        if lecteur is None:
            continue
        try:
            try:
                tags = lecteur(chemin)
            except ID3NoHeaderError:
                tags = lecteur()
                tags.filename = chemin
            tags["title"] = titre
            if album:
                tags["album"] = album
            tags["tracknumber"] = f"{rang}/{total}"
            tags.save(chemin)
            retagues += 1
        except Exception as exc:            # un tag rate ne perd pas le fichier
            _log.warning("Chapitre %d : tags non ecrits (%s)", rang, exc)
    return retagues


class _SplitChaptersPP(yt_dlp.postprocessor.FFmpegSplitChaptersPP):
    """Decoupe en un fichier par chapitre, PUIS supprime le fichier entier.

    yt-dlp conserve l'original par defaut ; ici l'utilisateur a demande « un
    fichier par chapitre », garder les deux doublerait l'espace occupe sans
    qu'il l'ait demande. Si la video n'a pas de chapitres, la classe parente ne
    produit rien : on ne supprime alors surtout pas le seul fichier telecharge.
    """

    @staticmethod
    def stream_copy_opts(copy=True, *, ext=None):
        """Ne recopie pas la table des chapitres dans les morceaux.

        ffmpeg recale les reperes du fichier entier sur chaque extrait sans les
        elaguer : un morceau de 21 secondes se retrouvait a annoncer onze
        chapitres s'etendant jusqu'a 23 minutes. Or chaque morceau EST un
        chapitre — il n'a aucune liste a porter.
        """
        parent = yt_dlp.postprocessor.FFmpegPostProcessor.stream_copy_opts
        yield from parent(copy, ext=ext)
        yield from ("-map_chapters", "-1")

    def run(self, info):
        had_chapters = bool(info.get("chapters"))
        to_delete, info = super().run(info)
        if had_chapters and info.get("filepath"):
            chapters = info.get("chapters") or []
            written = [c.get("filepath") for c in chapters]
            if any(f and os.path.exists(f) for f in written):
                to_delete = [*to_delete, info["filepath"]]
                n = _retag_chapters(chapters, info.get("title") or "")
                if n:
                    self.to_screen(f"Titres de chapitres ecrits dans {n} fichier(s)")
        return to_delete, info


class _BurnSubtitlesPP(yt_dlp.postprocessor.PostProcessor):
    """Incruste les sous-titres dans la vidéo en ré-encodant via ffmpeg.

    Utilisé quand `subtitle_mode = "burn"`. Copie le fichier de sous-titres
    sous un nom sûr dans le dossier de la vidéo pour éviter les soucis
    d'échappement du filtre `subtitles=` de ffmpeg, lance ffmpeg, puis
    remplace la vidéo originale.
    """

    def __init__(self, downloader=None, ffmpeg_path: str = "ffmpeg"):
        super().__init__(downloader)
        self._ffmpeg_path = ffmpeg_path

    def run(self, info):
        import subprocess as sp
        from pathlib import Path

        video_path = info.get("filepath")
        subs = info.get("requested_subtitles") or {}
        if not video_path or not subs:
            return [], info

        sub_path = None
        for data in subs.values():
            if data and data.get("filepath"):
                sub_path = data["filepath"]
                break
        if not sub_path or not os.path.exists(sub_path):
            return [], info

        video_p = Path(video_path)
        sub_p   = Path(sub_path)
        safe_sub = video_p.parent / ("_burn_sub" + sub_p.suffix)
        out_path = video_p.with_name(video_p.stem + ".burn" + video_p.suffix)

        try:
            shutil.copy2(sub_path, safe_sub)
            cmd = [
                self._ffmpeg_path, "-y",
                "-i", video_p.name,
                "-vf", f"subtitles={safe_sub.name}",
                "-c:a", "copy",
                out_path.name,
            ]
            result = sp.run(cmd, cwd=str(video_p.parent),
                            capture_output=True, text=True)
            if result.returncode != 0:
                self.report_warning(
                    _("Incrustation des sous-titres échouée : {error}").format(
                        error=(result.stderr or "")[:300]
                    )
                )
                if out_path.exists():
                    try:
                        out_path.unlink()
                    except OSError:
                        pass
                return [], info
            os.replace(str(out_path), video_path)
        except Exception as exc:
            self.report_warning(_("Erreur incrustation : {error}").format(error=exc))
            return [], info
        finally:
            if safe_sub.exists():
                try:
                    safe_sub.unlink()
                except OSError:
                    pass

        return [sub_path], info


def _sanitize_dirname(name: str) -> str:
    """Supprime les caractères interdits dans les noms de dossiers Windows."""
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    return sanitized.strip('. ') or "Playlist"


class DownloadError(Exception):
    pass


class LoginRequiredError(DownloadError):
    """Échec parce que le site exige une connexion (adulte, privé, membres…).
    Déclenche le parcours de connexion guidée côté UI."""
    pass


class _StringLogger:
    """Logger yt-dlp qui capture toute la sortie dans un StringIO."""

    def __init__(self, buf: io.StringIO) -> None:
        self._buf = buf

    def debug(self, msg: str) -> None:
        self._buf.write(msg + "\n")

    def info(self, msg: str) -> None:
        self._buf.write(msg + "\n")

    def warning(self, msg: str) -> None:
        self._buf.write(f"WARNING: {msg}\n")

    def error(self, msg: str) -> None:
        self._buf.write(f"ERROR: {msg}\n")
