import io
import logging
import os
import re
import tempfile
import time
import threading
from dataclasses import dataclass, field
from collections.abc import Callable
from urllib.parse import urlparse

import yt_dlp

from app.core.ffmpeg_utils import get_ffmpeg_path
from app.core.i18n import _translate as _

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


@dataclass
class DownloadInfo:
    download_id: str
    url: str
    title: str = ""
    site: str = ""
    fmt: str = ""
    raw_formats: list = field(default_factory=list)
    is_playlist: bool = False
    playlist_entries: list = field(default_factory=list)


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


def _humanize_error(msg: str) -> str:
    """Traduit certaines erreurs yt-dlp cryptiques en messages clairs et
    actionnables pour le grand public.

    Le texte d'origine reste disponible dans le log diagnostic ; ici on ne
    remplace que le message affiché à l'utilisateur dans le dialogue d'erreur.
    """
    low = msg.lower()

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


def _raise_download_error(raw_msg: str, cause: Exception) -> None:
    """Lève l'erreur du bon type : LoginRequiredError si une connexion
    aiderait, sinon DownloadError. Le message est reformulé pour l'utilisateur."""
    friendly = _humanize_error(raw_msg)
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
                   cookies: str | None = None) -> DownloadInfo | None:
        """
        Retourne les métadonnées de l'URL sans télécharger.
        Détecte automatiquement les playlists.
        use_cookies : forcer l'utilisation des cookies (retry après erreur).
        referer / cookies : headers UGE (extraction guidée).
        """
        # Première passe légère pour détecter les playlists
        flat_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "js_runtimes": {"node": {}},
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

        # Impersonation navigateur
        flat_opts["extractor_args"] = {"generic": {"impersonate": [""]}}

        # Cookies depuis le navigateur de l'utilisateur (si pas de cookies UGE)
        if not cookies and (use_cookies or _should_use_cookies(self._settings, url)):
            from app.core.cookies import apply_cookies
            apply_cookies(flat_opts, url)

        try:
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
                raw_formats=info.get("formats") or [],
            )
        except yt_dlp.utils.DownloadError as exc:
            _raise_download_error(str(exc), exc)
        except Exception as exc:
            _raise_download_error(str(exc), exc)
        finally:
            if cookie_jar_path:
                try:
                    os.unlink(cookie_jar_path)
                except OSError:
                    pass

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
        referer: str | None = None,
        cookies: str | None = None,
        verbose: bool = False,
        on_verbose_log: Callable[[str], None] | None = None,
        playlist_title: str | None = None,
        playlist_number: int | None = None,
        use_cookies: bool = False,
        subtitles_override: bool | None = None,
    ) -> str | None:
        """
        Télécharge l'URL dans le dossier configuré.
        format_spec    : "auto" | "mp4" | "mp3" | "m4a" | "manual"
        format_id      : format_id yt-dlp spécifique (mode manuel uniquement)
        verbose        : active les logs yt-dlp détaillés (mode diagnostic)
        on_verbose_log : appelé avec le log complet en fin de téléchargement
        playlist_title : titre de la playlist parente (pour l'organisation en sous-dossier)
        """
        _log.info("Démarrage téléchargement id=%s url=%s format=%s", download_id, url, format_spec)
        dest = self._settings.get("download_folder", ".")

        by_site     = self._settings.get("organize_by_site", False)
        by_playlist = self._settings.get("organize_by_playlist", False) and playlist_title

        if playlist_number:
            name_part = f"{playlist_number:02d} - %(title)s.%(ext)s"
        else:
            name_part = "%(title)s.%(ext)s"

        if by_site and by_playlist:
            pl_safe = _sanitize_dirname(playlist_title)
            outtmpl = f"{dest}/%(extractor_key)s/{pl_safe}/{name_part}"
        elif by_site:
            outtmpl = f"{dest}/%(extractor_key)s/{name_part}"
        elif by_playlist:
            pl_safe = _sanitize_dirname(playlist_title)
            outtmpl = f"{dest}/{pl_safe}/{name_part}"
        else:
            outtmpl = f"{dest}/{name_part}"

        # Garde-fou Windows MAX_PATH (260 caracteres) : certains titres sont
        # si longs (ex. podcasts Radio France dont le site duplique le titre)
        # que le chemin complet depasse la limite et yt-dlp echoue avec
        # "No such file or directory". On borne la longueur du nom de fichier
        # pour que le chemin reste sous la limite, quelle que soit la
        # profondeur du dossier de telechargement.
        _dir_prefix = outtmpl.rsplit("/", 1)[0].replace("%(extractor_key)s", "x" * 30)
        _trim_len = max(50, 240 - len(_dir_prefix) - len("/.m4a.part") - 4)

        log_buf = io.StringIO() if verbose else None

        fragments = self._settings.get("concurrent_fragments", 1)

        opts = {
            "outtmpl":        outtmpl,
            "trim_file_name": _trim_len,
            "quiet":          not verbose,
            "no_warnings":    not verbose,
            "verbose":        verbose,
            "progress_hooks": [self._make_hook(download_id, on_progress, stop_event, pause_event)],
            "js_runtimes":    {"node": {}},
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

        _apply_format(opts, format_spec, format_id)
        _apply_subtitles(opts, eff_settings)

        # Options yt-dlp supplémentaires (raw)
        for extra in self._settings.get("ytdlp_extra_opts", []):
            if extra.startswith("--"):
                key = extra.lstrip("-").replace("-", "_")
                opts[key] = True

        subtitle_warning: str | None = None

        burn_subs = (eff_settings.get("auto_subtitles") and
                     eff_settings.get("subtitle_mode") == "burn"
                     and not opts.get("skip_download"))

        try:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    if burn_subs:
                        ydl.add_post_processor(
                            _BurnSubtitlesPP(
                                downloader=ydl,
                                ffmpeg_path=get_ffmpeg_path(self._settings),
                            ),
                            when="post_process",
                        )
                    ydl.download([url])
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
                        _raise_download_error(str(exc2), exc2)
                    except Exception as exc2:
                        _raise_download_error(str(exc2), exc2)
                else:
                    _raise_download_error(err_msg, exc)
            except Exception as exc:
                if log_buf is not None and on_verbose_log is not None:
                    on_verbose_log(log_buf.getvalue())
                _log.error("Erreur inattendue id=%s url=%s — %s", download_id, url, exc)
                _raise_download_error(str(exc), exc)
        finally:
            if cookie_jar_path:
                try:
                    os.unlink(cookie_jar_path)
                except OSError:
                    pass

        if log_buf is not None and on_verbose_log is not None:
            on_verbose_log(log_buf.getvalue())

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
    ):
        def hook(d: dict) -> None:
            # Pause : bloquer jusqu'à reprise
            if pause_event:
                while pause_event.is_set():
                    if stop_event.is_set():
                        raise yt_dlp.utils.DownloadError(_("Annulé par l'utilisateur"))
                    time.sleep(0.1)
            if stop_event.is_set():
                raise yt_dlp.utils.DownloadError(_("Annulé par l'utilisateur"))

            status = d.get("status")
            if status == "downloading":
                pct   = d.get("_percent_str", "0%").strip().replace("%", "")
                speed = d.get("_speed_str", "").strip()
                total = d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str") or ""
                try:
                    percent = float(pct)
                except ValueError:
                    percent = 0.0
                on_progress(DownloadProgress(
                    download_id=download_id,
                    percent=percent,
                    speed=speed,
                    size=total,
                    status="downloading",
                ))
            elif status == "finished":
                on_progress(DownloadProgress(
                    download_id=download_id,
                    percent=100.0,
                    status="finished",
                    filepath=d.get("filename", "") or "",
                ))
        return hook


# ------------------------------------------------------------------
# Helpers privés
# ------------------------------------------------------------------

def _describe_format(info: dict) -> str:
    ext = info.get("ext") or info.get("format_note") or ""
    height = info.get("height")
    if height:
        return f"{height}p {ext}".strip()
    return ext


def _apply_format(opts: dict, format_spec: str, format_id: str | None = None) -> None:
    """Applique le format yt-dlp et les post-processeurs selon le choix."""
    if format_id:
        # Format manuel spécifique
        opts["format"] = format_id
    elif format_spec == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif format_spec == "m4a":
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }]
    elif format_spec == "mp4":
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]
    elif format_spec == "subtitles_only":
        # Pas de format vidéo/audio — seuls les sous-titres seront écrits.
        # skip_download est déjà mis à True par l'appelant.
        pass
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
        import shutil
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
