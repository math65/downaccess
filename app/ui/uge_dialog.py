"""
Extraction Guidée (User Guided Extraction)

L'utilisateur navigue dans un vrai navigateur Chrome (via DrissionPage).
Un script JS intercepte toutes les requêtes XHR/fetch et les éléments
<video>/<source> pour détecter les URLs de médias en temps réel.
La fenêtre DownAccess affiche la liste des médias détectés.
"""
import base64
import json
import logging
import os
import threading
import time
import urllib.request

import wx

from app.core import speech
from app.core.browser import build_options, find_browser, browser_name

_log = logging.getLogger("downaccess.uge")

# ------------------------------------------------------------------
# Script JS injecté après chaque chargement de page
# ------------------------------------------------------------------

_MONITOR_SCRIPT = r"""
(function() {
    if (window.__da_initialized) return;
    window.__da_initialized = true;
    window.__da_urls = window.__da_urls || [];

    var MEDIA_RE = /\.(mp4|m4v|webm|mkv|flv|mov|m3u8|mpd|ts|mp3|aac|ogg|wav|opus)(\?|#|$)/i;

    function addUrl(url) {
        if (!url || typeof url !== 'string') return;
        if (url.startsWith('blob:') || url.startsWith('data:')) return;
        if (!MEDIA_RE.test(url)) return;
        if (window.__da_urls.indexOf(url) !== -1) return;
        window.__da_urls.push(url);
    }

    // Intercepter XMLHttpRequest
    var origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        addUrl(String(url));
        return origOpen.apply(this, arguments);
    };

    // Intercepter fetch
    var origFetch = window.fetch;
    if (origFetch) {
        window.fetch = function(input, init) {
            if (typeof input === 'string') addUrl(input);
            else if (input && typeof input.url === 'string') addUrl(input.url);
            return origFetch.apply(this, arguments);
        };
    }

    // Observer les éléments video/source/audio ajoutés au DOM
    function scanNode(node) {
        if (!node || !node.tagName) return;
        var tag = node.tagName.toUpperCase();
        if (tag === 'VIDEO' || tag === 'SOURCE' || tag === 'AUDIO') {
            if (node.src) addUrl(node.src);
            if (node.currentSrc) addUrl(node.currentSrc);
        }
        if (node.querySelectorAll) {
            var els = node.querySelectorAll('video,source,audio');
            for (var i = 0; i < els.length; i++) {
                if (els[i].src) addUrl(els[i].src);
                if (els[i].currentSrc) addUrl(els[i].currentSrc);
            }
        }
    }

    var observer = new MutationObserver(function(mutations) {
        for (var i = 0; i < mutations.length; i++) {
            var nodes = mutations[i].addedNodes;
            for (var j = 0; j < nodes.length; j++) {
                scanNode(nodes[j]);
            }
        }
    });
    observer.observe(document.documentElement || document.body,
                     {childList: true, subtree: true});

    // Scanner les éléments déjà présents
    var existing = document.querySelectorAll('video,source,audio');
    for (var k = 0; k < existing.length; k++) {
        if (existing[k].src) addUrl(existing[k].src);
        if (existing[k].currentSrc) addUrl(existing[k].currentSrc);
    }
})();
"""

# User-agents
_UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _resolve_redirect(url: str, referer: str | None = None) -> str:
    """
    Suit les redirections HTTP et tente d'extraire l'URL du média depuis
    un éventuel JSON de réponse (ex : endpoint /register/).
    """
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", _UA_DESKTOP)
        if referer:
            req.add_header("Referer", referer)
        req.add_header("Accept", "*/*")
        with urllib.request.urlopen(req, timeout=8) as resp:
            final_url = resp.url
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(4096)  # lire au max 4 Ko

        # Si la réponse est JSON, chercher une URL média dedans
        if "json" in content_type or body.lstrip().startswith(b"{"):
            try:
                data = json.loads(body)
                found = _find_media_url(data)
                if found:
                    return found
            except Exception:
                pass

        return final_url
    except Exception:
        return url


