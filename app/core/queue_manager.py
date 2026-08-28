import logging
import threading
import uuid
from dataclasses import dataclass, field
from collections.abc import Callable

from app.core.downloader import (
    Downloader, DownloadError, DownloadInfo, DownloadProgress, LoginRequiredError,
    accepts_audio_only, estimate_total_bytes,
)

_log = logging.getLogger("downaccess.queue")


@dataclass
class QueueItem:
    download_id: str
    url: str
    format_spec: str = "auto"        # auto | mp4 | mp3 | m4a | manual
    format_id: str | None = None     # format_id yt-dlp (mode manuel)
    audio_groups: list[list[str]] | None = None  # pistes audio choisies (sites personnalisés)
    prefetched_info: DownloadInfo | None = None  # infos déjà extraites (évite une 2e analyse)
    referer: str | None = None       # Referer HTTP (UGE)
    cookies: str | None = None       # Cookies de session (UGE, document.cookie)
    playlist_title: str | None = None   # Titre de la playlist parente (organisation dossier)
    playlist_number: int | None = None # Numéro dans la playlist (1-based)
    use_cookies: bool = False          # Forcer les cookies navigateur (retry)
    skip_info: bool = False             # Passer fetch_info (URL interceptée avec token)
    subtitles_override: bool | None = None  # None = utiliser les préférences
    section: tuple[float, float] | None = None  # (début, fin) en secondes
                                        # = ne télécharger que cet extrait
    stop_event:  threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)


# Callbacks UI
OnInfoReady     = Callable[[DownloadInfo], None]
OnProgress      = Callable[[DownloadProgress], None]
OnComplete      = Callable[[str], None]           # download_id
OnError         = Callable[[str, str, bool], None]  # download_id, message, login_required
OnPlaylist      = Callable[[DownloadInfo], None]  # info avec is_playlist=True
OnWarning       = Callable[[str, str], None]      # download_id, message
PostToUI        = Callable[..., None]             # ex: wx.CallAfter


