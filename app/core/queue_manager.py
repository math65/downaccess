import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from collections.abc import Callable

from app.core.downloader import (
    BotCheckError, Downloader, DownloadError, DownloadInfo, DownloadProgress,
    LoginRequiredError,
    accepts_audio_only, destination_unreachable, estimate_total_bytes,
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
    restore_attempts: int = 0           # reprises depuis une session precedente
                                        # (garde-fou boucle, voir queue_store)
    stop_event:  threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)


# Callbacks UI
OnInfoReady     = Callable[[DownloadInfo], None]
OnProgress      = Callable[[DownloadProgress], None]
OnComplete      = Callable[[str], None]           # download_id
OnError         = Callable[[str, str, bool], None]  # download_id, message, login_required
OnPlaylist      = Callable[[DownloadInfo], None]  # info avec is_playlist=True
OnWarning       = Callable[[str, str], None]      # download_id, message
OnChange        = Callable[[], None]              # la file a change (conservation)
OnHeld          = Callable[[str], None]           # dossier introuvable : file retenue
OnBotPause      = Callable[[float], None]         # controle anti-robot : pause (minutes)
OnBotResume     = Callable[[], None]              # fin de la pause anti-robot
OnRequeued      = Callable[[str], None]           # download_id remis en attente
PostToUI        = Callable[..., None]             # ex: wx.CallAfter

