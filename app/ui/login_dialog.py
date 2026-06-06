"""
Dialogue de connexion à un site.
Ouvre un navigateur dans un profil dédié à DownAccess (via DrissionPage)
pour que les cookies soient conservés et réutilisés par yt-dlp.
Profil isolé = aucun conflit avec le navigateur habituel de l'utilisateur,
qu'il soit déjà ouvert ou non. La connexion ne se fait qu'une fois.
"""
import logging
import threading
from urllib.parse import urlparse

import wx

from app.core import speech
from app.core.browser import harvest_cookies, open_dedicated_browser
from app.core.cookies import jar_path_for, write_cookie_jar_from_dicts

_log = logging.getLogger("downaccess.login")


def friendly_browser_error(exc: Exception) -> str:
    """Convertit une erreur technique (souvent un message DrissionPage en
    chinois) en message clair. Partagé par les dialogues de connexion."""
    msg = str(exc)
    # Connexion à la page perdue (fenêtre fermée trop tôt).
    if "断开" in msg or "disconnect" in msg.lower():
        return _(
            "La connexion au navigateur a été perdue (la fenêtre a peut-être "
            "été fermée trop tôt).\n"
            "Réessayez, et laissez DownAccess fermer le navigateur lui-même."
        )
    if any(s in msg for s in ("127.0.0.1", "9222", "连接", "浏览器")) \
            or "Connect" in type(exc).__name__:
        return _(
            "Impossible de démarrer le navigateur dédié à DownAccess.\n"
            "Fermez les éventuelles fenêtres DownAccess restées ouvertes, "
            "puis réessayez."
        )
    return msg


