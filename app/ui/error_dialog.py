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


class ErrorDialog(wx.Dialog):
    """
    Affiche le message d'erreur et propose deux actions :
    - Fermer (défaut)
    - Envoyer un rapport d'erreur
    """

    def __init__(self, parent, message: str):
        super().__init__(
            parent,
            title=_("Erreur de téléchargement"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(520, 300),
        )
        self._action = ACTION_CLOSE
        self._build_ui(message)
        self.btn_close.SetFocus()
        self.Centre()

    def _build_ui(self, message: str) -> None:
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

    @property
    def action(self) -> str:
        return self._action

    def wants_report(self) -> bool:
        return self._action == ACTION_REPORT