# Pause apres un controle anti-robot : duree de depart (reglage, en minutes),
# doublee a chaque nouveau controle tant qu'aucun telechargement lance apres
# la reprise n'a abouti, plafonnee a une heure.
DEFAULT_BOT_PAUSE_MINUTES = 5
MAX_BOT_PAUSE_MINUTES = 60


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
        on_change:   OnChange   | None = None,
        on_held:     OnHeld     | None = None,
        on_bot_pause:  OnBotPause  | None = None,
        on_bot_resume: OnBotResume | None = None,
        on_requeued:   OnRequeued  | None = None,
    ):
        self._settings    = settings
        self._post        = post_to_ui
        self._on_info     = on_info
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error    = on_error
        self._on_playlist = on_playlist
        self._on_warning  = on_warning
        # Appele des que le contenu de la file change, pour l'ecrire sur le
        # disque. Sans cela, seule une fermeture propre conservait la file :
        # une fenetre tuee a l'Alt+F4 la perdait entierement (rapport de Brad).
        self._on_change   = on_change
        # Dossier de telechargement introuvable (disque debranche) : la file
        # ne demarre plus rien. Sans cela, chaque video partait quand meme,
        # etait analysee sur le site pour rien — des centaines de requetes,
        # de quoi declencher le controle anti-robot — puis echouait au moment
        # d'ecrire (rapport de Brad, 0.2.3 : 1 300 videos, lecteur D: disparu).
        self._on_held     = on_held
        self._held        = False

        # Controle anti-robot (« confirm you're not a bot ») : la limite porte
        # sur l'adresse IP, et chaque nouvelle requete la prolonge. Continuer a
        # depiler la file, c'etait faire echouer toutes les videos suivantes
        # une a une, et entretenir le blocage (demande de Brad, 2026-11-07 :
        # « faire attendre le programme quelques minutes »). La file s'arrete,
        # les videos touchees repassent en attente, et tout repart seul.
        self._on_bot_pause  = on_bot_pause
        self._on_bot_resume = on_bot_resume
        self._on_requeued   = on_requeued
        self._pause_until   = 0.0          # time.monotonic() de la reprise
        self._pause_timer: threading.Timer | None = None
        self._pause_streak  = 0            # pauses d'affilee sans reussite
        self._pause_epoch   = 0            # numero de la derniere pause
        # Apres une pause, un seul telechargement repart d'abord, pour sonder
        # le site. Relancer tous les creneaux d'un coup faisait buter chacun
        # sur le controle deux secondes apres la reprise, et la pause doublait
        # aussitot (rapport de Brad, 2026-11-09 : « it checks a download then
        # goes straight back to the robot check »).
        self._probing       = False

        # Delai entre deux demarrages (reglage `delay_between_downloads`, en
        # secondes) : espacer les requetes vers le site, pour ne pas declencher
        # son controle anti-robot (demande de Brad, 2026-11-09).
        self._last_start: float | None = None
        self._spacing_timer: threading.Timer | None = None

        self._queue:   list[QueueItem]        = []
        self._active:  dict[str, QueueItem]   = {}   # download_id → item
        self._lock     = threading.Lock()

    def _notify_change(self) -> None:
        """Signale que la file a change. Ne leve jamais, et jamais sous verrou.

        Le callback relit la file (`unfinished()`), qui reprend `self._lock` :
        l'appeler verrou tenu bloquerait tout.
        """
        if self._on_change is None:
            return
        try:
            self._on_change()
        except Exception:
            _log.exception("Notification de changement de file en echec")

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

    @property
    def pending_count(self) -> int:
        """Nombre de téléchargements en attente de créneau (thread-safe)."""
        with self._lock:
            return len(self._queue)

    @property
    def is_idle(self) -> bool:
        """Vrai si plus rien ne tourne ni n'attend : la rafale est finie."""
        with self._lock:
            return not self._active and not self._queue

    @property
    def is_bot_paused(self) -> bool:
        """Vrai pendant la pause qui suit un controle anti-robot."""
        with self._lock:
            return self._pause_until > time.monotonic()

    @property
    def bot_pause_remaining(self) -> float:
        """Secondes restantes avant la reprise automatique (0 hors pause)."""
        with self._lock:
            return max(0.0, self._pause_until - time.monotonic())

    def resume_bot_pause(self) -> bool:
        """Leve la pause anti-robot tout de suite. Vrai s'il y en avait une."""
        with self._lock:
            if self._pause_until <= time.monotonic():
                return False
            if self._pause_timer is not None:
                self._pause_timer.cancel()
        self._end_bot_pause(announce=False)
        return True

    @property
    def is_probing(self) -> bool:
        """Vrai apres une pause anti-robot, tant que le telechargement-test
        n'a pas franchi l'analyse : la file ne tourne que sur un creneau."""
        with self._lock:
            return self._probing

    @property
    def start_delay(self) -> float:
        """Delai minimal entre deux demarrages (secondes, 0 = aucun)."""
        try:
            return max(0.0, float(self._settings.get("delay_between_downloads", 0)))
        except (TypeError, ValueError):
            return 0.0

    def stop_bot_pause_timer(self) -> None:
        """Arrete les minuteurs de la file sans toucher a son contenu
        (fermeture de l'application : ils ne doivent plus rien poster a une
        fenetre detruite)."""
        with self._lock:
            if self._pause_timer is not None:
                self._pause_timer.cancel()
                self._pause_timer = None
            if self._spacing_timer is not None:
                self._spacing_timer.cancel()
                self._spacing_timer = None

    def add(self, url: str, format_spec: str = "auto", format_id: str | None = None,
            audio_groups: list[list[str]] | None = None,
            prefetched_info: DownloadInfo | None = None,
            referer: str | None = None, cookies: str | None = None,
            playlist_title: str | None = None,
            playlist_number: int | None = None,
            use_cookies: bool = False,
            skip_info: bool = False,
            subtitles_override: bool | None = None,
            section: tuple[float, float] | None = None,
            restore_attempts: int = 0) -> str:
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
            restore_attempts=restore_attempts,
        )
        with self._lock:
            self._queue.append(item)
        _log.info("Ajout file id=%s url=%s format=%s", dl_id, url, format_spec)
        self._notify_change()
        self._try_start_next()
        return dl_id

    def unfinished(self) -> list[QueueItem]:
        """Téléchargements ni terminés ni annulés, en cours d'abord.

        Sert a conserver la file d'une session a l'autre : ce sont exactement
        ceux que l'utilisateur perdait en fermant l'application.
        """
        with self._lock:
            actifs = [i for i in self._active.values()
                      if not i.stop_event.is_set()]
            return actifs + list(self._queue)

    def restore(self, entrees: list[dict]) -> list[tuple[str, dict]]:
        """Remet en file des téléchargements conservés.

        Retourne les couples (download_id, entree) de ceux qui ont repris :
        l'appelant en a besoin pour afficher leur ligne dans la liste.

        Chaque entree passe par `add()` : elle repart donc exactement comme un
        ajout normal, analyse comprise — une adresse devenue invalide echoue
        proprement au lieu de ressusciter un etat incoherent.
        """
        ids = []
        for entree in entrees:
            try:
                ids.append((self.add(**entree), entree))
            except TypeError as exc:
                # Fichier ecrit par une version differente : on ignore l'entree
                # plutot que d'empecher le demarrage.
                _log.warning("Entree de file ignoree (%s) : %s", exc, entree)
        if ids:
            _log.info("File restauree : %d telechargement(s)", len(ids))
        return ids

    def cancel(self, download_id: str) -> None:
        """Annule/supprime un téléchargement (en cours ou en attente)."""
        with self._lock:
            # En cours → signal d'arrêt
            if download_id in self._active:
                self._active[download_id].stop_event.set()
            else:
                # En attente → retirer de la file
                self._queue = [i for i in self._queue
                               if i.download_id != download_id]
        # Annuler doit s'inscrire tout de suite sur le disque : sinon le
        # telechargement dont on ne voulait plus reviendrait au prochain
        # lancement.
        self._notify_change()

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
        self._notify_change()
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
        self._notify_change()
        return True

    def cancel_all(self) -> None:
        with self._lock:
            for item in self._active.values():
                item.stop_event.set()
            self._queue.clear()
            # Plus rien a reprendre : la pause n'a plus d'objet.
            if self._pause_timer is not None:
                self._pause_timer.cancel()
                self._pause_timer = None
            if self._spacing_timer is not None:
                self._spacing_timer.cancel()
                self._spacing_timer = None
            self._pause_until = 0.0
            self._probing = False
        self._notify_change()

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

    @property
    def is_held(self) -> bool:
        """Vrai si la file est retenue faute de dossier de destination."""
        return self._held

    def retry_held(self) -> bool:
        """Relance la file retenue si le dossier est revenu. Vrai si elle repart.

        Appele periodiquement par l'UI tant que la file est retenue, et apres
        un changement de dossier dans les Preferences.
        """
        if not self._held:
            return False
        self._try_start_next()
        return not self._held

    def _try_start_next(self) -> None:
        with self._lock:
            if self._pause_until > time.monotonic():
                return      # pause anti-robot : le minuteur relancera la file
            attente = bool(self._queue) and len(self._active) < self._slots()
        if attente:
            dossier = self._settings.get("download_folder", "")
            introuvable = destination_unreachable(dossier)
            vient_de_manquer = introuvable and not self._held
            self._held = introuvable
            if introuvable:
                if vient_de_manquer:
                    _log.warning("Dossier de destination introuvable, file retenue : %s",
                                 dossier)
                    if self._on_held:
                        self._post(self._on_held, dossier)
                return
        delai = self.start_delay
        with self._lock:
            while len(self._active) < self._slots() and self._queue:
                if delai > 0 and self._last_start is not None:
                    reste = self._last_start + delai - time.monotonic()
                    if reste > 0:
                        self._arm_spacing_timer(reste)
                        break
                item = self._queue.pop(0)
                self._active[item.download_id] = item
                self._last_start = time.monotonic()
                t = threading.Thread(
                    target=self._worker,
                    args=(item,),
                    daemon=True,
                )
                t.start()

    def _slots(self) -> int:
        """Creneaux ouverts : un seul pendant le sondage d'apres-pause.
        Appele verrou tenu."""
        return 1 if self._probing else max(1, int(self.max_concurrent))

    def _arm_spacing_timer(self, secondes: float) -> None:
        """Programme le prochain demarrage espace. Appele verrou tenu."""
        if self._spacing_timer is not None:
            return          # deja programme : il relancera la file
        self._spacing_timer = threading.Timer(secondes, self._on_spacing_timer)
        self._spacing_timer.daemon = True
        self._spacing_timer.start()

    def _on_spacing_timer(self) -> None:
        with self._lock:
            self._spacing_timer = None
        self._try_start_next()

    # ------------------------------------------------------------------
    # Pause apres un controle anti-robot
    # ------------------------------------------------------------------

    def _bot_pause_minutes(self) -> float:
        """Duree de depart de la pause (reglage). 0 = fonction desactivee."""
        try:
            return max(0.0, float(self._settings.get(
                "bot_check_pause_minutes", DEFAULT_BOT_PAUSE_MINUTES)))
        except (TypeError, ValueError):
            return float(DEFAULT_BOT_PAUSE_MINUTES)

    def _defer_for_bot_check(self, item: QueueItem) -> bool:
        """Remet l'item en tete de file et met la file en pause.

        Vrai si l'item a ete remis en attente : l'appelant ne signale alors
        pas d'erreur. Les telechargements deja partis qui butent ensuite sur
        le meme controle sont remis en attente sans relancer de pause.
        """
        minutes = self._bot_pause_minutes()
        if minutes <= 0:
            return False
        with self._lock:
            if item.stop_event.is_set():
                return False
            self._active.pop(item.download_id, None)
            item.pause_event.clear()
            self._queue.insert(0, item)
            maintenant = time.monotonic()
            deja = self._pause_until > maintenant
            duree = 0.0
            if not deja:
                # Un controle qui revient juste apres la reprise : le site
                # n'a pas encore leve sa limite, on attend deux fois plus.
                duree = min(minutes * (2 ** self._pause_streak),
                            float(MAX_BOT_PAUSE_MINUTES))
                self._pause_streak += 1
                self._pause_epoch += 1
                self._pause_until = maintenant + duree * 60
                self._pause_timer = threading.Timer(
                    duree * 60, self._end_bot_pause,
                    kwargs={"epoch": self._pause_epoch})
                self._pause_timer.daemon = True
                self._pause_timer.start()
        if deja:
            _log.info("Controle anti-robot pendant la pause, remis en attente id=%s",
                      item.download_id)
        else:
            _log.warning("Controle anti-robot : file en pause %.1f min (id=%s)",
                         duree, item.download_id)
        self._notify_change()
        if self._on_requeued:
            self._post(self._on_requeued, item.download_id)
        if not deja and self._on_bot_pause:
            self._post(self._on_bot_pause, duree)
        return True

    def _end_bot_pause(self, epoch: int | None = None, announce: bool = True) -> None:
        """Fin de la pause (minuteur, ou reprise demandee) : la file repart."""
        with self._lock:
            # Minuteur d'une pause deja levee a la main, puis remplacee par
            # une nouvelle : il ne doit pas lever celle-ci.
            if epoch is not None and epoch != self._pause_epoch:
                return
            self._pause_timer = None
            self._pause_until = 0.0
            # Un seul telechargement repart : s'il franchit l'analyse, le site
            # a leve sa limite et les autres creneaux se rouvrent.
            self._probing = True
            reste = bool(self._queue)
        _log.info("Fin de la pause anti-robot, la file repart")
        if announce and reste and self._on_bot_resume:
            self._post(self._on_bot_resume)
        self._try_start_next()

    def _note_success(self, epoch: int) -> None:
        """Un telechargement lance apres la derniere pause a abouti : le site
        a leve sa limite, la prochaine pause repartira de la duree de depart."""
        with self._lock:
            if epoch == self._pause_epoch:
                self._pause_streak = 0
        self._note_passed(epoch)

    def _note_passed(self, epoch: int) -> None:
        """Un telechargement lance apres la derniere pause a franchi l'analyse
        (les octets arrivent) : fin du sondage, tous les creneaux se rouvrent."""
        with self._lock:
            if not self._probing or epoch != self._pause_epoch:
                return
            self._probing = False
        _log.info("Le site repond de nouveau : la file reprend son rythme")
        self._try_start_next()

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
        epoch = self._pause_epoch
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
                if item.stop_event.is_set():
                    # Annulation : ce n'est pas une panne, on ne montre pas de
                    # message d'erreur a l'utilisateur qui vient de la demander.
                    _log.info("Analyse annulee id=%s", dl_id)
                    return
                if isinstance(exc, BotCheckError) and self._defer_for_bot_check(item):
                    return
                _log.error("Erreur fetch_info id=%s — %s", dl_id, exc)
                self._post(self._on_error, dl_id, str(exc),
                           isinstance(exc, LoginRequiredError))
                return

        if item.stop_event.is_set():
            _log.info("Annulé avant téléchargement id=%s", dl_id)
            return

        # 2. Téléchargement
        def on_progress(prog: DownloadProgress) -> None:
            if prog.status in ("downloading", "already_downloaded", "processing"):
                self._note_passed(epoch)
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
            self._note_success(epoch)
            self._post(self._on_complete, dl_id)
        except DownloadError as exc:
            if isinstance(exc, BotCheckError) and self._defer_for_bot_check(item):
                return
            if not item.stop_event.is_set():
                _log.error("Échec téléchargement id=%s — %s", dl_id, exc)
                self._post(self._on_error, dl_id, str(exc),
                           isinstance(exc, LoginRequiredError))
            else:
                _log.info("Annulé pendant téléchargement id=%s", dl_id)

    def _finish(self, download_id: str) -> None:
        """Libère le créneau d'un téléchargement terminé, abouti ou non.

        C'est ici que la file conservée maigrit : un téléchargement terminé
        n'a plus à être repris au prochain lancement.
        """
        with self._lock:
            self._active.pop(download_id, None)
        self._notify_change()
        self._try_start_next()
