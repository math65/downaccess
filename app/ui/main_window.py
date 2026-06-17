import logging
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import wx

_log = logging.getLogger("downaccess.ui")

_URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)


# Cles internes (jamais traduites). search_dialog._TYPE_LABELS resout l'affichage.
_SEARCH_TYPE_ORDER = {"video": 0, "track": 0, "playlist": 1, "channel": 2}

# Filtres de type de la recherche YouTube (paramètre `sp` de la page de résultats).
# Permet de ne renvoyer qu'un type de résultat (vidéos / playlists / chaînes).
_YT_SEARCH_SP = {"video": "EgIQAQ==", "playlist": "EgIQAw==", "channel": "EgIQAg=="}


def _classify_search_entry(entry: dict, site_prefix: str) -> str:
    """Determine le type d'un resultat de recherche (cle interne)."""
    if site_prefix == "scsearch":
        return "track"
    ie_key = entry.get("ie_key") or ""
    url = entry.get("url") or ""
    if ie_key == "YoutubeTab":
        if "list=" in url or "/playlist" in url:
            return "playlist"
        return "channel"
    return "video"

from app.core import settings as cfg
from app.core import speech
from app.core import i18n
from app.core import updater
from app.core import app_updater
from app.core import announce
from app.core.downloader import DownloadInfo, DownloadProgress
from app.core.queue_manager import QueueManager
from app.ui.add_url_dialog import AddUrlDialog, FORMAT_MANUAL
from app.ui.announcement_dialog import AnnouncementDialog
from app.ui.download_list import (
    DownloadList,
    STATUS_PENDING,
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_DONE,
)
from app.ui.format_dialog import FormatDialog
from app.ui.playlist_dialog import PlaylistDialog
from app.ui.search_dialog import SearchDialog, SearchResultsDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.uge_dialog import UGEDialog
from app.ui.login_dialog import LoginDialog
from app.ui.login_required_dialog import LoginRequiredDialog
from app.ui.guided_login_dialog import GuidedLoginDialog
from app.ui.update_dialog import UpdateDialog
from app.ui.contact_dialog import ContactDialog
from app.ui.history_dialog import HistoryDialog
from app.core import history as history_log
from app.core.history import HistoryEntry
from app.ui.error_dialog import ErrorDialog
from app.ui.warning_dialog import WarningDialog
from app.ui.report_dialog import ReportDialog
from app.core import error_reporter
from app.core.downloader import Downloader

APP_NAME = "DownAccess"


def _is_bare_domain(url: str) -> bool:
    """Retourne True si l'URL est un domaine nu sans chemin vers un contenu."""
    try:
        parsed = urlparse(url)
        return not parsed.path.rstrip("/") and not parsed.query
    except Exception:
        return False

# IDs personnalisés pour les actions sans équivalent wx standard
ID_START        = wx.NewIdRef()
ID_PAUSE        = wx.NewIdRef()
ID_CANCEL       = wx.NewIdRef()
ID_CLEAR_ALL    = wx.NewIdRef()
ID_RETRY        = wx.NewIdRef()
ID_MOVE_UP      = wx.NewIdRef()
ID_MOVE_DOWN    = wx.NewIdRef()
ID_UGE          = wx.NewIdRef()
ID_LOGIN        = wx.NewIdRef()
ID_SHORTCUTS    = wx.NewIdRef()
ID_UPDATE_YDL   = wx.NewIdRef()
ID_CLIP_TOGGLE  = wx.NewIdRef()
ID_SEARCH       = wx.NewIdRef()
ID_UPDATE_APP   = wx.NewIdRef()
ID_CONTACT      = wx.NewIdRef()
ID_GITHUB       = wx.NewIdRef()
ID_IMPORT_LIST  = wx.NewIdRef()
ID_HISTORY      = wx.NewIdRef()
ID_USER_GUIDE   = wx.NewIdRef()


def _docs_dir() -> Path:
    """Dossier des guides HTML (embarques), en dev comme en frozen."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "docs"


class _AppDownloadDialog(wx.Frame):
    """
    Fenêtre de progression du téléchargement d'une mise à jour DownAccess.
    Non-modale pour ne pas bloquer l'UI. Reste au premier plan.
    """

    def __init__(self, parent, version: str):
        super().__init__(
            parent,
            title=_("Téléchargement de DownAccess {version}").format(version=version),
            style=(
                wx.DEFAULT_FRAME_STYLE
                & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX)
            ) | wx.STAY_ON_TOP,
            size=(420, 160),
        )
        # Fonction à appeler pour demander l'annulation (fournie par le caller
        # une fois le téléchargement lancé) ; voir set_cancel_handler.
        self._cancel_handler = None
        self._cancelling = False
        self._build_ui(version)
        self.CentreOnParent()
        # La croix / Alt+F4 doit annuler proprement, pas tuer le thread en cours.
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _build_ui(self, version: str) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._lbl = wx.StaticText(
            panel,
            label=_("Téléchargement de DownAccess {version}…").format(version=version),
        )
        self._gauge = wx.Gauge(
            panel, range=100,
            style=wx.GA_HORIZONTAL | wx.GA_SMOOTH,
            name=_("Progression du téléchargement"),
        )
        self._lbl_pct = wx.StaticText(panel, label="0 %")
        self._btn_cancel = wx.Button(panel, label=_("&Annuler"))
        self._btn_cancel.Bind(wx.EVT_BUTTON, self._on_cancel_btn)

        sizer.Add(self._lbl,       0, wx.ALL,                        12)
        sizer.Add(self._gauge,     0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self._lbl_pct,   0, wx.LEFT | wx.TOP,              12)
        sizer.Add(self._btn_cancel, 0, wx.ALL | wx.ALIGN_RIGHT,       12)
        panel.SetSizer(sizer)

        # Frame sizer pour que le panel remplisse correctement la frame
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)
        self.Layout()

    def set_cancel_handler(self, handler) -> None:
        """Enregistre la fonction à appeler pour demander l'annulation."""
        self._cancel_handler = handler

    def focus_gauge(self) -> None:
        """Donne le focus à la gauge pour que NVDA suive la progression."""
        self._gauge.SetFocus()

    def update(self, percent: float) -> None:
        pct = int(min(max(percent, 0), 100))
        self._gauge.SetValue(pct)
        self._lbl_pct.SetLabel(f"{pct} %")
        if pct >= 100:
            self._lbl.SetLabel(_("Installation en cours…"))
            speech.speak(_("Téléchargement terminé. Installation en cours."))
            # Trop tard pour annuler une fois l'installation lancée.
            self._btn_cancel.Enable(False)

    def _request_cancel(self) -> bool:
        """Demande l'annulation du téléchargement. Ne détruit pas la fenêtre :
        la fermeture effective vient du rappel on_cancel (cf. _on_app_dl_cancelled)
        une fois que le thread a bien arrêté et nettoyé le fichier partiel."""
        if self._cancelling or not self._cancel_handler:
            return False
        self._cancelling = True
        self._btn_cancel.Enable(False)
        self._lbl.SetLabel(_("Annulation en cours…"))
        self._cancel_handler()
        return True

    def _on_cancel_btn(self, _event) -> None:
        self._request_cancel()

    def _on_close(self, event) -> None:
        # Tant que le téléchargement tourne, la croix / Alt+F4 = Annuler.
        if self._request_cancel():
            event.Veto()  # on attend l'accusé de réception (on_cancel)
        else:
            event.Skip()


class _URLDropTarget(wx.TextDropTarget):
    """Accepte du texte glissé-déposé et le transmet au callback."""

    def __init__(self, on_drop):
        super().__init__()
        self._on_drop = on_drop

    def OnDropText(self, x, y, text):
        wx.CallAfter(self._on_drop, text)
        return True


