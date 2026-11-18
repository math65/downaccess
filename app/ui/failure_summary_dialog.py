"""
Bilan de fin de file : tous les téléchargements en échec, regroupés par cause.

Remplace la suite de fenêtres d'erreur (une par cause) par une seule, et offre
un seul rapport pour l'ensemble (cf. `app/core/error_summary.py`).
"""
import wx


class FailureSummaryDialog(wx.Dialog):

    def __init__(self, parent, summary: str):
        super().__init__(
            parent,
            title=_("Téléchargements en échec"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(600, 420),
        )
        self._report = False
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(self, label=_("Bilan des téléchargements en échec :"))
        sizer.Add(lbl, 0, wx.ALL, 12)
        # Zone de texte en lecture seule, et non un StaticText : NVDA la lit à
        # l'ouverture et l'utilisateur peut la parcourir ligne par ligne.
        self.txt_summary = wx.TextCtrl(
            self, value=summary,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            name=_("Bilan des téléchargements en échec"))
        sizer.Add(self.txt_summary, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_report = wx.Button(self, wx.ID_HELP,
                                    label=_("Envoyer un seul rapport pour tous"),
                                    name=_("Envoyer un seul rapport pour tous"))
        self.btn_close = wx.Button(self, wx.ID_CANCEL, label=_("Fermer"),
                                   name=_("Fermer"))
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_report, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_close, 0, wx.RIGHT, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.btn_report.Bind(wx.EVT_BUTTON, self._on_report)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.txt_summary.SetFocus()
        self.txt_summary.SetInsertionPoint(0)
        self.Centre()

    def _on_report(self, _event) -> None:
        self._report = True
        self.EndModal(wx.ID_HELP)

    def wants_report(self) -> bool:
        return self._report
