"""Fenetre de lecture d'une transcription.

Le texte est presente dans un `wx.TextCtrl` en lecture seule : le lecteur
d'ecran le parcourt ligne par ligne, mot par mot, et la recherche du curseur
fonctionne — ce qu'un `StaticText` ne permet pas. Le focus arrive sur le texte,
pas sur un bouton, pour que la lecture puisse commencer immediatement.
"""

import wx

from app.core.i18n import _translate as _


class TranscriptDialog(wx.Dialog):
    """Affiche la transcription d'un media et permet de l'enregistrer."""

    def __init__(self, parent, title: str, text: str, language: str = ""):
        super().__init__(
            parent,
            title=_("Transcription — {title}").format(title=title or _("média")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._text = text
        self._media_title = title
        self._build_ui(text, language)
        self.SetMinSize((640, 460))
        self.Fit()
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self._on_close, id=wx.ID_CANCEL)

    def _build_ui(self, text: str, language: str) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = (_("Transcription ({language}) :").format(language=language)
                 if language else _("Transcription :"))
        lbl = wx.StaticText(panel, label=label)

        self.txt = wx.TextCtrl(
            panel,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            name=_("Transcription"),
        )

        self.btn_save = wx.Button(panel, wx.ID_SAVE, label=_("Enregistrer en texte..."))
        self.btn_copy = wx.Button(panel, wx.ID_COPY, label=_("Copier tout"))
        self.btn_close = wx.Button(panel, wx.ID_CANCEL, label=_("Fermer"))

        btns = wx.BoxSizer(wx.HORIZONTAL)
        btns.Add(self.btn_save, 0, wx.RIGHT, 8)
        btns.Add(self.btn_copy, 0, wx.RIGHT, 8)
        btns.Add(self.btn_close, 0)

        sizer.Add(lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(btns, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(sizer)

        self.btn_save.Bind(wx.EVT_BUTTON, self._on_save)
        self.btn_copy.Bind(wx.EVT_BUTTON, self._on_copy)

        # Ordre de tabulation : le texte d'abord, puis les actions.
        self.btn_save.MoveAfterInTabOrder(self.txt)
        self.btn_copy.MoveAfterInTabOrder(self.btn_save)
        self.btn_close.MoveAfterInTabOrder(self.btn_copy)

        self.txt.SetInsertionPoint(0)
        self.txt.SetFocus()

    # ------------------------------------------------------------------

    def _default_filename(self) -> str:
        safe = "".join(c for c in (self._media_title or "transcription")
                       if c not in '<>:"/|?*' + chr(92))
        return (safe.strip() or "transcription")[:120] + ".txt"

    def _on_save(self, _event) -> None:
        with wx.FileDialog(
            self, _("Enregistrer la transcription"),
            defaultFile=self._default_filename(),
            wildcard=_("Fichier texte (*.txt)|*.txt"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._text)
        except OSError as exc:
            wx.MessageBox(
                _("La transcription n'a pas pu être enregistrée.\n\n{error}").format(error=exc),
                _("Enregistrement impossible"), wx.OK | wx.ICON_ERROR, self)
            return
        wx.MessageBox(
            _("Transcription enregistrée dans :\n{path}").format(path=path),
            _("Enregistrement terminé"), wx.OK | wx.ICON_INFORMATION, self)
        wx.CallAfter(self.txt.SetFocus)

    def _on_copy(self, _event) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._text))
            wx.TheClipboard.Close()
            wx.MessageBox(
                _("La transcription a été copiée dans le presse-papiers."),
                _("Copie effectuée"), wx.OK | wx.ICON_INFORMATION, self)
        wx.CallAfter(self.txt.SetFocus)

    def _on_close(self, _event) -> None:
        self.EndModal(wx.ID_CANCEL)