class QueueManager:
    """
    Gère la file de téléchargement.
    - Les téléchargements tournent dans des threads daemon séparés.
    - La communication vers l'UI passe par post_to_ui (injecté par l'appelant).
    """

    def __init__(
        self,
        settings: dict,
        post_to_ui:  PostToUI,
        on_info:     OnInfoReady,
        on_progress: OnProgress,
        on_complete: OnComplete,
        on_error:    OnError,
        on_playlist: OnPlaylist | None = None,
        on_warning:  OnWarning  | None = None,
    ):
        self._settings    = settings
        self._post        = post_to_ui
        self._on_info     = on_info
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error    = on_error
        self._on_playlist = on_playlist
        self._on_warning  = on_warning

        self._queue:   list[QueueItem]        = []
        self._active:  dict[str, QueueItem]   = {}   # download_id → item
        self._lock     = threading.Lock()

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    @property
    def max_concurrent(self) -> int:
        return self._settings.get("max_concurrent_downloads", 2)

    @property
    def active_count(self) -> int:
        """Nombre de téléchargements actuellement en cours (thread-safe)."""
        with self._lock:
            return len(self._active)

    def add(self, url: str, format_spec: str = "auto", format_id: str | None = None,
            audio_groups: list[list[str]] | None = None,
            prefetched_info: DownloadInfo | None = None,
            referer: str | None = None, cookies: str | None = None,
            playlist_title: str | None = None,
            playlist_number: int | None = None,
            use_cookies: bool = False,
            skip_info: bool = False,
            subtitles_override: bool | None = None,
            section: tuple[float, float] | None = None) -> str:
        """Ajoute une URL à la file. Retourne le download_id."""
        dl_id = str(uuid.uuid4())
        item = QueueItem(
            download_id=dl_id,
            url=url,
            format_spec=format_spec,
            format_id=format_id,
            audio_groups=audio_groups,
            prefetched_info=prefetched_info,
            referer=referer,
            cookies=cookies,
            playlist_title=playlist_title,
            playlist_number=playlist_number,
            use_cookies=use_cookies,
            skip_info=skip_info,
            subtitles_override=subtitles_override,
            section=section,
        )
        with self._lock:
            self._queue.append(item)
        _log.info("Ajout file id=%s url=%s format=%s", dl_id, url, format_spec)
        self._try_start_next()
        return dl_id

    def cancel(self, download_id: str) -> None:
        """Annule/supprime un téléchargement (en cours ou en attente)."""
        with self._lock:
            # En cours → signal d'arrêt
            if download_id in self._active:
                self._active[download_id].stop_event.set()
                return
            # En attente → retirer de la file
            self._queue = [i for i in self._queue if i.download_id != download_id]

    def pause(self, download_id: str) -> None:
        with self._lock:
            if download_id in self._active:
                self._active[download_id].pause_event.set()

    def resume(self, download_id: str) -> None:
        with self._lock:
            if download_id in self._active:
                self._active[download_id].pause_event.clear()

    def is_paused(self, download_id: str) -> bool:
        with self._lock:
            if download_id in self._active:
                return self._active[download_id].pause_event.is_set()
        return False

    def is_active(self, download_id: str) -> bool:
        """Retourne True si le téléchargement est en cours (actif)."""
        with self._lock:
            return download_id in self._active

    def move_up(self, download_id: str) -> bool:
        """Remonte un item en attente dans la file. Retourne True si déplacé."""
        with self._lock:
            ids = [i.download_id for i in self._queue]
            if download_id not in ids:
                return False
            idx = ids.index(download_id)
            if idx == 0:
                return False
            self._queue[idx], self._queue[idx - 1] = self._queue[idx - 1], self._queue[idx]
            return True

    def move_down(self, download_id: str) -> bool:
        """Descend un item en attente dans la file. Retourne True si déplacé."""
        with self._lock:
            ids = [i.download_id for i in self._queue]
            if download_id not in ids:
                return False
            idx = ids.index(download_id)
            if idx >= len(self._queue) - 1:
                return False
            self._queue[idx], self._queue[idx + 1] = self._queue[idx + 1], self._queue[idx]
            return True

    def cancel_all(self) -> None:
        with self._lock:
            for item in self._active.values():
                item.stop_event.set()
            self._queue.clear()

    def get_state(self) -> dict:
        """Retourne l'état courant de la file (thread-safe)."""
        with self._lock:
            return {
                "pending": [{"id": i.download_id, "url": i.url} for i in self._queue],
                "active":  [{"id": i.download_id, "url": i.url} for i in self._active.values()],
            }

    # ------------------------------------------------------------------
    # Démarrage des workers
    # ------------------------------------------------------------------

    def _try_start_next(self) -> None:
        with self._lock:
            while len(self._active) < self.max_concurrent and self._queue:
                item = self._queue.pop(0)
                self._active[item.download_id] = item
                t = threading.Thread(
                    target=self._worker,
                    args=(item,),
                    daemon=True,
                )
                t.start()

    def _worker(self, item: QueueItem) -> None:
        """Enveloppe robuste : quoi qu'il arrive, l'item est libéré (`_finish`)
        et signalé en erreur si une exception inattendue survient. Sans ça, une
        exception non prévue tuerait le thread sans appeler `_finish` -> créneau
        de concurrence perdu et ligne figée sur « Préparation »."""
        dl_id = item.download_id
        try:
            self._run_worker(item)
        except Exception as exc:
            _log.exception("Erreur inattendue worker id=%s", dl_id)
            if not item.stop_event.is_set():
                self._post(self._on_error, dl_id, str(exc),
                           isinstance(exc, LoginRequiredError))
        finally:
            self._finish(dl_id)

    def _run_worker(self, item: QueueItem) -> None:
        dl = Downloader(self._settings)
        dl_id = item.download_id
        _log.info("Démarrage worker id=%s url=%s", dl_id, item.url)

        # Signaler « Préparation » : entre le démarrage du worker et le premier
        # octet, l'analyse (fetch_info, manifestes signés type france.tv) peut
        # durer ; sans ça l'item resterait « En attente » comme s'il était bloqué.
        self._post(self._on_progress, DownloadProgress(download_id=dl_id, status="preparing"))

        # 1. Extraction des infos (skip si URL interceptée avec token)
        if item.skip_info:
            _log.info("Skip fetch_info (URL interceptée) id=%s", dl_id)
            info = DownloadInfo(
                download_id=dl_id,
                url=item.url,
                title=item.url.split("/")[-1].split("?")[0],
                site="generic",
            )
            self._post(self._on_info, info)
        elif item.prefetched_info is not None:
            # Infos déjà extraites (ex. dialogue de pistes audio) : on réutilise
            # pour éviter une 2e analyse (france.tv : manifeste lent).
            _log.info("Réutilisation des infos préextraites id=%s", dl_id)
            info = item.prefetched_info
            info.download_id = dl_id
            if info.is_playlist:
                self._post(self._on_playlist or self._on_info, info)
                return
            self._post(self._on_info, info)
        else:
            try:
                info = dl.fetch_info(dl_id, item.url, use_cookies=item.use_cookies,
                                     referer=item.referer, cookies=item.cookies,
                                     stop_event=item.stop_event,
                                     accept_audio_only=accepts_audio_only(
                                         item.format_spec, item.format_id))
                if not info:
                    return
                if info.is_playlist:
                    # Déléguer la gestion de la playlist à l'UI
                    _log.info("Playlist détectée id=%s url=%s", dl_id, item.url)
                    self._post(self._on_playlist or self._on_info, info)
                    return
                self._post(self._on_info, info)
            except DownloadError as exc:
                _log.error("Erreur fetch_info id=%s — %s", dl_id, exc)
                self._post(self._on_error, dl_id, str(exc),
                           isinstance(exc, LoginRequiredError))
                return

        if item.stop_event.is_set():
            _log.info("Annulé avant téléchargement id=%s", dl_id)
            return

        # 2. Téléchargement
        def on_progress(prog: DownloadProgress) -> None:
            self._post(self._on_progress, prog)

        # Estimation de la taille totale -> barre de progression pondérée
        expected_bytes = 0
        raw_formats = getattr(info, "raw_formats", None)
        if raw_formats:
            expected_bytes = estimate_total_bytes(
                raw_formats, item.format_spec, item.format_id, item.audio_groups,
                duration=getattr(info, "duration", 0.0))
            # Extrait : l'estimation porte sur la video entiere. Sans mise a
            # l'echelle, la barre plafonnerait a quelques pour cent et le
            # garde-fou d'espace disque reclamerait la place du fichier complet.
            duration = float(getattr(info, "duration", 0.0) or 0.0)
            if item.section and duration > 0:
                ratio = (item.section[1] - item.section[0]) / duration
                expected_bytes = int(expected_bytes * min(max(ratio, 0.0), 1.0))

        try:
            warning = dl.download(
                dl_id, item.url, on_progress, item.stop_event,
                pause_event=item.pause_event,
                format_spec=item.format_spec,
                format_id=item.format_id,
                audio_groups=item.audio_groups,
                expected_bytes=expected_bytes,
                title=getattr(info, "title", "") or "",
                referer=item.referer,
                cookies=item.cookies,
                playlist_title=item.playlist_title,
                playlist_number=item.playlist_number,
                use_cookies=item.use_cookies,
                subtitles_override=item.subtitles_override,
                section=item.section,
            )
            if warning and self._on_warning:
                self._post(self._on_warning, dl_id, warning)
            _log.info("Terminé avec succès id=%s url=%s", dl_id, item.url)
            self._post(self._on_complete, dl_id)
        except DownloadError as exc:
            if not item.stop_event.is_set():
                _log.error("Échec téléchargement id=%s — %s", dl_id, exc)
                self._post(self._on_error, dl_id, str(exc),
                           isinstance(exc, LoginRequiredError))
            else:
                _log.info("Annulé pendant téléchargement id=%s", dl_id)

    def _finish(self, download_id: str) -> None:
        with self._lock:
            self._active.pop(download_id, None)
        self._try_start_next()