def _find_media_url(obj) -> str | None:
    """Cherche récursivement la première URL http(s) dans un objet JSON."""
    if isinstance(obj, str):
        if obj.startswith("http") and any(
            ext in obj.lower() for ext in (".mp3", ".mp4", ".m4a", ".webm", ".ogg",
                                            ".aac", ".wav", ".flac", ".m3u8", ".mpd")
        ):
            return obj
        return None
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_media_url(v)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _find_media_url(item)
            if found:
                return found
    return None


_MEDIA_EXTENSIONS = (
    ".mp4", ".m4v", ".webm", ".mkv", ".flv", ".mov",
    ".m3u8", ".mpd", ".ts",
    ".mp3", ".aac", ".ogg", ".wav", ".opus", ".m4a",
)

_MANIFEST_EXTENSIONS = (".m3u8", ".mpd")

_BLOCKABLE_EXTENSIONS = (
    ".mp4", ".m4v", ".webm", ".mkv", ".flv", ".mov", ".ts",
    ".mp3", ".aac", ".ogg", ".wav", ".opus", ".m4a",
)


def _is_media_url(url: str) -> bool:
    """Filtre les URLs réseau pour ne garder que les médias."""
    low = url.lower().split("?")[0].split("#")[0]
    return any(low.endswith(ext) for ext in _MEDIA_EXTENSIONS)


def _is_manifest_url(url: str) -> bool:
    """Vérifie si l'URL est un manifeste HLS/DASH (à laisser passer)."""
    low = url.lower().split("?")[0].split("#")[0]
    return any(low.endswith(ext) for ext in _MANIFEST_EXTENSIONS)


def _url_type(url: str) -> str:
    low = url.lower().split("?")[0].split("#")[0]
    if ".m3u8" in low:
        return "HLS"
    if ".mpd" in low:
        return "DASH"
    for ext in (".mp4", ".m4v", ".webm", ".mkv", ".flv", ".mov"):
        if low.endswith(ext):
            return _("Vidéo {ext}").format(ext=ext[1:].upper())
    for ext in (".mp3", ".aac", ".ogg", ".wav", ".opus"):
        if low.endswith(ext):
            return _("Audio {ext}").format(ext=ext[1:].upper())
    return _("Média")


