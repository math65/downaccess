"""
Dialogue de connexion guidée (minimal), déclenché par un échec « connexion
nécessaire ».

Contrairement au menu « Se connecter à un site » (LoginDialog complet, avec
barre d'adresse), ce dialogue est volontairement minimal : il ouvre directement
le navigateur dédié sur le bon site, l'utilisateur se connecte, clique sur
« J'ai terminé », et le téléchargement reprend automatiquement.

Les cookies sont récoltés depuis la session navigateur (déjà déchiffrés via CDP)
et écrits dans un jar persistant — parade au chiffrement App-Bound de Chrome 127+
que yt-dlp ne sait pas déchiffrer.
"""
import logging
import threading
from collections.abc import Callable

import wx

from app.core import speech
from app.core.browser import harvest_cookies, harvest_cookies_headless, open_dedicated_browser
from app.core.cookies import jar_path_for, write_cookie_jar_from_dicts
from app.ui.login_dialog import friendly_browser_error

_log = logging.getLogger("downaccess.guided_login")


class GuidedLoginDialog(wx.Dialog):
    """Ouvre le navigateur dédié sur `site_url`, récolte les cookies à la
    confirmation, puis appelle `on_done(success: bool)`."""

    def __init__(self, parent, site_url: str, site_name: str,
                 on_done: Callable[[bool], None]):
        super().__init__(
            parent,
            title=_("Connexion à {site}").format(site=site_name),
            style=wx.DEFAULT_DIALOG_STYLE,
            size=(480, 240),
        )
        self._site_url = site_url
        self._site_name = site_name
        self._on_done = on_done
        self._page = None
        self._done_fired = False
        self._build_ui()
        self.Centre()
        speech.speak(
            _("Connectez-vous à {site} dans le navigateur, puis cliquez sur "
              "« J'ai terminé ».").format(site=site_name)
        )
        self._launch_browser()

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        msg = _(
            "DownAccess ouvre {site} dans son navigateur.\n\n"
            "Connectez-vous à votre compte, puis revenez ici et cliquez sur "
            "« J'ai terminé » : le téléchargement reprendra automatiquement.\n\n"
            "Inutile de fermer le navigateur vous-même, DownAccess s'en charge."
        ).format(site=self._site_name)

        # Message lu par NVDA au focus (un StaticText serait annoncé « panneau »).
        self.txt_status = wx.TextCtrl(
            self,
            value=msg,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,
            name=_("Connexion guidée"),
        )
        self.txt_status.SetBackgroundColour(self.GetBackgroundColour())
        sizer.Add(self.txt_status, 1, wx.EXPAND | wx.ALL, 14)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_done = wx.Button(self, wx.ID_OK,
                                  label=_("J'ai terminé"),
                                  name=_("J'ai terminé"))
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL,
                                    label=_("Annuler"),
                                    name=_("Annuler"))
        self.btn_done.Disable()  # actif une fois le navigateur prêt
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_done, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_cancel, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.btn_done.SetDefault()
        self.btn_done.Bind(wx.EVT_BUTTON, self._on_done_click)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self._on_cancel)
        self.Bind(wx.EVT_CLOSE, self._on_close_evt)

        self.SetSizer(sizer)
        self.txt_status.SetFocus()

    def _set_status(self, text: str) -> None:
        self.txt_status.SetValue(text)

    # ------------------------------------------------------------------
    # Lancement du navigateur (thread)
    # ------------------------------------------------------------------

    def _launch_browser(self) -> None:
        self._set_status(_("Ouverture du navigateur…"))

        def work():
            try:
                page = open_dedicated_browser(self._site_url)
                wx.CallAfter(self._on_browser_ready, page)
            except Exception as exc:
                _log.error("Ouverture du navigateur impossible : %s", exc)
                wx.CallAfter(self._on_browser_error, friendly_browser_error(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_browser_ready(self, page) -> None:
        self._page = page
        self.btn_done.Enable()
        self._set_status(
            _("Connectez-vous à {site} dans la fenêtre du navigateur, puis "
              "cliquez sur « J'ai terminé ».").format(site=self._site_name)
        )

    def _on_browser_error(self, message: str) -> None:
        wx.MessageBox(
            _("Impossible d'ouvrir le navigateur.\n\n{error}").format(error=message),
            _("Erreur"), wx.OK | wx.ICON_ERROR, self,
        )
        self._finish(False)

    # ------------------------------------------------------------------
    # Confirmation : récolte des cookies (thread)
    # ------------------------------------------------------------------

    def _on_done_click(self, _event) -> None:
        if not self._page:
            return
        self.btn_done.Disable()
        self.btn_cancel.Disable()
        self._set_status(_("Récupération de votre connexion…"))
        page = self._page

        def work():
            try:
                try:
                    cookies = harvest_cookies(page)
                except Exception as exc_live:
                    # La fenêtre a peut-être été fermée trop tôt -> repli headless
                    # sur le profil dédié persistant (la connexion y est conservée).
                    _log.warning("Récolte directe impossible (%s), repli headless", exc_live)
                    try:
                        page.quit()
                    except Exception:
                        pass
                    cookies = harvest_cookies_headless()
                write_cookie_jar_from_dicts(cookies, jar_path_for(self._site_url))
                wx.CallAfter(self._finish, True)
            except Exception as exc:
                _log.error("Récolte des cookies impossible : %s", exc)
                wx.CallAfter(self._on_harvest_error, friendly_browser_error(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_harvest_error(self, message: str) -> None:
        wx.MessageBox(
            _("Impossible de récupérer votre connexion.\n\n{error}").format(error=message),
            _("Erreur"), wx.OK | wx.ICON_ERROR, self,
        )
        self._finish(False)

    # ------------------------------------------------------------------
    # Fermeture
    # ------------------------------------------------------------------

    def _on_cancel(self, _event) -> None:
        self._finish(False)

    def _on_close_evt(self, event) -> None:
        self._quit_page()
        self._fire(False)
        event.Skip()

    def _quit_page(self) -> None:
        if self._page:
            try:
                self._page.quit()
            except Exception:
                pass
            self._page = None

    def _finish(self, success: bool) -> None:
        self._quit_page()
        self._fire(success)
        self.Destroy()

    def _fire(self, success: bool) -> None:
        if self._done_fired:
            return
        self._done_fired = True
        if self._on_done:
            wx.CallAfter(self._on_done, success)
