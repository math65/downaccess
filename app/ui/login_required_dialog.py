"""
Dialogue « Connexion nécessaire ».

Affiché quand un téléchargement échoue parce que le site exige une connexion
(vidéo réservée aux adultes, privée ou réservée aux membres). Propose un
parcours unique et simple : se connecter via le navigateur dédié de DownAccess,
puis reprise automatique du téléchargement. Le mot « cookies » n'apparaît pas :
pour l'utilisateur, c'est juste « se connecter ».
"""
import wx


class LoginRequiredDialog(wx.Dialog):
    """
    Dialogue à deux choix :
    - Se connecter et télécharger (défaut)
    - Annuler
    """

    def __init__(self, parent, site_name: str):
        super().__init__(
            parent,
            title=_("Connexion nécessaire"),
            style=wx.DEFAULT_DIALOG_STYLE,
            size=(480, 260),
        )
        self._build_ui(site_name)
        self.Centre()

    def _build_ui(self, site_name: str) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        message = _(
            "Cette vidéo {site} est réservée aux personnes connectées à leur "
            "compte.\n\n"
            "DownAccess va ouvrir une fenêtre pour vous connecter, puis "
            "reprendra le téléchargement automatiquement."
        ).format(site=site_name)

        # Message dans un TextCtrl lecture seule : NVDA le lit au focus
        # (un wx.StaticText n'est pas focusable et serait annoncé « panneau »).
        self.txt_message = wx.TextCtrl(
            self,
            value=message,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,
            name=_("Connexion nécessaire"),
        )
        self.txt_message.SetBackgroundColour(self.GetBackgroundColour())
        sizer.Add(self.txt_message, 1, wx.EXPAND | wx.ALL, 14)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_login = wx.Button(
            self, wx.ID_OK,
            label=_("Se connecter et télécharger"),
            name=_("Se connecter et télécharger"),
        )
        self.btn_cancel = wx.Button(
            self, wx.ID_CANCEL,
            label=_("Annuler"),
            name=_("Annuler"),
        )
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_login, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_cancel, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.btn_login.SetDefault()
        self.SetSizer(sizer)
        # Focus initial sur le contenu (le message), pas sur un bouton.
        self.txt_message.SetFocus()

    def wants_login(self) -> bool:
        return self.GetReturnCode() == wx.ID_OK