class UGEDialog(wx.Frame):
    """
    Fenêtre d'extraction guidée.
    Ouvre un vrai navigateur Chrome (DrissionPage) à côté de la fenêtre
    DownAccess qui affiche les médias détectés.
    100 % accessible NVDA.
    """

    def __init__(self, parent, on_add_url):
        super().__init__(
            parent,
            title=_("Extraction guidée — DownAccess"),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self._on_add_url = on_add_url
        self._detected: list[str] = []
        self._poll_timer = wx.Timer(self)
        self._page = None  # DrissionPage ChromiumPage
        # Processus hote du moteur WebView2, quand c'est lui qui sert. None
        # quand l'extraction tourne sur un navigateur installe.
        self._wv_proc = None
        self._engine = ""
        self._polling = False
        self._intercept_enabled = False
        self._intercepted_headers: dict[str, tuple[str, str]] = {}  # url → (referer, cookies)
        self._save_threads: list[threading.Thread] = []  # threads de sauvegarde média en cours

        self._build_ui()
        self._bind_events()
        self.SetSize((500, 600))
        self.Centre()

        speech.speak(
            _(
                "Extraction guidée ouverte. "
                "Saisissez une URL et appuyez sur Entrée pour naviguer. "
                "Lancez la vidéo dans le navigateur qui s'est ouvert. "
                "Les médias détectés apparaîtront dans cette fenêtre. "
                "Note : les contenus protégés par DRM (Netflix, Disney+, Prime Video) ne sont pas pris en charge."
            ),
        )

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Barre d'adresse
        addr_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_addr = wx.StaticText(panel, label=_("Adresse :"))
        self.txt_url = wx.TextCtrl(
            panel,
            name=_("Adresse URL"),
            style=wx.TE_PROCESS_ENTER,
        )
        self.txt_url.SetHint("https://www.example.com/video")
        self.btn_go = wx.Button(panel, label=_("Aller"), name=_("Aller à l'adresse"))

        # WebView2 n'a aucune barre de navigation : ces boutons-ci la
        # remplacent. Ils pilotent la page par le meme canal que le reste, donc
        # ils fonctionnent aussi avec le navigateur installe.
        self.btn_back = wx.Button(panel, label=_("Précédent"),
                                  name=_("Revenir à la page précédente"))
        self.btn_forward = wx.Button(panel, label=_("Suivant"),
                                     name=_("Aller à la page suivante"))
        self.btn_reload = wx.Button(panel, label=_("Actualiser"),
                                    name=_("Recharger la page"))
        # Rien a piloter tant qu'aucune page n'est ouverte.
        for bouton in (self.btn_back, self.btn_forward, self.btn_reload):
            bouton.Disable()

        addr_sizer.Add(lbl_addr,     0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        addr_sizer.Add(self.txt_url, 1, wx.EXPAND | wx.RIGHT, 6)
        addr_sizer.Add(self.btn_go,  0, wx.RIGHT, 6)
        addr_sizer.Add(self.btn_back, 0, wx.RIGHT, 6)
        addr_sizer.Add(self.btn_forward, 0, wx.RIGHT, 6)
        addr_sizer.Add(self.btn_reload, 0)
        sizer.Add(addr_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Statut
        self.lbl_status = wx.StaticText(
            panel,
            label=_("Entrez une URL pour ouvrir le navigateur."),
        )
        sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Interception des tokens
        self.chk_intercept = wx.CheckBox(
            panel,
            label=_("Intercepter les requêtes (sites avec tokens expirants)"),
            name=_("Activer l'interception des requêtes média"),
        )
        self.chk_intercept.SetValue(False)
        sizer.Add(self.chk_intercept, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Liste des médias détectés
        lbl_detected = wx.StaticText(panel, label=_("Médias détectés :"))
        self.lst_media = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SUNKEN,
            name=_("Liste des médias détectés"),
        )
        self.lst_media.InsertColumn(0, _("Type"), width=90)
        self.lst_media.InsertColumn(1, _("URL"), width=360)

        self.lbl_count = wx.StaticText(panel, label=_("0 média(s) détecté(s)"))

        sizer.Add(lbl_detected,   0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.lst_media, 1, wx.EXPAND | wx.ALL, 6)
        sizer.Add(self.lbl_count, 0, wx.LEFT | wx.BOTTOM, 8)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_clear = wx.Button(
            panel, label=_("Effacer"),
            name=_("Effacer la liste des médias détectés"),
        )
        self.btn_add = wx.Button(
            panel, label=_("Ajouter à la file"),
            name=_("Ajouter le média sélectionné à la file de téléchargement"),
        )
        self.btn_add.Disable()
        self.btn_close = wx.Button(panel, wx.ID_CLOSE, label=_("Fermer"))

        btn_sizer.Add(self.btn_clear, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_add,   1, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_close, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)
        self.txt_url.SetFocus()

    # ------------------------------------------------------------------
    # Liaison des événements
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        self.btn_go.Bind(wx.EVT_BUTTON, self._on_go)
        self.txt_url.Bind(wx.EVT_TEXT_ENTER, self._on_go)
        self.btn_back.Bind(wx.EVT_BUTTON, self._on_back)
        self.btn_forward.Bind(wx.EVT_BUTTON, self._on_forward)
        self.btn_reload.Bind(wx.EVT_BUTTON, self._on_reload)

        # Raccourcis habituels d'un navigateur : ils evitent d'aller chercher
        # le bouton depuis la liste des medias.
        id_back, id_forward, id_reload = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self._on_back, id=id_back)
        self.Bind(wx.EVT_MENU, self._on_forward, id=id_forward)
        self.Bind(wx.EVT_MENU, self._on_reload, id=id_reload)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_ALT, wx.WXK_LEFT, id_back),
            (wx.ACCEL_ALT, wx.WXK_RIGHT, id_forward),
            (wx.ACCEL_NORMAL, wx.WXK_F5, id_reload),
        ]))
        self.chk_intercept.Bind(wx.EVT_CHECKBOX, self._on_toggle_intercept)
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear)
        self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _: self.Close())
        self.lst_media.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_media_select)
        self.lst_media.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_media_deselect)
        self.lst_media.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_media_activate)
        self.lst_media.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self.Bind(wx.EVT_TIMER, self._on_poll, self._poll_timer)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ------------------------------------------------------------------
    # Interception CDP Fetch (tokens expirants)
    # ------------------------------------------------------------------

    def _on_toggle_intercept(self, _event) -> None:
        enabled = self.chk_intercept.GetValue()
        if self._page is None:
            self._intercept_enabled = enabled
            if enabled:
                speech.speak(_("L'interception sera activée au lancement du navigateur."))
            return
        if enabled:
            self._enable_fetch_intercept()
        else:
            self._disable_fetch_intercept()

    def _enable_fetch_intercept(self) -> None:
        try:
            patterns = [
                {"urlPattern": f"*{ext}*", "requestStage": "Response"}
                for ext in _MEDIA_EXTENSIONS
            ]
            self._page.run_cdp("Fetch.enable", patterns=patterns)
            self._page.driver.set_callback(
                "Fetch.requestPaused", self._on_request_paused
            )
            self._intercept_enabled = True
            self._saved_urls: set[str] = set()  # déduplication
            speech.speak(_("Interception des requêtes média activée."))
        except Exception:
            self.chk_intercept.SetValue(False)
            self._intercept_enabled = False

    def _disable_fetch_intercept(self) -> None:
        try:
            self._page.driver.set_callback("Fetch.requestPaused", None)
            self._page.run_cdp("Fetch.disable")
            self._intercept_enabled = False
            speech.speak(_("Interception des requêtes média désactivée."))
        except Exception:
            pass  # Normal si Chrome déjà fermé

    def _on_request_paused(self, **kwargs) -> None:
        """Callback CDP Fetch.requestPaused au stade Response (thread Driver).
        Le navigateur a déjà reçu la réponse. On capture le corps et on
        sauvegarde sur le disque, puis on laisse le navigateur continuer."""
        request_id = kwargs.get("requestId")
        request = kwargs.get("request", {})
        url = request.get("url", "")
        status_code = kwargs.get("responseStatusCode", 0)

        _drv = self._page.driver

        if not _is_media_url(url):
            try:
                _drv.run("Fetch.continueRequest", requestId=request_id)
            except Exception:
                pass
            return

        # Laisser passer les non-200/206
        if status_code not in (200, 206):
            try:
                _drv.run("Fetch.continueRequest", requestId=request_id)
            except Exception:
                pass
            return

        # Ignorer les URLs sans token
        if "?" not in url:
            try:
                _drv.run("Fetch.continueRequest", requestId=request_id)
            except Exception:
                pass
            return

        # Déduplication : ne sauvegarder qu'une fois par URL base (sans token)
        url_base = url.split("?")[0]
        already_saved = url_base in getattr(self, "_saved_urls", set())

        # Capturer le corps de la réponse
        body_data = b""
        if not already_saved:
            try:
                body_result = _drv.run(
                    "Fetch.getResponseBody", requestId=request_id
                )
                raw = body_result.get("body", "")
                is_b64 = body_result.get("base64Encoded", False)
                _log.debug("Fetch body: %d chars, base64=%s", len(raw), is_b64)
                body_data = base64.b64decode(raw) if is_b64 else raw.encode("utf-8")
            except Exception as exc:
                _log.error("Fetch.getResponseBody failed: %s", exc)

        # Toujours laisser le navigateur continuer (l'audio joue normalement)
        try:
            _drv.run("Fetch.continueRequest", requestId=request_id)
        except Exception:
            pass

        # Sauvegarder dans un thread séparé (pas wx.CallAfter)
        if body_data and not already_saved:
            if not hasattr(self, "_saved_urls"):
                self._saved_urls = set()
            self._saved_urls.add(url_base)
            # Récupérer le titre de la page pour le nom du fichier
            page_title = ""
            try:
                page_title = self._page.title or ""
            except Exception:
                pass
            wx.CallAfter(self._add_intercepted_url, url, "", "")
            wx.CallAfter(self._set_status, _("Téléchargement en cours…"))
            wx.CallAfter(speech.speak, _("Téléchargement en cours…"), interrupt=False)
            t = threading.Thread(
                target=self._save_intercepted_media,
                args=(url, body_data, page_title),
                daemon=True,
            )
            t.start()
            self._save_threads.append(t)

    def _add_intercepted_url(self, url: str,
                             referer: str = "", cookies: str = "") -> None:
        """Ajoute une URL interceptée à la liste (thread UI via CallAfter)."""
        if url in self._detected:
            return
        self._detected.append(url)
        # Stocker les headers CDP pour le téléchargement
        self._intercepted_headers[url] = (referer, cookies)
        media_type = _url_type(url)
        idx = self.lst_media.GetItemCount()
        # Le prefixe "[I] " est un marqueur interne (intercepte) detecte au clic
        self.lst_media.InsertItem(idx, f"[I] {media_type}")
        self.lst_media.SetItem(idx, 1, url)
        n = self.lst_media.GetItemCount()
        self.lbl_count.SetLabel(_("{count} média(s) détecté(s)").format(count=n))
        speech.speak(_("Média intercepté."), interrupt=False)

    def _save_intercepted_media(self, url: str, data: bytes,
                                page_title: str = "") -> None:
        """Sauvegarde les données interceptées sur le disque (thread séparé)."""
        try:
            from app.core import settings as cfg
            settings = cfg.load()
            dest_dir = settings.get("download_folder", os.path.expanduser("~"))

            # Extension depuis l'URL
            url_filename = url.split("/")[-1].split("?")[0]
            ext = os.path.splitext(url_filename)[1] or ".mp3"

            # Nom du fichier : titre de la page ou nom brut de l'URL
            use_title = settings.get("intercept_use_page_title", True)
            if use_title and page_title:
                # Nettoyer le titre pour un nom de fichier Windows valide
                clean = page_title.strip()
                for ch in r'<>:"/\|?*':
                    clean = clean.replace(ch, "")
                clean = clean.strip(". ")
                if clean:
                    filename = clean + ext
                else:
                    filename = url_filename or ("media_intercepte" + ext)
            else:
                filename = url_filename or ("media_intercepte" + ext)

            filepath = os.path.join(dest_dir, filename)

            # Éviter les doublons
            base_path, ext = os.path.splitext(filepath)
            counter = 1
            while os.path.exists(filepath):
                filepath = f"{base_path} ({counter}){ext}"
                counter += 1

            _log.info("Sauvegarde média: %s (%d octets)", filepath, len(data))

            with open(filepath, "wb") as f:
                f.write(data)

            size_mb = len(data) / (1024 * 1024)
            _log.info("Média sauvegardé: %s (%.1f Mo)", filepath, size_mb)

            wx.CallAfter(self._on_media_saved, filepath, filename, size_mb)
        except Exception as exc:
            _log.error("Erreur sauvegarde média: %s", exc)
            wx.CallAfter(
                wx.MessageBox,
                _("Erreur lors de la sauvegarde :\n{error}").format(error=exc),
                _("Erreur — DownAccess"),
                wx.OK | wx.ICON_ERROR,
                self,
            )

    def _on_media_saved(self, filepath: str, filename: str,
                        size_mb: float) -> None:
        """Callback UI après sauvegarde réussie."""
        self._set_status(
            _("Téléchargement terminé : {filename} ({size_mb:.1f} Mo)").format(
                filename=filename, size_mb=size_mb
            )
        )
        speech.speak(
            _("Média sauvegardé : {filename} ({size_mb:.1f} Mo)").format(
                filename=filename, size_mb=size_mb
            ),
            interrupt=False,
        )
        wx.MessageBox(
            _("Fichier sauvegardé :\n{filepath}\n\nTaille : {size_mb:.1f} Mo").format(
                filepath=filepath, size_mb=size_mb
            ),
            _("Média intercepté — DownAccess"),
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _set_status(self, text: str) -> None:
        """Met à jour le label de statut (thread-safe : CallAfter inconditionnel)."""
        wx.CallAfter(self.lbl_status.SetLabel, text)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _ensure_browser(self) -> bool:
        """Ouvre le moteur de navigation, s'il ne l'est pas deja.

        Deux moteurs possibles : **WebView2**, celui que Windows fournit (rien
        a installer, aucune fenetre de navigateur tiers), ou un navigateur
        Chromium present sur la machine. Ils se pilotent par le meme protocole
        — c'est le meme moteur Chromium en dessous — donc tout le reste de
        cette fenetre les ignore superbement.

        Le repli est silencieux et sans perte : sans WebView2, l'extraction se
        deroule exactement comme avant. Ce n'est pas une panne a signaler.
        """
        if self._page is not None:
            return True

        prefere = "auto"
        try:
            from app.core import settings as cfg
            prefere = cfg.load().get("uge_engine", "auto")
        except Exception:
            pass

        if prefere in ("auto", "webview2") and self._start_webview2():
            return True
        return self._start_installed_browser()

    def _start_webview2(self) -> bool:
        """Lance le moteur de Windows. False si indisponible (on replie)."""
        proc = None
        try:
            from DrissionPage import ChromiumOptions, ChromiumPage

            from app.core import webview_host

            self._set_status(_("Ouverture du navigateur..."))
            proc, addr = webview_host.start_host(
                "about:blank", _("Extraction guidée — DownAccess"))
            # `existing_only` : on s'attache a l'hote deja lance, on ne veut
            # surtout pas que DrissionPage demarre un navigateur de son cote.
            page = ChromiumPage(
                ChromiumOptions().set_address(addr).existing_only())
        except Exception as exc:
            _log.warning("Moteur WebView2 indisponible, repli sur le "
                         "navigateur installe : %s", exc)
            try:
                from app.core import webview_host
                webview_host.stop_host(proc)
            except Exception:
                pass
            return False

        self._wv_proc = proc
        self._page = page
        self._engine = "webview2"
        self._browser_name = "WebView2"
        _log.info("Extraction guidee : moteur WebView2 de Windows")
        self._page.listen.start('')
        if self._intercept_enabled:
            self._enable_fetch_intercept()
        return True

    def _start_installed_browser(self) -> bool:
        """Lance un navigateur Chromium installe (Chrome, Edge ou Brave)."""
        browser_path = find_browser()
        if not browser_path:
            wx.MessageBox(
                _(
                    "Aucun navigateur compatible trouvé.\n\n"
                    "Installez Google Chrome, Microsoft Edge ou Brave."
                ),
                _("Erreur — Extraction guidée"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return False

        try:
            from DrissionPage import ChromiumPage
            # Profil dédié PERSISTANT (cf. browser.build_options) : l'utilisateur
            # reste connecté aux sites d'une extraction à l'autre. Avant, cet
            # appel utilisait auto_port(), qui repart d'un profil temporaire
            # supprimé à la fermeture -> reconnexion obligatoire à chaque fois.
            self._page = ChromiumPage(build_options(browser_path))
            self._browser_name = browser_name(browser_path)
            self._engine = "browser"
            _log.info("Extraction guidee : navigateur installe (%s)",
                      self._browser_name)
            # Écouter toutes les requêtes réseau (filtrage côté Python)
            self._page.listen.start('')
            if self._intercept_enabled:
                self._enable_fetch_intercept()
            return True
        except Exception as exc:
            _log.error("Impossible d'ouvrir le navigateur : %s", exc)
            wx.MessageBox(
                _("Impossible d'ouvrir le navigateur.\n\n{error}").format(error=exc),
                _("Erreur — Extraction guidée"),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return False

    def _on_go(self, _event) -> None:
        url = self.txt_url.GetValue().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.txt_url.SetValue(url)

        if not self._ensure_browser():
            return

        self.lbl_status.SetLabel(_("Chargement…"))

        def navigate():
            try:
                self._page.get(url)
                # Injecter le script de détection de médias
                self._page.run_js(_MONITOR_SCRIPT)
                current_url = self._page.url
                title = self._page.title
                wx.CallAfter(self._on_page_loaded, current_url, title)
            except Exception as exc:
                _log.error("Erreur navigation : %s", exc)
                wx.CallAfter(
                    self.lbl_status.SetLabel,
                    _("Erreur : {error}").format(error=exc),
                )

        threading.Thread(target=navigate, daemon=True).start()

    def _navigate(self, action, echec: str) -> None:
        """Joue une action de navigation dans un thread, puis rafraichit l'UI.

        Toujours hors du thread interface : `back()` attend le chargement de la
        page, ce qui figerait la fenetre pendant plusieurs secondes.
        """
        if self._page is None:
            return

        def travail():
            try:
                action(self._page)
            except Exception as exc:
                _log.info("Navigation : %s (%s)", echec, exc)
                wx.CallAfter(self._set_status_direct, echec)
                return
            try:
                url, titre = self._page.url, self._page.title
            except Exception:
                return
            wx.CallAfter(self._on_page_loaded, url, titre)

        threading.Thread(target=travail, daemon=True).start()

    def _set_status_direct(self, texte: str) -> None:
        self.lbl_status.SetLabel(texte)
        speech.speak(texte, interrupt=False)

    def _on_back(self, _event) -> None:
        self._navigate(lambda page: page.back(),
                       _("Aucune page précédente."))

    def _on_forward(self, _event) -> None:
        self._navigate(lambda page: page.forward(),
                       _("Aucune page suivante."))

    def _on_reload(self, _event) -> None:
        self._navigate(lambda page: page.refresh(),
                       _("Impossible de recharger la page."))

    def _on_page_loaded(self, url: str, title: str) -> None:
        self.txt_url.SetValue(url)
        for bouton in (self.btn_back, self.btn_forward, self.btn_reload):
            bouton.Enable()
        self.lbl_status.SetLabel(
            _("Page chargée : {title}\nLancez la vidéo dans le navigateur — les médias seront détectés automatiquement.").format(
                title=title
            )
        )
        if not self._poll_timer.IsRunning():
            self._poll_timer.Start(1000)

    # ------------------------------------------------------------------
    # Polling JS → détection des médias
    # ------------------------------------------------------------------

    def _on_poll(self, _event) -> None:
        if self._page is None or self._polling:
            return
        self._polling = True

        def poll():
            try:
                found_urls = []

                # 1. Requêtes réseau capturées (iframes inclus)
                for packet in self._page.listen.steps(timeout=0.5):
                    url = packet.url if hasattr(packet, 'url') else str(packet)
                    if url and _is_media_url(url):
                        found_urls.append(url)

                # 2. Script JS sur la page principale (XHR/fetch/DOM)
                try:
                    self._page.run_js(_MONITOR_SCRIPT)
                    data = self._page.run_js("JSON.stringify(window.__da_urls || [])")
                    if data:
                        found_urls.extend(json.loads(data))
                except Exception:
                    pass

                current_url = self._page.url
                wx.CallAfter(self._update_detected, found_urls, current_url)
            except Exception:
                pass  # Normal quand Chrome est fermé
            finally:
                self._polling = False

        threading.Thread(target=poll, daemon=True).start()

    def _update_detected(self, urls: list, current_url: str) -> None:
        self.txt_url.SetValue(current_url)

        added = 0
        for url in urls:
            if url not in self._detected:
                self._detected.append(url)
                media_type = _url_type(url)
                idx = self.lst_media.GetItemCount()
                self.lst_media.InsertItem(idx, media_type)
                self.lst_media.SetItem(idx, 1, url)
                added += 1

        if added:
            n = self.lst_media.GetItemCount()
            self.lbl_count.SetLabel(_("{count} média(s) détecté(s)").format(count=n))
            if added > 1:
                msg = _("{count} médias détectés.").format(count=added)
            else:
                msg = _("{count} média détecté.").format(count=added)
            speech.speak(msg, interrupt=False)

    # ------------------------------------------------------------------
    # Gestion de la liste des médias
    # ------------------------------------------------------------------

    def _on_media_select(self, event) -> None:
        self.btn_add.Enable()
        event.Skip()

    def _on_media_deselect(self, _event) -> None:
        if self.lst_media.GetFirstSelected() == -1:
            self.btn_add.Disable()

    def _on_media_activate(self, _event) -> None:
        self._on_add(None)

    def _on_list_key(self, event) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_add(None)
        else:
            event.Skip()

    def _on_clear(self, _event) -> None:
        self._detected.clear()
        self.lst_media.DeleteAllItems()
        self.lbl_count.SetLabel(_("0 média(s) détecté(s)"))
        self.btn_add.Disable()
        speech.speak(_("Liste effacée."))

    def _on_add(self, _event) -> None:
        idx = self.lst_media.GetFirstSelected()
        if idx == -1:
            return
        url = self.lst_media.GetItemText(idx, 1)
        # Normaliser les paramètres de consentement connus
        url = url.replace("accepted=false", "accepted=true")

        self.btn_add.Disable()

        # Si URL interceptée via CDP Fetch, utiliser les headers capturés
        # (inclut les cookies httpOnly invisibles à document.cookie)
        # Le marqueur "[I] " est un prefixe interne, jamais traduit.
        is_intercepted = self.lst_media.GetItemText(idx, 0).startswith("[I]")

        if is_intercepted:
            hdrs = self._intercepted_headers.get(url, ("", ""))
            referer = hdrs[0] or None
            cookies = hdrs[1] or None
            _log.info("Ajout intercepté url=%s cookies=%d chars",
                      url[:80], len(cookies or ""))
            speech.speak(_("Ajout direct du média intercepté…"), interrupt=False)
            wx.CallAfter(self._finish_add, url, referer, cookies, True)
        else:
            referer = self._page.url if self._page else None
            speech.speak(_("Résolution de l'URL en cours…"), interrupt=False)

            def resolve_and_add():
                final_url = _resolve_redirect(url, referer)
                wx.CallAfter(self._finish_add, final_url, referer, None)

            threading.Thread(target=resolve_and_add, daemon=True).start()

    def _finish_add(self, url: str, referer: str | None, cookies: str | None,
                    skip_info: bool = False) -> None:
        self.btn_add.Enable()
        self._on_add_url(url, referer=referer, cookies=cookies, skip_info=skip_info)
        speech.speak(_("Ajouté à la file de téléchargement."))

    # ------------------------------------------------------------------
    # Fermeture
    # ------------------------------------------------------------------

    def _on_close(self, event) -> None:
        self._poll_timer.Stop()

        # Attendre les sauvegardes média en cours pour éviter les fichiers tronqués
        active_saves = [t for t in self._save_threads if t.is_alive()]
        if active_saves:
            deadline = time.monotonic() + 5.0
            for t in active_saves:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                t.join(timeout=remaining)

        # Fermer le navigateur Chrome
        if self._page:
            if self._intercept_enabled:
                try:
                    self._disable_fetch_intercept()
                except Exception:
                    pass
            try:
                self._page.listen.stop()
            except Exception:
                pass
            if self._engine == "webview2":
                # `quit()` fermerait le moteur par en dessous alors que c'est
                # notre processus hote qui le possede : on ferme l'hote, il
                # emporte le moteur avec lui.
                self._page = None
                try:
                    from app.core import webview_host
                    webview_host.stop_host(self._wv_proc)
                except Exception:
                    pass
                self._wv_proc = None
            else:
                try:
                    self._page.quit()
                except Exception:
                    pass
            self._page = None
            self._engine = ""
        event.Skip()