class LoginDialog(wx.Dialog):
    """
    Dialogue de connexion. Ouvre un navigateur dans le profil dédié à
    DownAccess, l'utilisateur se connecte, puis ferme ce dialogue.
    Les cookies restent dans ce profil → yt-dlp y accède.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Se connecter à un site — DownAccess"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(500, 300),
        )
        self._page = None
        self._build_ui()
        self._bind_events()
        self.Centre()

        speech.speak(
            _(
                "Connexion à un site. "
                "Saisissez l'adresse : un navigateur dédié à DownAccess s'ouvrira. "
                "Connectez-vous une fois ; vos cookies seront conservés pour les prochains téléchargements. "
                "Note : les contenus protégés par DRM (Netflix, Disney+, Prime Video) ne sont pas pris en charge."
            ),
        )

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Barre d'adresse
        row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_url = wx.StaticText(panel, label=_("Adresse du site :"))
        self.txt_url = wx.TextCtrl(
            panel,
            style=wx.TE_PROCESS_ENTER,
            name=_("Adresse du site"),
        )
        self.txt_url.SetHint("https://www.youtube.com")
        self.btn_go = wx.Button(panel, label=_("Ouvrir"), name=_("Ouvrir dans le navigateur"))
        row.Add(lbl_url, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self.txt_url, 1, wx.EXPAND | wx.RIGHT, 6)
        row.Add(self.btn_go, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

        # Info
        self.lbl_status = wx.StaticText(
            panel,
            label=_(
                "Entrez l'adresse du site et connectez-vous dans le navigateur dédié à\n"
                "DownAccess qui va s'ouvrir. C'est un navigateur séparé de votre navigation\n"
                "habituelle : vous restez connecté une fois pour toutes, et vos cookies sont\n"
                "réutilisés automatiquement pour les téléchargements.\n\n"
                "Note : les contenus protégés par DRM ne sont pas pris en charge."
            ),
        )
        sizer.Add(self.lbl_status, 1, wx.EXPAND | wx.ALL, 8)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_clear_cookies = wx.Button(
            panel,
            label=_("Supprimer les cookies du site"),
            name=_("Supprimer les cookies du site actuellement ouvert"),
        )
        self.btn_clear_cookies.Disable()
        self.btn_close = wx.Button(panel, wx.ID_CLOSE, label=_("Fermer"), name=_("Fermer"))
        btn_sizer.Add(self.btn_clear_cookies, 0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_close, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)
        self.txt_url.SetFocus()

    def _bind_events(self) -> None:
        self.txt_url.Bind(wx.EVT_TEXT_ENTER, self._on_go)
        self.btn_go.Bind(wx.EVT_BUTTON, self._on_go)
        self.btn_clear_cookies.Bind(wx.EVT_BUTTON, self._on_clear_cookies)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _e: self.Close())
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_go(self, _event) -> None:
        url = self.txt_url.GetValue().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.txt_url.SetValue(url)

        self.lbl_status.SetLabel(_("Ouverture du navigateur…"))
        self.btn_go.Disable()

        def open_browser():
            try:
                if self._page is None:
                    self._page = open_dedicated_browser(url)
                else:
                    self._page.get(url)
                title = self._page.title
                wx.CallAfter(self._on_browser_ready, title)
            except Exception as exc:
                _log.error("Impossible d'ouvrir le navigateur : %s", exc)
                wx.CallAfter(self._on_browser_error, friendly_browser_error(exc))

        threading.Thread(target=open_browser, daemon=True).start()

    def _on_browser_ready(self, title: str) -> None:
        self.lbl_status.SetLabel(
            _(
                "Le navigateur DownAccess est ouvert sur : {title}\n\n"
                "Connectez-vous, puis fermez cette fenêtre. Si vous êtes déjà connecté,\n"
                "il n'y a rien à faire. Vos cookies sont conservés pour les prochains téléchargements."
            ).format(title=title)
        )
        speech.speak(
            _("Le navigateur DownAccess est ouvert. Connectez-vous puis fermez cette fenêtre.")
        )
        self.btn_go.Enable()
        self.btn_clear_cookies.Enable()

    def _on_browser_error(self, error: str) -> None:
        self.btn_go.Enable()
        self.lbl_status.SetLabel(_("Erreur : {error}").format(error=error))
        wx.MessageBox(
            _("Impossible d'ouvrir le navigateur.\n\n{error}").format(error=error),
            _("Erreur"),
            wx.OK | wx.ICON_ERROR,
            self,
        )

    def _on_clear_cookies(self, _event) -> None:
        """Supprime les cookies du site actuellement ouvert."""
        if not self._page:
            return
        try:
            current_url = self._page.url
            # Extraire le domaine
            from urllib.parse import urlparse
            domain = urlparse(current_url).hostname or ""
            if not domain:
                wx.MessageBox(
                    _("Impossible de déterminer le domaine du site."),
                    _("Erreur"), wx.OK | wx.ICON_WARNING, self,
                )
                return

            confirm = wx.MessageBox(
                _("Supprimer tous les cookies de {domain} ?\n\nVous serez déconnecté de ce site.").format(domain=domain),
                _("Confirmer la suppression"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if confirm != wx.YES:
                return

            # Supprimer les cookies via CDP
            self._page.run_cdp(
                "Network.deleteCookies",
                domain=domain,
                name="",
            )
            # Supprimer aussi avec le point devant (sous-domaines)
            self._page.run_cdp(
                "Network.deleteCookies",
                domain=f".{domain}",
                name="",
            )
            # Recharger la page pour refléter la déconnexion
            self._page.refresh()
            self.lbl_status.SetLabel(
                _("Cookies de {domain} supprimés.\nVous êtes déconnecté de ce site.").format(domain=domain)
            )
            speech.speak(_("Cookies de {domain} supprimés.").format(domain=domain))
        except Exception as exc:
            _log.error("Erreur suppression cookies : %s", exc)
            wx.MessageBox(
                _("Erreur lors de la suppression des cookies :\n{error}").format(error=exc),
                _("Erreur"), wx.OK | wx.ICON_ERROR, self,
            )

    def _on_close(self, event) -> None:
        if self._page:
            # Récolter les cookies de la session AVANT de fermer le navigateur :
            # ils sont déjà déchiffrés ici (CDP), ce qui contourne le chiffrement
            # App-Bound de Chrome 127+ que yt-dlp ne sait pas lire.
            self._save_session_cookies()
            try:
                self._page.quit()
            except Exception:
                pass
            self._page = None
        event.Skip()

    def _save_session_cookies(self) -> None:
        """Écrit les cookies du site ouvert dans un jar persistant et mémorise
        le site, pour que yt-dlp les réutilise aux prochains téléchargements."""
        try:
            current_url = self._page.url or ""
            domain = (urlparse(current_url).hostname or "").lower()
            if not domain:
                return
            cookies = harvest_cookies(self._page)
            n = write_cookie_jar_from_dicts(cookies, jar_path_for(current_url))
            if n <= 0:
                return
            # Mémoriser le site dans les préférences (réutilise le dict en mémoire
            # de la fenêtre principale pour rester cohérent).
            parent = self.GetParent()
            settings = getattr(parent, "settings", None)
            if settings is not None:
                norm = domain[4:] if domain.startswith("www.") else domain
                sites = settings.setdefault("cookie_sites", [])
                if norm not in sites:
                    sites.append(norm)
                    from app.core import settings as cfg
                    cfg.save(settings)
            _log.info("Cookies du site %s récoltés (%d) à la connexion manuelle", domain, n)
        except Exception as exc:
            _log.error("Récolte des cookies impossible : %s", exc)
