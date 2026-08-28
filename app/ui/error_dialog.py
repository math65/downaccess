"""
Dialogue d'erreur de téléchargement avec bouton "Envoyer un rapport".

Note : les échecs dus à une connexion requise (vidéo réservée aux adultes,
privée ou aux membres) ne passent PAS par ce dialogue — ils déclenchent le
parcours de connexion guidée (voir MainWindow._on_login_required).
"""
import wx

# Actions possibles retournées par le dialogue
ACTION_CLOSE  = "close"
ACTION_REPORT = "report"
ACTION_AUDIO  = "audio"


class ErrorDialog(wx.Dialog):
    """
    Affiche le message d'erreur et propose deux actions :
    - Fermer (défaut)
    - Envoyer un rapport d'erreur

    Et, quand le site ne laisse passer que la bande-son (`audio_offer`), une
    troisième : relancer en MP3. Sans elle, le message expliquait la marche à
    suivre et laissait l'utilisateur refaire l'ajout à la main — deux
    testeurs sont allés changer le format dans les Préférences, ce qui ne
    relance pas le téléchargement déjà refusé (2026-08-28).
    """

    def __init__(self, parent, message: str, audio_offer: bool = False):
        super().__init__(
            parent,
            title=_("Erreur de téléchargement"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(520, 300),
        )
        self._action = ACTION_CLOSE
        self._build_ui(message, audio_offer)
        self.btn_close.SetFocus()
        self.Centre()

    def _build_ui(self, message: str, audio_offer: bool = False) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(self, label=_("Une erreur s'est produite :"))
        sizer.Add(lbl, 0, wx.ALL, 12)

        lbl_msg = wx.StaticText(self, label=message)
        lbl_msg.Wrap(480)
        sizer.Add(lbl_msg, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_close   = wx.Button(self, wx.ID_OK,
                                     label=_("Fermer"),
                                     name=_("Fermer"))
        self.btn_report  = wx.Button(self, wx.ID_HELP,
                                     label=_("Envoyer un rapport d'erreur"),
                                     name=_("Envoyer un rapport d'erreur"))
        btn_sizer.AddStretchSpacer()
        # En tête : c'est l'action utile ici, donc la première atteinte par
        # Tab depuis le message.
        self.btn_audio = None
        if audio_offer:
            self.btn_audio = wx.Button(self, wx.ID_YES,
                                       label=_("Télécharger le son (MP3)"),
                                       name=_("Télécharger le son (MP3)"))
            btn_sizer.Add(self.btn_audio, 0, wx.RIGHT, 8)
            self.btn_audio.Bind(wx.EVT_BUTTON, self._on_audio)
        btn_sizer.Add(self.btn_close,   0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_report,  0, wx.RIGHT, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.btn_close.Bind(wx.EVT_BUTTON,   self._on_close)
        self.btn_report.Bind(wx.EVT_BUTTON,  self._on_report)

        self.SetSizer(sizer)

    def _on_close(self, _event) -> None:
        self._action = ACTION_CLOSE
        self.EndModal(wx.ID_OK)

    def _on_report(self, _event) -> None:
        self._action = ACTION_REPORT
        self.EndModal(wx.ID_HELP)

    def _on_audio(self, _event) -> None:
        self._action = ACTION_AUDIO
        self.EndModal(wx.ID_YES)

    @property
    def action(self) -> str:
        return self._action

    def wants_report(self) -> bool:
        return self._action == ACTION_REPORT

    def wants_audio(self) -> bool:
        """Vrai si l'utilisateur a demandé la bande-son plutôt que d'abandonner."""
        return self._action == ACTION_AUDIO