class MainWindow(wx.Frame):
    def __init__(self, parent):
        super().__init__(
            parent,
            title=APP_NAME,
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.settings = cfg.load()
        self._build_ui()
        self._bind_events()
        self._init_queue()
        self._init_clipboard()
        self.Maximize()
        # Focus initial sur le message — NVDA lit son contenu directement
        wx.CallAfter(self.lbl_empty.SetFocus)

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    def _init_clipboard(self) -> None:
        self._clip_seen: set[str] = set() # URLs déjà ajoutées via surveillance
        self._clip_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_clip_tick, self._clip_timer)
        # Ignorer le contenu actuel du presse-papiers au démarrage
        self._clip_last: str = _clipboard_text()
        # Restaurer l'état de surveillance depuis les préférences
        if self.settings.get("clipboard_monitor", False):
            self.mi_clip_toggle.Check(True)
            self._clip_timer.Start(1500)  # vérif toutes les 1,5 s

    def _init_queue(self) -> None:
        # Stocke les données par download_id pour le retry
        self._dl_data: dict[str, dict] = {}
        # Progression courante par download_id (pour la gauge)
        self._progress: dict[str, float] = {}
        self._gauge_dl_id: str | None = None
        # Mise à jour yt-dlp en cours au démarrage → bloquer les téléchargements
        self._updater_running: bool = True
        self._pending_downloads: list[tuple[str, str, str | None, str | None]] = []
        self._queue = QueueManager(
            settings=self.settings,
            post_to_ui=wx.CallAfter,
            on_info=self._on_dl_info,
            on_progress=self._on_dl_progress,
            on_complete=self._on_dl_complete,
            on_error=self._on_dl_error,
            on_playlist=self._on_dl_playlist,
            on_warning=self._on_dl_warning,
        )

    def _announce_download(self, text: str, interrupt: bool = False) -> None:
        """Annonce vocale d'un evenement de telechargement, selon le reglage
        'download_announcements' :
          - always     : toujours annoncer
          - foreground : seulement si la fenetre DownAccess est au premier plan
          - never      : ne jamais annoncer
        L'info reste de toute facon visible (barre de statut + liste)."""
        mode = self.settings.get("download_announcements", "always")
        if mode == "never":
            return
        if mode == "foreground" and not self.IsActive():
            return
        speech.speak(text, interrupt=interrupt)

    def _on_dl_info(self, info: DownloadInfo) -> None:
        self.download_list.update_info(info.download_id, info.title, info.site, info.fmt)
        if info.download_id in self._dl_data:
            self._dl_data[info.download_id]["site"]  = info.site
            self._dl_data[info.download_id]["title"] = info.title
        title = info.title or info.url
        self._announce_download(_("Téléchargement démarré : {title}.").format(title=title))

    def _on_dl_progress(self, prog: DownloadProgress) -> None:
        self.download_list.update_progress(prog.download_id, prog.percent, prog.size)
        self._progress[prog.download_id] = prog.percent
        # La gauge suit le dernier download actif sauf si l'utilisateur
        # a sélectionné un autre item dans la liste
        if self._gauge_dl_id is None or self._gauge_dl_id == prog.download_id:
            self._update_gauge(prog.download_id, prog.percent)
        # Capture du chemin final pour l'historique
        if prog.status == "finished" and prog.filepath:
            data = self._dl_data.get(prog.download_id)
            if data is not None:
                data["filepath"] = prog.filepath

    def _on_dl_complete(self, download_id: str) -> None:
        self.download_list.complete_item(download_id)
        self._progress.pop(download_id, None)
        if self._gauge_dl_id == download_id:
            self._reset_gauge()
        self.set_status(_("Téléchargement terminé."))
        self._announce_download(_("Téléchargement terminé."), interrupt=False)
        dl_data = self._dl_data.get(download_id, {})
        self._log_history(dl_data, status="success")
        # Si c'était un retry avec cookies, proposer de mémoriser le site
        if dl_data.get("use_cookies"):
            self._propose_remember_cookie_site(dl_data.get("url", ""))
        # Ouvrir le dossier si tous les téléchargements sont terminés
        if self.settings.get("open_folder_when_done") and self._all_done():
            self._open_download_folder()

    def _on_diagnostic_recovered(self, download_id: str, filepath: str) -> None:
        """La relance de diagnostic (lancée pour le rapport d'erreur) a finalement
        réussi en reprenant le fichier partiel : l'échec initial était transitoire.
        On rétablit l'item en « terminé » et on signale que le fichier est bien là."""
        self.download_list.complete_item(download_id)
        self._progress.pop(download_id, None)
        data = self._dl_data.get(download_id)
        if data is not None and filepath:
            data["filepath"] = filepath
        self._log_history(self._dl_data.get(download_id, {}), status="success")
        self.set_status(_("Le téléchargement a finalement réussi : le fichier "
                          "est dans votre dossier de téléchargements."))
        self._announce_download(_("Le téléchargement a finalement réussi. Le fichier est "
                                  "dans votre dossier de téléchargements."))

    def _on_dl_error(self, download_id: str, message: str,
                     login_required: bool = False) -> None:
        self.download_list.error_item(download_id)
        self._progress.pop(download_id, None)
        if self._gauge_dl_id == download_id:
            self._reset_gauge()
        self.set_status(_("Erreur lors du téléchargement."))
        dl_data = self._dl_data.get(download_id, {})
        self._log_history(dl_data, status="failed", error=message)

        # Échec faute de connexion → parcours de connexion guidée.
        if login_required:
            if dl_data.get("use_cookies"):
                # Connexion déjà tentée et insuffisante (pas le bon compte,
                # ou contenu nécessitant un abonnement) → message final.
                self._login_failed_after_attempt(download_id)
            else:
                self._on_login_required(download_id)
            return

        dlg = ErrorDialog(self, message)
        dlg.ShowModal()
        if dlg.wants_report():
            self._start_error_report(download_id, message)
        dlg.Destroy()

    def _log_history(self, dl_data: dict, status: str, error: str = "") -> None:
        """Enregistre une entrée d'historique pour ce téléchargement."""
        if not dl_data or not dl_data.get("url"):
            return
        try:
            filepath = dl_data.get("filepath", "")
            file_size = 0
            if filepath:
                try:
                    file_size = os.path.getsize(filepath)
                except OSError:
                    file_size = 0
            history_log.add(HistoryEntry(
                url=dl_data.get("url", ""),
                title=dl_data.get("title", ""),
                site=dl_data.get("site", ""),
                format_spec=dl_data.get("format_spec", "auto"),
                format_id=dl_data.get("format_id"),
                filepath=filepath,
                file_size=file_size,
                status=status,
                error=error,
            ))
        except Exception:
            _log.exception("Impossible d'enregistrer l'entrée d'historique")

    def _on_show_history(self, _event) -> None:
        dlg = HistoryDialog(self, on_redownload=self._on_history_redownload)
        dlg.ShowModal()
        dlg.Destroy()
        wx.CallAfter(self.download_list.SetFocus)

    def _on_history_redownload(self, entry: HistoryEntry) -> None:
        """Callback : ré-ajoute une entrée de l'historique à la queue."""
        self._enqueue_url(
            entry.url,
            format_spec=entry.format_spec or "auto",
            format_id=entry.format_id,
        )

    def _retry_with_cookies(self, download_id: str) -> None:
        """Relance le téléchargement avec les cookies du navigateur."""
        data = self._dl_data.get(download_id)
        if not data:
            self.set_status(_("Impossible de réessayer : données introuvables."))
            return
        # Supprimer l'item échoué et relancer avec cookies
        self.download_list.remove_item(download_id)
        self._dl_data.pop(download_id, None)
        url = data["url"]
        dl_id = self._queue.add(
            url,
            format_spec=data.get("format_spec", "auto"),
            format_id=data.get("format_id"),
            referer=data.get("referer"),
            cookies=data.get("cookies"),
            playlist_title=data.get("playlist_title"),
            playlist_number=data.get("playlist_number"),
            use_cookies=True,
        )
        label = data.get("format_spec", "auto").upper()
        if label == "AUTO":
            label = _("Auto")
        self.download_list.add_item(dl_id, url, site="—", fmt=label)
        self._dl_data[dl_id] = {
            "url": url,
            "format_spec": data.get("format_spec", "auto"),
            "format_id": data.get("format_id"),
            "referer": data.get("referer"),
            "cookies": data.get("cookies"),
            "site": data.get("site", ""),
            "playlist_title": data.get("playlist_title"),
            "playlist_number": data.get("playlist_number"),
            "use_cookies": True,
        }
        self.set_count(self.download_list.count())
        self.set_status(_("Reprise du téléchargement après connexion..."))
        speech.speak(_("Reprise du téléchargement."))

    # ------------------------------------------------------------------
    # Parcours de connexion guidée (échec faute de connexion au site)
    # ------------------------------------------------------------------

    @staticmethod
    def _site_label(url: str) -> str:
        """Nom lisible du site à partir de l'URL (ex: 'YouTube')."""
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        known = {
            "youtube.com": "YouTube", "youtu.be": "YouTube",
            "vimeo.com": "Vimeo", "dailymotion.com": "Dailymotion",
            "twitch.tv": "Twitch", "facebook.com": "Facebook",
            "instagram.com": "Instagram", "tiktok.com": "TikTok",
            "twitter.com": "Twitter", "x.com": "X",
        }
        if host in known:
            return known[host]
        # Repli : domaine sans le TLD, première lettre en majuscule.
        base = host.split(".")[0] if host else ""
        return base.capitalize() if base else _("ce site")

    def _on_login_required(self, download_id: str) -> None:
        """Affiche le dialogue « Connexion nécessaire » puis, si l'utilisateur
        accepte, lance la connexion guidée."""
        data = self._dl_data.get(download_id, {})
        url = data.get("url", "")
        site = self._site_label(url)
        speech.speak(_("Connexion nécessaire pour télécharger cette vidéo {site}.").format(site=site))
        dlg = LoginRequiredDialog(self, site)
        dlg.ShowModal()
        wants = dlg.wants_login()
        dlg.Destroy()
        if wants:
            self._open_guided_login(download_id)
        else:
            wx.CallAfter(self.download_list.SetFocus)

    def _open_guided_login(self, download_id: str) -> None:
        """Ouvre le dialogue de connexion guidée (minimal) sur le site, puis
        relance le téléchargement automatiquement une fois connecté."""
        data = self._dl_data.get(download_id, {})
        url = data.get("url", "")
        parsed = urlparse(url)
        login_url = f"{parsed.scheme}://{parsed.hostname}" if parsed.hostname else url
        site = self._site_label(url)
        dlg = GuidedLoginDialog(
            self,
            site_url=login_url,
            site_name=site,
            on_done=lambda ok, did=download_id, u=url: self._guided_login_done(ok, did, u),
        )
        dlg.Show()

    def _guided_login_done(self, success: bool, download_id: str, url: str) -> None:
        """Callback de fin de connexion guidée : relance le téléchargement si
        la connexion a réussi, sinon redonne le focus à la liste."""
        if success:
            self._propose_remember_cookie_site(url)
            self._retry_with_cookies(download_id)
        else:
            wx.CallAfter(self.download_list.SetFocus)

    def _login_failed_after_attempt(self, download_id: str) -> None:
        """La connexion a été faite mais le téléchargement échoue toujours :
        mauvais compte, ou contenu nécessitant un abonnement/des droits."""
        data = self._dl_data.get(download_id, {})
        site = self._site_label(data.get("url", ""))
        speech.speak(_("La connexion n'a pas suffi pour télécharger cette vidéo."))
        dlg = wx.MessageDialog(
            self,
            _(
                "Vous êtes connecté, mais cette vidéo {site} n'a pas pu être "
                "téléchargée.\n\n"
                "Soit vous n'êtes pas connecté au bon compte, soit ce contenu "
                "nécessite un abonnement ou des droits que votre compte n'a pas.\n\n"
                "Voulez-vous réessayer de vous connecter ?"
            ).format(site=site),
            _("Connexion insuffisante"),
            wx.YES_NO | wx.ICON_WARNING,
        )
        retry = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        if retry:
            self._open_guided_login(download_id)
        else:
            wx.CallAfter(self.download_list.SetFocus)

    def _propose_remember_cookie_site(self, url: str) -> None:
        """Après une connexion réussie, mémorise le site silencieusement :
        les prochaines vidéos du même site passeront direct, sans dialogue."""
        if not url:
            return
        host = urlparse(url).hostname or ""
        if host.startswith("www."):
            host = host[4:]
        host = host.lower()
        if not host:
            return
        sites = self.settings.get("cookie_sites", [])
        if host in sites:
            return
        sites.append(host)
        self.settings["cookie_sites"] = sites
        from app.core import settings as cfg
        cfg.save(self.settings)
        site = self._site_label(url)
        self.set_status(_("Connexion à {site} mémorisée.").format(site=site))
        speech.speak(
            _("DownAccess se souviendra de votre connexion à {site} pour "
              "les prochaines vidéos.").format(site=site)
        )

    def _on_dl_warning(self, download_id: str, message: str) -> None:
        self.set_status(_("Téléchargement terminé avec avertissement."))
        self._announce_download(_("Téléchargement terminé avec avertissement."))
        dlg = WarningDialog(self, message)
        dlg.ShowModal()
        if dlg.wants_report():
            self._start_error_report(download_id, message)
        dlg.Destroy()

    def _start_error_report(self, download_id: str, error_message: str) -> None:
        """Avant de laisser l'utilisateur rédiger un rapport, vérifie que l'app
        est à jour : si une version plus récente existe, le bug est peut-être
        déjà corrigé — on bloque et on propose la mise à jour, sans faire perdre
        de temps à rédiger. Si GitHub est injoignable, on laisse passer (ne pas
        perdre le rapport d'un utilisateur hors-ligne)."""
        self.set_status(_("Vérification de la version…"))
        speech.speak(_("Vérification de la version."))

        def _on_checked(status: str, info: str, _notes: str) -> None:
            if status == "update_available":
                self._report_blocked_outdated(info)
            else:
                self._open_report_form(download_id, error_message)

        app_updater.check_for_update(
            on_done=lambda s, i, n: wx.CallAfter(_on_checked, s, i, n)
        )

    def _report_blocked_outdated(self, new_version: str) -> None:
        """Empêche l'envoi d'un rapport tant que l'app n'est pas à jour."""
        self.set_status(_("Mise à jour requise avant d'envoyer un rapport."))
        dlg = wx.MessageDialog(
            self,
            _(
                "Une version plus récente de DownAccess est disponible "
                "(version {version}).\n\n"
                "Votre problème est peut-être déjà corrigé. Merci de mettre à "
                "jour l'application, puis de réessayer si le problème persiste.\n\n"
                "Voulez-vous mettre à jour maintenant ?"
            ).format(version=new_version),
            _("Mise à jour requise"),
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        do_update = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        if do_update:
            self._on_update_app(None)
        else:
            wx.CallAfter(self.download_list.SetFocus)

    def _open_report_form(self, download_id: str, error_message: str) -> None:
        dl_data = self._dl_data.get(download_id, {})
        url         = dl_data.get("url", "")
        site        = dl_data.get("site", "")
        format_spec = dl_data.get("format_spec", "auto")
        format_id   = dl_data.get("format_id")
        referer     = dl_data.get("referer")
        cookies     = dl_data.get("cookies")

        import threading as _th

        def _on_confirmed(comment: str, email: str) -> None:
            if email:
                self.settings["user_email"] = email
                from app.core import settings as cfg
                cfg.save(self.settings)
            verbose_log_holder = []
            stop_evt  = _th.Event()
            pause_evt = _th.Event()

            def _run_verbose():
                log = []
                recovered = {"ok": False, "filepath": ""}

                def _diag_progress(p):
                    if p.status == "finished" and p.filepath:
                        recovered["filepath"] = p.filepath

                try:
                    downloader = Downloader(self.settings)
                    downloader.download(
                        download_id="diagnostic",
                        url=url,
                        on_progress=_diag_progress,
                        stop_event=stop_evt,
                        pause_event=pause_evt,
                        format_spec=format_spec,
                        format_id=format_id,
                        referer=referer,
                        cookies=cookies,
                        verbose=True,
                        on_verbose_log=lambda txt: log.append(txt),
                    )
                    # La relance de diagnostic reprend le .part laissé par l'échec.
                    # Si elle aboutit sans lever d'erreur, c'est que l'échec
                    # initial était transitoire (connexion instable) et que le
                    # fichier est bien présent → on rétablit l'item dans l'UI.
                    recovered["ok"] = True
                except Exception:
                    pass

                verbose = log[0] if log else ""
                if recovered["ok"]:
                    verbose = (
                        "[DownAccess] La relance de diagnostic a repris et "
                        "terminé le téléchargement : l'erreur initiale était "
                        "transitoire (connexion instable).\n\n" + verbose
                    )
                    wx.CallAfter(self._on_diagnostic_recovered,
                                 download_id, recovered["filepath"])
                verbose_log_holder.append(verbose)
                wx.CallAfter(_send_report)

            def _send_report():
                import sys
                import platform as _plat
                import locale as _locale
                import shutil as _shutil
                import subprocess as _sp

                # Préférences filtrées (sans données sensibles)
                _SENSITIVE = {"proxy_http", "proxy_socks", "user_agent", "user_email"}
                prefs = {k: v for k, v in self.settings.items() if k not in _SENSITIVE}

                # État de la file
                queue_state = self._queue.get_state()

                # Infos système étendues
                def _ffmpeg_ver() -> str:
                    try:
                        r = _sp.run(
                            [self.settings.get("ffmpeg_path", "ffmpeg"), "-version"],
                            capture_output=True, text=True, timeout=3,
                        )
                        return r.stdout.splitlines()[0] if r.returncode == 0 else "indisponible"
                    except Exception:
                        return "indisponible"

                try:
                    import psutil as _psutil
                    mem = _psutil.virtual_memory()
                    ram_available_mb = mem.available // 1_048_576
                    ram_total_mb     = mem.total     // 1_048_576
                except Exception:
                    ram_available_mb = -1
                    ram_total_mb     = -1

                # Édition Windows (Pro / Famille…) — best effort
                try:
                    os_edition = _plat.win32_edition() or "inconnue"
                except Exception:
                    os_edition = "inconnue"

                # Espace disque libre sur le dossier de téléchargement (cause
                # classique d'échec : disque plein)
                try:
                    usage = _shutil.disk_usage(self.settings.get("download_folder", "."))
                    disk_free_gb  = round(usage.free  / 1_073_741_824, 1)
                    disk_total_gb = round(usage.total / 1_073_741_824, 1)
                except Exception:
                    disk_free_gb  = -1
                    disk_total_gb = -1

                # Langue / locale du système
                try:
                    sys_locale = ".".join(filter(None, _locale.getlocale())) or "inconnue"
                except Exception:
                    sys_locale = "inconnue"

                system_info = {
                    "python":           sys.version,
                    "wxpython":         wx.version(),
                    "ffmpeg":           _ffmpeg_ver(),
                    "ram_available_mb": ram_available_mb,
                    "ram_total_mb":     ram_total_mb,
                    "os_platform":      _plat.platform(),
                    "os_edition":       os_edition,
                    "architecture":     _plat.machine(),
                    "cpu":              _plat.processor() or "inconnu",
                    "cpu_count":        os.cpu_count() or -1,
                    "disk_free_gb":     disk_free_gb,
                    "disk_total_gb":    disk_total_gb,
                    "system_locale":    sys_locale,
                    "app_language":     self.settings.get("language", "auto"),
                    "screen_reader":    speech.active_screen_reader(),
                    "frozen":           bool(getattr(sys, "frozen", False)),
                }

                report = error_reporter.build_report(
                    url=url,
                    site=site,
                    format_spec=format_spec,
                    error_message=error_message,
                    verbose_log=verbose_log_holder[0] if verbose_log_holder else "",
                    user_comment=comment,
                    email=email,
                    preferences=prefs,
                    queue_state=queue_state,
                    system_info=system_info,
                )
                error_reporter.send_report(
                    report,
                    on_done=lambda ok, msg: wx.CallAfter(_on_sent, ok, msg),
                )

            def _on_sent(success: bool, msg: str):
                report_dlg.set_done(success, msg)
                if success:
                    self.set_status(_("Rapport d'erreur envoyé."))
                else:
                    self.set_status(_("Échec de l'envoi du rapport."))

            _th.Thread(target=_run_verbose, daemon=True).start()

        report_dlg = ReportDialog(
            self, url=url, site=site, error_message=error_message,
            on_confirmed=_on_confirmed,
            saved_email=self.settings.get("user_email", ""),
        )
        report_dlg.ShowModal()
        report_dlg.Destroy()

    def _on_dl_playlist(self, info: DownloadInfo) -> None:
        """Playlist détectée — supprimer l'item placeholder puis, selon le cas,
        récupérer la liste complète via le navigateur (si yt-dlp est plafonné)
        ou afficher directement le dialogue de sélection."""
        self.download_list.remove_item(info.download_id)
        self._dl_data.pop(info.download_id, None)
        self.set_count(self.download_list.count())

        # Plafonné = YouTube annonce plus de vidéos que yt-dlp n'en a extraites.
        capped = info.playlist_count > len(info.playlist_entries)
        host = (urlparse(info.url).hostname or "").lower()
        is_youtube = host.endswith("youtube.com") or host.endswith("youtu.be")

        total = info.playlist_count if capped else len(info.playlist_entries)
        speech.speak(
            _("Playlist détectée : {title}. {count} vidéos.").format(
                title=info.title, count=total
            )
        )

        if capped and is_youtube:
            self._maybe_harvest_full_playlist(info)
        else:
            self._show_playlist_dialog(info)

    def _maybe_harvest_full_playlist(self, info: DownloadInfo) -> None:
        """Playlist plafonnée par YouTube : proposer (1ʳᵉ fois) puis, si l'option
        est mémorisée, récupérer automatiquement la liste complète via navigateur."""
        if self.settings.get("playlist_full_harvest_auto"):
            self._start_playlist_harvest(info)
            return

        dlg = wx.RichMessageDialog(
            self,
            _("Cette playlist contient {total} vidéos, mais YouTube n'en rend "
              "que {got} accessibles directement.\n\n"
              "Voulez-vous récupérer la liste complète via le navigateur ? "
              "Cela peut prendre un moment pour les grandes playlists.").format(
                total=info.playlist_count, got=len(info.playlist_entries)),
            _("Playlist incomplète"),
            wx.YES_NO | wx.ICON_QUESTION,
        )
        dlg.SetYesNoLabels(_("Récupérer la liste complète"),
                           _("Garder les premières"))
        dlg.ShowCheckBox(_("Toujours récupérer automatiquement (ne plus demander)"))
        answer = dlg.ShowModal()
        remember = dlg.IsCheckBoxChecked()
        dlg.Destroy()

        if answer == wx.ID_YES:
            if remember:
                self.settings["playlist_full_harvest_auto"] = True
                cfg.save(self.settings)
            self._start_playlist_harvest(info)
        else:
            self._show_playlist_dialog(info)

    def _start_playlist_harvest(self, info: DownloadInfo) -> None:
        """Lance la récolte navigateur dans un thread, avec dialogue de
        progression accessible. Le résultat repasse par `_on_harvest_done`."""
        import threading

        from app.ui.playlist_harvest_dialog import PlaylistHarvestDialog

        self._harvest_stop = False
        self._harvest_dlg = PlaylistHarvestDialog(
            self, info.title, info.playlist_count,
            on_cancel=lambda: setattr(self, "_harvest_stop", True),
        )
        self._harvest_dlg.Show()

        def work() -> None:
            from app.core import browser
            try:
                entries = browser.harvest_youtube_playlist(
                    info.url,
                    on_progress=lambda n: wx.CallAfter(self._on_harvest_progress, n),
                    should_stop=lambda: self._harvest_stop,
                )
                wx.CallAfter(self._on_harvest_done, info, entries, None)
            except Exception as exc:
                wx.CallAfter(self._on_harvest_done, info, None, exc)

        threading.Thread(target=work, daemon=True).start()

    def _on_harvest_progress(self, n: int) -> None:
        dlg = getattr(self, "_harvest_dlg", None)
        if dlg:
            dlg.set_progress(n)

    def _on_harvest_done(self, info: DownloadInfo, entries, exc) -> None:
        from app.core.browser import ConsentRequiredError

        dlg = getattr(self, "_harvest_dlg", None)
        self._harvest_dlg = None
        if dlg:
            try:
                dlg.Destroy()
            except Exception:
                pass

        # Consentement / connexion YouTube requis -> connexion guidée puis reprise.
        if isinstance(exc, ConsentRequiredError):
            self._harvest_consent_login(info)
            return

        if exc is not None:
            _log.error("Echec recolte playlist via navigateur — %s", exc)
            self.set_status(_("Récupération impossible. Liste partielle affichée."))
            self._show_playlist_dialog(info)
            return

        # Annulé ou rien récolté -> on garde la liste yt-dlp (les premières).
        if self._harvest_stop or not entries:
            self._show_playlist_dialog(info)
            return

        info.playlist_entries = entries
        info.playlist_count = len(entries)
        self._show_playlist_dialog(info)

    def _harvest_consent_login(self, info: DownloadInfo) -> None:
        """YouTube réclame d'accepter son consentement (cookies/conditions) avant
        de lister la playlist. On ouvre YouTube dans le navigateur dédié pour que
        l'utilisateur l'accepte, puis on relance la récolte. Pas besoin de compte
        pour une playlist publique — d'où un wording « consentement », pas « login »."""
        speech.speak(_("YouTube demande d'accepter ses conditions pour récupérer la playlist."))
        dlg = wx.MessageDialog(
            self,
            _("Pour récupérer la liste complète, DownAccess va ouvrir YouTube "
              "dans le navigateur.\n\n"
              "Acceptez les conditions affichées par YouTube (et connectez-vous "
              "si vous le souhaitez), puis revenez ici : la récupération "
              "reprendra automatiquement."),
            _("Une étape dans le navigateur"),
            wx.OK | wx.CANCEL | wx.ICON_INFORMATION,
        )
        dlg.SetOKCancelLabels(_("Ouvrir YouTube"), _("Annuler"))
        proceed = dlg.ShowModal() == wx.ID_OK
        dlg.Destroy()
        if not proceed:
            self._show_playlist_dialog(info)
            return
        gdlg = GuidedLoginDialog(
            self,
            site_url="https://www.youtube.com",
            site_name="YouTube",
            title=_("YouTube dans le navigateur"),
            intro=_(
                "DownAccess ouvre YouTube dans son navigateur.\n\n"
                "Acceptez les conditions affichées (et connectez-vous si vous le "
                "souhaitez), puis revenez ici et cliquez sur « J'ai terminé » : "
                "la récupération de la playlist reprendra automatiquement.\n\n"
                "Inutile de fermer le navigateur vous-même, DownAccess s'en charge."
            ),
            action_text=_(
                "Acceptez les conditions de YouTube dans le navigateur, puis "
                "cliquez sur « J'ai terminé »."
            ),
            on_done=lambda ok, i=info: (
                self._start_playlist_harvest(i) if ok
                else self._show_playlist_dialog(i)
            ),
        )
        gdlg.Show()

    def _show_playlist_dialog(self, info: DownloadInfo) -> None:
        """Affiche le dialogue de sélection des entrées et enfile la sélection."""
        from app.ui.playlist_dialog import NUMBER_ORIGINAL, NUMBER_SEQUENTIAL
        from app.core import settings as cfg

        default_num = self.settings.get("playlist_numbering", NUMBER_ORIGINAL)
        with PlaylistDialog(self, info.title, info.playlist_entries,
                            default_numbering=default_num) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                self.set_status(_("Téléchargement de playlist annulé."))
                return
            selected = dlg.get_selected_entries()
            numbering = dlg.get_numbering_mode()

        # Mémoriser le choix de numérotation
        if numbering != default_num:
            self.settings["playlist_numbering"] = numbering
            cfg.save(self.settings)

        fmt_choice = self._dl_data.get("__last_fmt__", "auto")
        for seq, (orig_idx, entry) in enumerate(selected, start=1):
            url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
            if not url:
                continue
            if numbering == NUMBER_ORIGINAL:
                num = orig_idx
            elif numbering == NUMBER_SEQUENTIAL:
                num = seq
            else:
                num = None
            self._enqueue_url(url, fmt_choice, playlist_title=info.title,
                              playlist_number=num)

        speech.speak(_("{count} vidéos ajoutées à la file.").format(count=len(selected)))

    def _update_gauge(self, dl_id: str, percent: float) -> None:
        self._gauge_dl_id = dl_id
        self.gauge.SetValue(int(percent))
        title = self._dl_data.get(dl_id, {}).get("title") or self._dl_data.get(dl_id, {}).get("url", "")
        self.lbl_gauge_title.SetLabel(title)

    def _reset_gauge(self) -> None:
        # Si un autre download est encore actif, lui passer la gauge
        for dl_id, pct in self._progress.items():
            self._update_gauge(dl_id, pct)
            return
        self._gauge_dl_id = None
        self.gauge.SetValue(0)
        self.lbl_gauge_title.SetLabel("")

    def _on_list_select(self, event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id and dl_id in self._progress:
            self._update_gauge(dl_id, self._progress[dl_id])
        event.Skip()

    def _all_done(self) -> bool:
        """Retourne True si aucun téléchargement n'est en cours ou en attente."""
        count = self.download_list.count()
        done  = self.download_list.count_by_status(STATUS_DONE)
        return count > 0 and done >= count

    def _open_download_folder(self) -> None:
        folder = self.settings.get("download_folder", "")
        if folder:
            subprocess.Popen(["explorer", folder])

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_menubar()
        self._build_toolbar()
        self._build_main_panel()
        self._build_statusbar()

    def _build_menubar(self) -> None:
        mb = wx.MenuBar()

        # ---- Fichier ----
        file_menu = wx.Menu()
        self.mi_add = file_menu.Append(
            wx.ID_NEW, _("&Ajouter URL...\tCtrl+N"),
            _("Ajouter un ou plusieurs URLs à télécharger"),
        )
        self.mi_uge = file_menu.Append(
            ID_UGE, _("Extraction &guidée...\tCtrl+G"),
            _("Ouvrir le navigateur intégré pour détecter les médias sur n'importe quelle page"),
        )
        self.mi_login = file_menu.Append(
            ID_LOGIN, _("Se &connecter à un site..."),
            _("Ouvrir un navigateur pour se connecter à un site et sauvegarder les cookies"),
        )
        self.mi_search = file_menu.Append(
            ID_SEARCH, _("&Rechercher...\tCtrl+F"),
            _("Rechercher des vidéos ou musiques sur YouTube, SoundCloud, etc."),
        )
        self.mi_import = file_menu.Append(
            ID_IMPORT_LIST, _("&Importer une liste d'URLs..."),
            _("Charger un fichier texte contenant une URL par ligne"),
        )
        file_menu.AppendSeparator()
        self.mi_open_folder = file_menu.Append(
            wx.ID_OPEN, _("&Ouvrir le dossier de destination\tCtrl+O"),
            _("Ouvrir le dossier de téléchargement dans l'Explorateur"),
        )
        file_menu.AppendSeparator()
        self.mi_prefs = file_menu.Append(
            wx.ID_PREFERENCES, _("&Préférences...\tCtrl+P"),
            _("Ouvrir les préférences"),
        )
        file_menu.AppendSeparator()
        self.mi_quit = file_menu.Append(
            wx.ID_EXIT, _("&Quitter\tAlt+F4"),
            _("Quitter DownAccess"),
        )
        mb.Append(file_menu, _("&Fichier"))

        # ---- Téléchargements ----
        dl_menu = wx.Menu()
        self.mi_start = dl_menu.Append(
            ID_START, _("Dé&marrer\tF5"),
            _("Démarrer les téléchargements en attente"),
        )
        self.mi_pause = dl_menu.Append(
            ID_PAUSE, _("&Pause / Reprendre\tSpace"),
            _("Mettre en pause ou reprendre le téléchargement sélectionné"),
        )
        self.mi_cancel = dl_menu.Append(
            ID_CANCEL, _("Annu&ler\tDelete"),
            _("Supprimer le téléchargement sélectionné"),
        )
        dl_menu.Append(
            ID_CLEAR_ALL, _("&Vider la liste\tShift+Delete"),
            _("Annuler tous les téléchargements et vider la liste"),
        )
        dl_menu.AppendSeparator()
        self.mi_retry = dl_menu.Append(
            ID_RETRY, _("&Réessayer\tF2"),
            _("Réessayer le téléchargement échoué sélectionné"),
        )
        dl_menu.AppendSeparator()
        self.mi_move_up = dl_menu.Append(
            ID_MOVE_UP, _("Mo&nter dans la file\tAlt+Up"),
            _("Déplacer l'item sélectionné vers le haut"),
        )
        self.mi_move_down = dl_menu.Append(
            ID_MOVE_DOWN, _("Descen&dre dans la file\tAlt+Down"),
            _("Déplacer l'item sélectionné vers le bas"),
        )
        dl_menu.AppendSeparator()
        self.mi_clip_toggle = dl_menu.AppendCheckItem(
            ID_CLIP_TOGGLE, _("&Surveiller le presse-papiers\tCtrl+Shift+V"),
            _("Détecter automatiquement les URLs copiées"),
        )
        dl_menu.AppendSeparator()
        self.mi_history = dl_menu.Append(
            ID_HISTORY, _("&Historique...\tCtrl+H"),
            _("Afficher l'historique des téléchargements"),
        )
        mb.Append(dl_menu, _("&Téléchargements"))

        # ---- Aide ----
        help_menu = wx.Menu()
        self.mi_user_guide = help_menu.Append(
            ID_USER_GUIDE, _("&Guide d'utilisation\tF1"),
            _("Ouvrir le guide d'utilisation dans le navigateur"),
        )
        self.mi_shortcuts = help_menu.Append(
            ID_SHORTCUTS, _("Raccourcis cla&vier"),
            _("Afficher la liste des raccourcis clavier"),
        )
        help_menu.AppendSeparator()
        self.mi_update_ydl = help_menu.Append(
            ID_UPDATE_YDL, _("Mettre à jour &yt-dlp"),
            _("Télécharger et installer la dernière version de yt-dlp"),
        )
        self.mi_update_app = help_menu.Append(
            ID_UPDATE_APP, _("Mettre à jour &DownAccess"),
            _("Vérifier et installer la dernière version de DownAccess"),
        )
        self.mi_contact = help_menu.Append(
            ID_CONTACT, _("&Contacter le support / Faire une suggestion"),
            _("Envoyer un message, une suggestion ou signaler un problème"),
        )
        self.mi_github = help_menu.Append(
            ID_GITHUB, _("Page Git&Hub du projet"),
            _("Ouvrir la page GitHub de DownAccess dans le navigateur"),
        )
        help_menu.AppendSeparator()
        self.mi_about = help_menu.Append(
            wx.ID_ABOUT, _("À &propos de DownAccess"),
            _("Informations sur DownAccess"),
        )
        mb.Append(help_menu, _("&Aide"))

        self.SetMenuBar(mb)

    def _build_toolbar(self) -> None:
        tb = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_TEXT | wx.TB_NOICONS)
        tb.AddTool(wx.ID_NEW,  _("Ajouter URL"), wx.NullBitmap, shortHelp=_("Ajouter URL (Ctrl+N)"))
        tb.AddSeparator()
        tb.AddTool(ID_START,  _("Démarrer"),   wx.NullBitmap, shortHelp=_("Démarrer (F5)"))
        tb.AddTool(ID_PAUSE,  _("Pause"),      wx.NullBitmap, shortHelp=_("Pause/Reprendre (Espace)"))
        tb.AddTool(ID_CANCEL, _("Annuler"),    wx.NullBitmap, shortHelp=_("Annuler (Suppr)"))
        tb.Realize()

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Message affiché quand la liste est vide.
        # TextCtrl read-only pour que NVDA lise directement le contenu au focus.
        self.lbl_empty = wx.TextCtrl(
            panel,
            value=_(
                "Aucun téléchargement pour le moment.\r\n\r\n"
                "Ajoutez une URL via le menu Fichier, collez-la depuis le "
                "presse-papiers, glissez-déposez du texte sur cette fenêtre, "
                "ou utilisez la recherche pour trouver des médias."
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,
        )
        self.lbl_empty.SetBackgroundColour(panel.GetBackgroundColour())
        # Le TextCtrl lecture seule capte Ctrl+V nativement (collage sans effet)
        # et empêche l'accélérateur global. On redirige Ctrl+V vers le collage
        # d'URL pour que la zone d'aide reste utilisable au clavier (NVDA).
        self.lbl_empty.Bind(wx.EVT_CHAR_HOOK, self._on_empty_char_hook)
        sizer.Add(self.lbl_empty, 1, wx.EXPAND | wx.ALL, 24)

        self.download_list = DownloadList(panel)
        sizer.Add(self.download_list, 1, wx.EXPAND | wx.ALL, 4)
        self.download_list.Hide()  # caché tant que la liste est vide

        # Barre de progression native
        prog_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_gauge_title = wx.StaticText(panel, label="", size=(220, -1),
                                             style=wx.ST_ELLIPSIZE_END)
        self.gauge = wx.Gauge(panel, range=100,
                              style=wx.GA_HORIZONTAL | wx.GA_SMOOTH,
                              name=_("Progression du téléchargement actif"))
        prog_sizer.Add(self.lbl_gauge_title, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        prog_sizer.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 6)
        sizer.Add(prog_sizer, 0, wx.EXPAND)

        panel.SetSizer(sizer)

        # Glisser-déposer d'URLs (texte) sur la fenêtre principale.
        panel.SetDropTarget(_URLDropTarget(self._on_url_dropped))
        self.lbl_empty.SetDropTarget(_URLDropTarget(self._on_url_dropped))
        self.download_list.SetDropTarget(_URLDropTarget(self._on_url_dropped))

    def _build_statusbar(self) -> None:
        self.statusbar = self.CreateStatusBar(2)
        self.statusbar.SetStatusWidths([-1, 220])
        self.statusbar.SetStatusText(_("Prêt"), 0)
        self.statusbar.SetStatusText(_("0 téléchargement(s)"), 1)

    # ------------------------------------------------------------------
    # Liaison des événements
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        self.Bind(wx.EVT_MENU, self._on_add_url,        id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self._on_uge,            id=ID_UGE)
        self.Bind(wx.EVT_MENU, self._on_login,          id=ID_LOGIN)
        self.Bind(wx.EVT_MENU, self._on_search,         id=ID_SEARCH)
        self.Bind(wx.EVT_MENU, self._on_open_folder,    id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self._on_preferences,    id=wx.ID_PREFERENCES)
        self.Bind(wx.EVT_MENU, self._on_quit,           id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self._on_start,          id=ID_START)
        self.Bind(wx.EVT_MENU, self._on_pause,          id=ID_PAUSE)
        self.Bind(wx.EVT_MENU, self._on_cancel,         id=ID_CANCEL)
        self.Bind(wx.EVT_MENU, self._on_clear_all,      id=ID_CLEAR_ALL)
        self.Bind(wx.EVT_MENU, self._on_retry,          id=ID_RETRY)
        self.Bind(wx.EVT_MENU, self._on_move_up,        id=ID_MOVE_UP)
        self.Bind(wx.EVT_MENU, self._on_move_down,      id=ID_MOVE_DOWN)
        self.Bind(wx.EVT_MENU, self._on_clip_toggle,    id=ID_CLIP_TOGGLE)
        self.Bind(wx.EVT_MENU, self._on_shortcuts,      id=ID_SHORTCUTS)
        self.Bind(wx.EVT_MENU, self._on_update_ytdlp,   id=ID_UPDATE_YDL)
        self.Bind(wx.EVT_MENU, self._on_update_app,     id=ID_UPDATE_APP)
        self.Bind(wx.EVT_MENU, self._on_contact,        id=ID_CONTACT)
        self.Bind(wx.EVT_MENU, self._on_github,         id=ID_GITHUB)
        self.Bind(wx.EVT_MENU, self._on_user_guide,     id=ID_USER_GUIDE)
        self.Bind(wx.EVT_MENU, self._on_import_urls,    id=ID_IMPORT_LIST)
        self.Bind(wx.EVT_MENU, self._on_show_history,   id=ID_HISTORY)
        self.Bind(wx.EVT_MENU, self._on_about,          id=wx.ID_ABOUT)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.download_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_list_select)
        # Ctrl+V global sur la fenêtre principale → coller URL directement
        accel = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord("V"), wx.ID_PASTE),
            (wx.ACCEL_ALT, wx.WXK_UP,   ID_MOVE_UP),
            (wx.ACCEL_ALT, wx.WXK_DOWN, ID_MOVE_DOWN),
        ])
        self.SetAcceleratorTable(accel)
        self.Bind(wx.EVT_MENU, self._on_paste_url, id=wx.ID_PASTE)

    # ------------------------------------------------------------------
    # Gestionnaires d'événements
    # ------------------------------------------------------------------

    def _on_search(self, _event) -> None:
        with SearchDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            query        = dlg.get_query()
            site_prefix  = dlg.get_site_prefix()
            site_label   = dlg.get_site_label()
            search_type  = dlg.get_search_type()
            n            = dlg.get_n()

        if site_prefix == "ytsearch" and search_type in _YT_SEARCH_SP:
            # Filtre par type via la page de résultats YouTube (paramètre `sp`).
            import urllib.parse
            search_url = "https://www.youtube.com/results?" + urllib.parse.urlencode(
                {"search_query": query, "sp": _YT_SEARCH_SP[search_type]})
        else:
            search_url = f"{site_prefix}{n}:{query}"
        self.set_status(_("Recherche en cours : {query}…").format(query=query))
        speech.speak(_("Recherche sur {site}…").format(site=site_label))

        import threading

        result = {}

        def fetch():
            try:
                import yt_dlp
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": True,
                    "skip_download": True,
                    "playlistend": n,
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(search_url, download=False)
                entries = [e for e in (info.get("entries") or []) if e] if info else []
                for e in entries:
                    e["_dl_type"] = _classify_search_entry(e, site_prefix)
                entries.sort(key=lambda e: _SEARCH_TYPE_ORDER.get(e.get("_dl_type", ""), 3))
                result["entries"] = entries
            except Exception as exc:
                result["error"] = str(exc)
            wx.CallAfter(self._on_search_done, site_label, result)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_search_done(self, site_label: str, result: dict) -> None:
        if "error" in result:
            self.set_status(_("Erreur lors de la recherche."))
            wx.MessageBox(
                _("Erreur de recherche :\n\n{error}").format(error=result["error"]),
                _("Erreur"), wx.OK | wx.ICON_ERROR,
            )
            return

        entries = result.get("entries", [])
        if not entries:
            self.set_status(_("Aucun résultat trouvé."))
            speech.speak(_("Aucun résultat trouvé."))
            return

        with SearchResultsDialog(self, site_label, entries,
                                  settings=self.settings) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                self.set_status(_("Recherche annulée."))
                return
            selected = dlg.get_selected_entries()
            fmt      = dlg.get_format()

        enqueued = 0
        for entry in selected:
            url = entry.get("webpage_url") or entry.get("url") or ""
            # yt-dlp peut retourner un ID nu sans schéma en mode extract_flat
            if url and not url.startswith("http"):
                ie_key = (entry.get("ie_key") or entry.get("extractor_key") or "").lower()
                vid_id = entry.get("id", "") or url
                if "youtube" in ie_key or not ie_key:
                    url = f"https://www.youtube.com/watch?v={vid_id}"
                else:
                    url = ""
            if url:
                self._enqueue_url(url, format_spec=fmt)
                enqueued += 1

        n = enqueued
        if n > 1:
            msg = _("{count} résultats ajoutés à la file.").format(count=n)
        else:
            msg = _("{count} résultat ajouté à la file.").format(count=n)
        self.set_status(msg)
        speech.speak(msg)

    def _on_uge(self, _event) -> None:
        # Dialogue d'explication à la première utilisation
        if not self.settings.get("_uge_intro_shown"):
            wx.MessageBox(
                _(
                    "L'extraction guidée ouvre votre navigateur (Chrome, Edge ou Brave) "
                    "à côté de DownAccess.\n\n"
                    "Naviguez sur le site et lancez la vidéo dans le navigateur.\n"
                    "Les médias détectés apparaîtront dans la fenêtre DownAccess.\n\n"
                    "Vous pourrez ensuite les ajouter à la file de téléchargement.\n\n"
                    "Note : les contenus protégés par DRM (Netflix, Disney+, Prime Video…) "
                    "ne sont pas pris en charge."
                ),
                _("Extraction guidée — Comment ça marche"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            self.settings["_uge_intro_shown"] = True
            cfg.save(self.settings)

        dlg = UGEDialog(
            self,
            on_add_url=lambda url, referer=None, cookies=None, skip_info=False:
                self._enqueue_url(url, referer=referer, cookies=cookies, skip_info=skip_info),
        )
        dlg.Show()

    def _on_login(self, _event) -> None:
        # Dialogue d'explication à la première utilisation
        if not self.settings.get("_login_intro_shown"):
            wx.MessageBox(
                _(
                    "Cette fonction ouvre un navigateur dédié à DownAccess pour vous\n"
                    "connecter à un site (par exemple YouTube).\n\n"
                    "Vous restez connecté une fois pour toutes : les vidéos réservées aux\n"
                    "personnes connectées pourront alors être téléchargées. Si un\n"
                    "téléchargement nécessite une connexion, DownAccess vous proposera\n"
                    "aussi de vous connecter au moment voulu.\n\n"
                    "Note : les contenus protégés par DRM (Netflix, Disney+, Prime Video…) "
                    "ne sont pas pris en charge."
                ),
                _("Connexion à un site — Comment ça marche"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            self.settings["_login_intro_shown"] = True
            cfg.save(self.settings)

        dlg = LoginDialog(self)
        dlg.Show()

    def _on_add_url(self, _event) -> None:
        default_fmt = self.settings.get("post_processing", "none")
        if default_fmt == "none":
            default_fmt = "auto"
        default_subs = self.settings.get("auto_subtitles", False)
        with AddUrlDialog(self, default_format=default_fmt,
                          default_subtitles=default_subs) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            urls       = dlg.get_urls()
            fmt_choice = dlg.get_format_choice()
            subs       = dlg.get_subtitles()

        if fmt_choice == FORMAT_MANUAL and len(urls) == 1:
            self._enqueue_with_format_selection(urls[0], subtitles_override=subs)
        else:
            for url in urls:
                self._enqueue_url(url, fmt_choice, subtitles_override=subs)

    def _ask_video_or_playlist(self, url: str) -> str | None:
        """
        URL contenant vidéo + playlist → demander à l'utilisateur.
        Retourne l'URL (éventuellement nettoyée), ou None si annulé.
        """
        dlg = wx.MessageDialog(
            self,
            _(
                "Cette URL contient une vidéo et une playlist.\n\n"
                "Voulez-vous télécharger la playlist entière\n"
                "ou uniquement cette vidéo ?"
            ),
            _("Vidéo ou playlist ?"),
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        dlg.SetYesNoCancelLabels(_("La playlist"), _("La vidéo"), _("Annuler"))
        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_CANCEL:
            return None

        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        if result == wx.ID_NO:
            # Vidéo seule → retirer le paramètre list= de l'URL
            params.pop("list", None)
            params.pop("index", None)
            clean_query = urlencode(params, doseq=True)
            return urlunparse(parsed._replace(query=clean_query))

        # Playlist → construire une URL playlist pure pour que yt-dlp
        # l'extraie comme playlist et non comme vidéo unique
        list_id = params.get("list", [None])[0]
        if list_id and "youtube" in (parsed.hostname or ""):
            return f"https://www.youtube.com/playlist?list={list_id}"
        return url

    def _enqueue_url(self, url: str, format_spec: str = "auto",
                     format_id: str | None = None,
                     referer: str | None = None,
                     cookies: str | None = None,
                     playlist_title: str | None = None,
                     playlist_number: int | None = None,
                     skip_info: bool = False,
                     subtitles_override: bool | None = None) -> None:
        # Détection URL mixte vidéo + playlist (ex: YouTube watch?v=...&list=...)
        if not playlist_title and "list=" in url and ("watch?" in url or "/watch/" in url):
            url = self._ask_video_or_playlist(url)
            if url is None:
                return

        # Si la mise à jour yt-dlp est en cours, mettre en attente
        if self._updater_running:
            self._pending_downloads.append((url, format_spec, format_id, playlist_title))
            self.set_status(_("URL en file d'attente — mise à jour yt-dlp en cours…"))
            speech.speak(
                _("URL ajoutée. Le téléchargement démarrera après la mise à jour de yt-dlp."),
                interrupt=False,
            )
            return
        dl_id = self._queue.add(url, format_spec=format_spec, format_id=format_id,
                                referer=referer, cookies=cookies,
                                playlist_title=playlist_title,
                                playlist_number=playlist_number,
                                skip_info=skip_info,
                                subtitles_override=subtitles_override)
        if format_spec == "auto":
            label = _("Auto")
        elif format_spec == "subtitles_only":
            label = _("Sous-titres")
        else:
            label = format_spec.upper()
        self.download_list.add_item(dl_id, url, site="—", fmt=label)
        # Stocker pour retry et rapport d'erreur
        self._dl_data[dl_id] = {
            "url": url, "format_spec": format_spec, "format_id": format_id,
            "referer": referer, "cookies": cookies, "site": "",
            "playlist_title": playlist_title, "playlist_number": playlist_number,
        }
        self._dl_data["__last_fmt__"] = format_spec
        self.set_count(self.download_list.count())
        self.set_status(_("URL ajoutée : {url}").format(url=url))
        speech.speak(_("Ajouté à la file."), interrupt=False)

    def _enqueue_with_format_selection(self, url: str,
                                       subtitles_override: bool | None = None) -> None:
        """Fetch info → FormatDialog → enqueue avec format_id."""
        self.set_status(_("Récupération des formats disponibles…"))
        speech.speak(_("Récupération des formats disponibles."))

        import threading
        from app.core.downloader import Downloader, DownloadError

        result = {"subs": subtitles_override}

        def fetch():
            try:
                dl = Downloader(self.settings)
                info = dl.fetch_info("__fmt__", url)
                result["info"] = info
            except DownloadError as exc:
                result["error"] = str(exc)
            wx.CallAfter(self._on_formats_ready, url, result)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_formats_ready(self, url: str, result: dict) -> None:
        subs = result.get("subs")
        if "error" in result:
            self.set_status(_("Impossible de récupérer les formats."))
            wx.MessageBox(
                _("Impossible de récupérer les formats :\n\n{error}").format(error=result["error"]),
                _("Erreur"), wx.OK | wx.ICON_ERROR,
            )
            return

        info = result.get("info")
        if not info:
            self.set_status(_("Aucune information disponible."))
            return

        formats = info.raw_formats if hasattr(info, "raw_formats") else []
        if not formats:
            # Pas de formats détaillés → enqueue en auto
            self._enqueue_url(url, "auto", subtitles_override=subs)
            self.set_status(_("Formats non disponibles, téléchargement en qualité auto."))
            return

        with FormatDialog(self, info.title, formats) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                fmt_id = dlg.get_format_id()
                self._enqueue_url(url, "manual", format_id=fmt_id,
                                  subtitles_override=subs)
            else:
                self.set_status(_("Sélection de format annulée."))

    def _on_open_folder(self, _event) -> None:
        self._open_download_folder()

    def _on_preferences(self, _event) -> None:
        with SettingsDialog(self, self.settings) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.settings = dlg.get_settings()
                cfg.save(self.settings)
                self._queue._settings = self.settings
                speech.speak(_("Préférences enregistrées."))
                if dlg.restart_requested():
                    self._restart_app()

    def _restart_app(self) -> None:
        if getattr(sys, "frozen", False):
            args = [sys.executable] + sys.argv[1:]
        else:
            args = [sys.executable] + sys.argv
        try:
            subprocess.Popen(args, close_fds=True)
        except Exception:
            _log.exception("Échec du redémarrage automatique")
        self.Close(force=True)

    def _on_quit(self, _event) -> None:
        self.Close()

    def _on_start(self, _event) -> None:
        # Sera connecté au QueueManager en Phase 2
        wx.MessageBox(
            _("Démarrage de la file disponible en Phase 2."),
            APP_NAME, wx.OK | wx.ICON_INFORMATION,
        )

    def _on_pause(self, _event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id is None:
            speech.speak(_("Aucun téléchargement sélectionné."))
            return
        if not self._queue.is_active(dl_id):
            self.set_status(_("Ce téléchargement n'est pas en cours."))
            speech.speak(_("Ce téléchargement n'est pas en cours."))
            return
        if self._queue.is_paused(dl_id):
            self._queue.resume(dl_id)
            self.download_list.set_status(dl_id, STATUS_ACTIVE)
            speech.speak(_("Téléchargement repris."))
            self.set_status(_("Téléchargement repris."))
        else:
            self._queue.pause(dl_id)
            self.download_list.set_status(dl_id, STATUS_PAUSED)
            speech.speak(_("Téléchargement mis en pause."))
            self.set_status(_("Téléchargement mis en pause."))

    def _on_cancel(self, _event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id is None:
            self.set_status(_("Aucun téléchargement sélectionné."))
            return
        status = self.download_list.get_selected_status()
        if status in (STATUS_ACTIVE, STATUS_PENDING):
            if wx.MessageBox(
                _("Annuler ce téléchargement ?"),
                _("Confirmer l'annulation"),
                wx.YES_NO | wx.ICON_QUESTION,
            ) != wx.YES:
                return
            self._queue.cancel(dl_id)
        self.download_list.remove_selected()
        self._progress.pop(dl_id, None)
        self._dl_data.pop(dl_id, None)
        self.set_status(_("Téléchargement supprimé de la liste."))
        speech.speak(_("Supprimé."))
        self.set_count(self.download_list.count())

    def _on_clear_all(self, _event) -> None:
        if self.download_list.count() == 0:
            self.set_status(_("La liste est déjà vide."))
            return
        # Vérifier s'il y a des téléchargements en cours
        active = self.download_list.count_by_status(STATUS_ACTIVE)
        pending = self.download_list.count_by_status(STATUS_PENDING)
        if active + pending > 0:
            msg = _("Il y a {count} téléchargement(s) en cours ou en attente.\n\nTout annuler et vider la liste ?").format(
                count=active + pending
            )
        else:
            msg = _("Vider toute la liste ?")
        if wx.MessageBox(msg, _("Confirmer"), wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            return
        # Annuler tous les téléchargements actifs
        for dl_id in self.download_list.get_all_ids():
            self._queue.cancel(dl_id)
        self.download_list.clear_all()
        self._progress.clear()
        self._dl_data.clear()
        self._reset_gauge()
        self.set_count(0)
        self.set_status(_("Liste vidée."))
        speech.speak(_("Liste vidée."))

    def _on_retry(self, _event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id is None:
            self.set_status(_("Aucun téléchargement sélectionné."))
            return
        data = self._dl_data.get(dl_id)
        if not data:
            self.set_status(_("Impossible de réessayer : données introuvables."))
            return
        # Supprimer l'item échoué et relancer
        self.download_list.remove_selected()
        self._dl_data.pop(dl_id, None)
        self._enqueue_url(
            data["url"],
            data.get("format_spec", "auto"),
            format_id=data.get("format_id"),
            referer=data.get("referer"),
            cookies=data.get("cookies"),
            playlist_title=data.get("playlist_title"),
            playlist_number=data.get("playlist_number"),
        )
        self.set_status(_("Téléchargement relancé."))

    def _on_move_up(self, _event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id is None:
            return
        moved = self._queue.move_up(dl_id)
        if moved:
            self.download_list.move_item_up(dl_id)
            speech.speak(_("Déplacé vers le haut."), interrupt=False)
        else:
            speech.speak(_("Impossible de déplacer."), interrupt=False)

    def _on_move_down(self, _event) -> None:
        dl_id = self.download_list.get_selected_id()
        if dl_id is None:
            return
        moved = self._queue.move_down(dl_id)
        if moved:
            self.download_list.move_item_down(dl_id)
            speech.speak(_("Déplacé vers le bas."), interrupt=False)
        else:
            speech.speak(_("Impossible de déplacer."), interrupt=False)

    def _on_import_urls(self, _event) -> None:
        """Importe un fichier texte contenant des URLs (une par ligne)."""
        with wx.FileDialog(
            self,
            _("Importer une liste d'URLs"),
            wildcard=_("Fichiers texte (*.txt)|*.txt|Tous les fichiers|*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            wx.MessageBox(
                _("Impossible de lire le fichier :\n{error}").format(error=exc),
                _("Erreur de lecture"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return
        self._on_url_dropped(content)

    def _on_url_dropped(self, text: str) -> None:
        """Glisser-déposer de texte : extrait les URLs et ouvre AddUrlDialog pré-rempli."""
        urls = [u for u in _URL_RE.findall(text or "") if not _is_bare_domain(u)]
        if not urls:
            wx.MessageBox(
                _("Le texte déposé ne contient aucune URL valide."),
                _("Aucune URL détectée"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        default_fmt = self.settings.get("post_processing", "none")
        if default_fmt == "none":
            default_fmt = "auto"
        default_subs = self.settings.get("auto_subtitles", False)
        with AddUrlDialog(
            self,
            default_format=default_fmt,
            initial_urls="\n".join(urls),
            default_subtitles=default_subs,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            picked     = dlg.get_urls()
            fmt_choice = dlg.get_format_choice()
            subs       = dlg.get_subtitles()

        if fmt_choice == FORMAT_MANUAL and len(picked) == 1:
            self._enqueue_with_format_selection(picked[0], subtitles_override=subs)
        else:
            for url in picked:
                self._enqueue_url(url, fmt_choice, subtitles_override=subs)

    def _on_empty_char_hook(self, event) -> None:
        """Redirige Ctrl+V depuis la zone d'aide (TextCtrl lecture seule) vers le
        collage d'URL — sinon le contrôle natif l'avale sans rien faire."""
        if event.ControlDown() and not event.AltDown() and event.GetKeyCode() == ord("V"):
            self._on_paste_url(None)
            return  # ne pas Skip : le TextCtrl ne traite pas la touche
        event.Skip()

    def _on_paste_url(self, _event) -> None:
        """Ctrl+V global : colle l'URL du presse-papiers sans ouvrir de dialogue."""
        urls = _urls_from_clipboard()
        if not urls:
            self.set_status(_("Aucune URL valide dans le presse-papiers."))
            speech.speak(_("Aucune URL dans le presse-papiers."))
            return
        for url in urls:
            if _is_bare_domain(url):
                self.set_status(_("URL ignorée (domaine seul) : {url}").format(url=url))
                continue
            self._enqueue_url(url)
        n = len(urls)
        if n > 1:
            msg = _("{count} URLs ajoutées depuis le presse-papiers.").format(count=n)
        else:
            msg = _("{count} URL ajoutée depuis le presse-papiers.").format(count=n)
        self.set_status(msg)
        speech.speak(msg)

    def _on_clip_toggle(self, _event) -> None:
        """Active/désactive la surveillance du presse-papiers."""
        active = self.mi_clip_toggle.IsChecked()
        self.settings["clipboard_monitor"] = active
        cfg.save(self.settings)
        if active:
            self._clip_seen.clear()
            self._clip_last = _clipboard_text()
            self._clip_timer.Start(1500)
            speech.speak(_("Surveillance du presse-papiers activée."))
            self.set_status(_("Surveillance du presse-papiers activée."))
        else:
            self._clip_timer.Stop()
            speech.speak(_("Surveillance du presse-papiers désactivée."))
            self.set_status(_("Surveillance du presse-papiers désactivée."))

    def _on_clip_tick(self, _event) -> None:
        """Appelé toutes les 1,5 s — vérifie si une nouvelle URL a été copiée."""
        text = _clipboard_text()
        if text == self._clip_last:
            return
        self._clip_last = text
        urls = _URL_RE.findall(text)
        new_urls = [u for u in urls if u not in self._clip_seen]
        for url in new_urls:
            self._clip_seen.add(url)
            if _is_bare_domain(url):
                continue
            self._enqueue_url(url)
            msg = _("URL détectée et ajoutée : {url}").format(url=url)
            self.set_status(msg)
            speech.speak(msg)

    def _on_shortcuts(self, _event) -> None:
        msg = _(
            "F1               Ouvrir le guide d'utilisation\n"
            "Ctrl+N           Ajouter URL(s)\n"
            "Ctrl+F           Rechercher (YouTube, SoundCloud...)\n"
            "Ctrl+G           Extraction guidée (navigateur intégré)\n"
            "Ctrl+V           Coller URL depuis le presse-papiers\n"
            "Ctrl+Shift+V     Activer/désactiver la surveillance du presse-papiers\n"
            "Ctrl+H           Afficher l'historique\n"
            "F5               Démarrer la file\n"
            "Espace           Pause / Reprendre\n"
            "Suppr            Supprimer de la liste\n"
            "Maj+Suppr        Vider toute la liste\n"
            "F2               Réessayer\n"
            "Alt+Haut         Monter dans la file\n"
            "Alt+Bas          Descendre dans la file\n"
            "Ctrl+O           Ouvrir le dossier de destination\n"
            "Ctrl+P           Préférences\n"
            "Alt+F4           Quitter"
        )
        dlg = wx.Dialog(self, title=_("Raccourcis clavier"), size=(450, 400))
        sizer = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(dlg, value=msg, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 10)
        btn = wx.Button(dlg, wx.ID_CLOSE, _("Fermer"))
        btn.Bind(wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_CLOSE))
        sizer.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        dlg.SetSizer(sizer)
        txt.SetInsertionPoint(0)
        txt.SetFocus()
        dlg.ShowModal()
        dlg.Destroy()

    def _on_update_app(self, _event) -> None:
        self.mi_update_app.Enable(False)
        self.set_status(_("Vérification de la mise à jour DownAccess…"))
        speech.speak(_("Vérification de la mise à jour."))
        app_updater.check_for_update(
            on_done=lambda status, info, notes: wx.CallAfter(self._on_app_update_checked, status, info, notes)
        )

    def _on_app_update_checked(self, status: str, info: str, release_notes: str = "") -> None:
        self.mi_update_app.Enable(True)
        update_started = False
        if status == "up_to_date":
            msg = _("DownAccess est à jour. Version {version}.").format(version=info)
            self.set_status(msg)
            wx.MessageBox(
                _("Vous utilisez déjà la dernière version de DownAccess.\n\nVersion actuelle : {version}").format(version=info),
                _("Aucune mise à jour disponible"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        elif status == "update_available":
            dlg = UpdateDialog(self, new_version=info, release_notes=release_notes)
            if dlg.ShowModal() == wx.ID_OK:
                self.mi_update_app.Enable(False)
                self._app_dl_progress_dlg = _AppDownloadDialog(self, info)
                self._app_dl_progress_dlg.Show()
                self._app_dl_progress_dlg.Raise()
                self._app_dl_progress_dlg.focus_gauge()
                update_started = True
                cancel_handler = app_updater.download_and_install(
                    new_version=info,
                    on_progress=lambda pct: wx.CallAfter(self._on_app_dl_progress, pct),
                    on_error=lambda msg: wx.CallAfter(self._on_app_dl_error, msg),
                    on_cancel=lambda: wx.CallAfter(self._on_app_dl_cancelled),
                    on_quit=lambda: wx.CallAfter(self.Close),
                )
                self._app_dl_progress_dlg.set_cancel_handler(cancel_handler)
            else:
                self.set_status(_("Mise à jour DownAccess {version} reportée.").format(version=info))
            dlg.Destroy()
        elif status == "error":
            msg = _("Impossible de vérifier la mise à jour.")
            self.set_status(msg)
            speech.speak(msg)
            wx.MessageBox(
                _("Impossible de vérifier la mise à jour.\n\n{error}\n\nVérifiez votre connexion et réessayez.").format(error=info),
                _("Erreur de vérification"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
        # Ne pas voler le focus au dialogue de progression s'il vient d'ouvrir
        if not update_started:
            wx.CallAfter(self.download_list.SetFocus)

    def _on_app_dl_progress(self, percent: float) -> None:
        self.set_status(_("Téléchargement de la mise à jour… {percent} %").format(percent=int(percent)))
        if hasattr(self, "_app_dl_progress_dlg") and self._app_dl_progress_dlg:
            self._app_dl_progress_dlg.update(percent)

    def _on_app_dl_error(self, message: str) -> None:
        self.mi_update_app.Enable(True)
        if hasattr(self, "_app_dl_progress_dlg") and self._app_dl_progress_dlg:
            self._app_dl_progress_dlg.Destroy()
            self._app_dl_progress_dlg = None
        self.set_status(_("Erreur lors du téléchargement de la mise à jour."))
        wx.MessageBox(
            _("Impossible de télécharger la mise à jour :\n\n{error}").format(error=message),
            _("Erreur de mise à jour"), wx.OK | wx.ICON_ERROR, self,
        )

    def _on_app_dl_cancelled(self) -> None:
        """Le téléchargement de la mise à jour a été annulé par l'utilisateur :
        le thread a arrêté et nettoyé le fichier partiel. On ferme le dialogue
        de progression et on réactive l'option de mise à jour du menu."""
        self.mi_update_app.Enable(True)
        if hasattr(self, "_app_dl_progress_dlg") and self._app_dl_progress_dlg:
            self._app_dl_progress_dlg.Destroy()
            self._app_dl_progress_dlg = None
        self.set_status(_("Mise à jour annulée."))
        speech.speak(_("Mise à jour annulée."))
        wx.CallAfter(self.download_list.SetFocus)

    def check_app_update_at_startup(self) -> None:
        """Vérification silencieuse au démarrage — annonce seulement si mise à jour dispo."""
        def _on_done(status, info, notes):
            if status == "update_available":
                wx.CallAfter(self._on_app_update_checked, status, info, notes)
        app_updater.check_for_update(on_done=_on_done)

    def check_announcement_at_startup(self) -> None:
        """Vérification silencieuse d'une annonce serveur au démarrage."""
        install_id = self.settings.get("install_id", "")
        if not install_id:
            install_id = uuid.uuid4().hex
            self.settings["install_id"] = install_id
            cfg.save(self.settings)
        announce.check_announcement(
            install_id,
            on_done=lambda ann: wx.CallAfter(self._on_announcement_received, ann),
        )

    def _on_announcement_received(self, ann: dict | None) -> None:
        """Affiche l'annonce (si non vue), puis enchaine la verif MAJ."""
        try:
            if not ann:
                return
            title = ann.get("title") or APP_NAME
            body = ann.get("body") or ""
            if not body:
                return
            ann_id = ann.get("id") or ""
            mode = ann.get("mode") or "every"

            if mode == "once" and ann_id in self.settings.get("seen_announcements", []):
                return

            # /announce/check renvoie le lien comme objet imbrique {label, url}
            # (deja localise par le backend), ou null. Pas de champs plats.
            link = ann.get("link") or {}
            link_url = link.get("url") or ""
            if link_url:
                # Annonce « interactive » : dialogue avec bouton lien + /click.
                iid = self.settings.get("install_id", "")
                dlg = AnnouncementDialog(
                    self, title=title, body=body,
                    link_label=link.get("label") or "",
                    link_url=link_url,
                    on_link=(lambda: announce.click_announcement(iid, ann_id)) if ann_id else None,
                )
                dlg.ShowModal()
                dlg.Destroy()
            else:
                icon = wx.ICON_WARNING if ann.get("style") == "warning" else wx.ICON_INFORMATION
                wx.MessageBox(body, title, wx.OK | icon, self)

            if mode == "once" and ann_id:
                seen = self.settings.setdefault("seen_announcements", [])
                if ann_id not in seen:
                    seen.append(ann_id)
                    cfg.save(self.settings)
            if ann_id:
                announce.ack_announcement(self.settings.get("install_id", ""), ann_id)
        finally:
            # Quoi qu'il arrive (annonce affichee, deja vue, ou aucune), on
            # enchaine la verif MAJ — jamais avant la fermeture de l'annonce.
            self.check_app_update_at_startup()

    def _on_update_ytdlp(self, _event) -> None:
        self.set_status(_("Vérification de la version yt-dlp…"))
        speech.speak(_("Vérification en cours."))
        self.mi_update_ydl.Enable(False)

        updater.check_and_update(
            on_done=lambda status, info: wx.CallAfter(
                self.on_ytdlp_update_done, status, info, from_menu=True
            )
        )

    def _on_contact(self, _event) -> None:
        def _save_email(email: str) -> None:
            self.settings["user_email"] = email
            from app.core import settings as cfg
            cfg.save(self.settings)

        dlg = ContactDialog(
            self,
            saved_email=self.settings.get("user_email", ""),
            on_email_saved=_save_email,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def _on_github(self, _event) -> None:
        wx.LaunchDefaultBrowser("https://github.com/math65/downaccess")

    def _on_user_guide(self, _event) -> None:
        """Ouvre le guide d'utilisation (HTML embarqué) dans le navigateur.

        Choisit la langue selon l'UI courante, avec repli sur le français.
        Le navigateur + lecteur d'écran assurent une lecture accessible (la
        règle a11y du projet déconseille WebView2 embarqué pour ce contenu).
        """
        lang = i18n.get_current_language_code()
        docs = _docs_dir()
        for path in (docs / f"guide.{lang}.html", docs / "guide.fr.html"):
            if path.exists():
                wx.LaunchDefaultBrowser(path.as_uri())
                return
        wx.MessageBox(
            _("Le guide d'utilisation est introuvable."),
            _("Guide d'utilisation"),
            wx.OK | wx.ICON_ERROR, self,
        )

    def _on_about(self, _event) -> None:
        wx.MessageBox(
            _(
                "DownAccess\n\n"
                "Téléchargeur vidéo/audio Windows,\n"
                "entièrement accessible avec NVDA.\n\n"
                "Propulsé par yt-dlp et ffmpeg."
            ),
            _("À propos de DownAccess"),
            wx.OK | wx.ICON_INFORMATION,
        )

    def _on_close(self, event) -> None:
        n_active = self._queue.active_count
        if n_active > 0 and event.CanVeto():
            result = wx.MessageBox(
                _("{count} téléchargement(s) en cours.\n\nQuitter maintenant les annulera.\n\nVoulez-vous vraiment quitter ?").format(count=n_active),
                _("Téléchargements en cours — DownAccess"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if result != wx.YES:
                event.Veto()
                return

        if n_active > 0:
            self._queue.cancel_all()
            deadline = time.monotonic() + 3.0
            while self._queue.active_count > 0 and time.monotonic() < deadline:
                wx.Yield()
                time.sleep(0.05)

        cfg.save(self.settings)
        event.Skip()

    # ------------------------------------------------------------------
    # API publique (appelée depuis les threads via wx.CallAfter)
    # ------------------------------------------------------------------

    def on_ytdlp_update_done(self, status: str, info: str, from_menu: bool = False) -> None:
        """
        Callback pour bootstrap() (démarrage, silencieux) et le menu Mettre à jour (from_menu=True).
        status : "up_to_date" | "updated" | "installed" | "error"
        info   : version ou message d'erreur
        """
        self.mi_update_ydl.Enable(True)
        self._updater_running = False

        if not from_menu:
            # Démarrage : complètement silencieux, on débloque juste les téléchargements
            return

        # Déclenchement manuel depuis le menu
        if status == "up_to_date":
            self.set_status(_("yt-dlp est à jour. Version {version}.").format(version=info))
            wx.MessageBox(
                _("yt-dlp est déjà à jour.\n\nVersion actuelle : {version}").format(version=info),
                _("yt-dlp à jour"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        elif status == "updated":
            self.set_status(_("yt-dlp mis à jour. Version {version}.").format(version=info))
            wx.MessageBox(
                _("yt-dlp a été mis à jour avec succès.\n\nNouvelle version : {version}").format(version=info),
                _("yt-dlp mis à jour"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        elif status == "installed":
            self.set_status(_("yt-dlp installé. Version {version}.").format(version=info))
            wx.MessageBox(
                _("yt-dlp a été installé avec succès.\n\nVersion : {version}").format(version=info),
                _("yt-dlp installé"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        elif status == "error":
            self.set_status(_("Échec de la mise à jour de yt-dlp."))
            wx.MessageBox(
                _("La mise à jour de yt-dlp a échoué :\n\n{error}\n\nVérifiez votre connexion et réessayez via Aide → Mettre à jour yt-dlp.").format(error=info),
                _("Erreur yt-dlp"),
                wx.OK | wx.ICON_ERROR,
                self,
            )

        # Remettre le focus sur la liste pour NVDA (déféré pour laisser wx nettoyer les modaux)
        wx.CallAfter(self.download_list.SetFocus)

        # Démarrer les téléchargements mis en attente pendant la mise à jour
        if self._pending_downloads:
            pending = self._pending_downloads[:]
            self._pending_downloads.clear()
            n = len(pending)
            if n > 1:
                msg = _("Démarrage de {count} téléchargements en attente.").format(count=n)
            else:
                msg = _("Démarrage de {count} téléchargement en attente.").format(count=n)
            speech.speak(msg, interrupt=False)
            for url, fmt, fid, plt in pending:
                self._enqueue_url(url, fmt, fid, playlist_title=plt)

    def set_status(self, message: str) -> None:
        """Met à jour le premier panneau de la barre de statut (lu par NVDA)."""
        self.statusbar.SetStatusText(message, 0)

    def set_count(self, count: int) -> None:
        """Met à jour le compteur de téléchargements dans la barre de statut."""
        self.statusbar.SetStatusText(_("{count} téléchargement(s)").format(count=count), 1)
        # Bascule entre le message de liste vide et la liste de téléchargements
        empty = (count == 0)
        if self.lbl_empty.IsShown() != empty:
            self.lbl_empty.Show(empty)
            self.download_list.Show(not empty)
            self.lbl_empty.GetParent().Layout()
            # Si le focus était sur le contrôle qu'on vient de cacher, déplace-le
            focused = self.FindFocus()
            if empty and focused is self.download_list:
                self.lbl_empty.SetFocus()
            elif (not empty) and focused is self.lbl_empty:
                self.download_list.SetFocus()


# ------------------------------------------------------------------
# Fonctions utilitaires presse-papiers (hors classe)
# ------------------------------------------------------------------

def _clipboard_text() -> str:
    """Retourne le texte brut du presse-papiers, ou chaîne vide."""
    try:
        if wx.TheClipboard.Open():
            data = wx.TextDataObject()
            ok = wx.TheClipboard.GetData(data)
            wx.TheClipboard.Close()
            return data.GetText() if ok else ""
    except Exception:
        pass
    return ""


def _urls_from_clipboard() -> list[str]:
    """Extrait les URLs http/https du presse-papiers."""
    text = _clipboard_text()
    return [u for u in _URL_RE.findall(text) if u]
