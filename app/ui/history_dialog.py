"""Dialogue d'historique des téléchargements."""
import os
import subprocess
from datetime import datetime
from collections.abc import Callable

import wx

from app.core import history
from app.core.history import HistoryEntry


class HistoryDialog(wx.Dialog):
    """Affiche l'historique en wx.ListCtrl avec actions sur la sélection.

    Le callback `on_redownload(entry)` est appelé si l'utilisateur clique sur
    « Re-télécharger ». Le dialogue se ferme alors avec wx.ID_OK.
    """

    def __init__(self, parent,
                 on_redownload: Callable[[HistoryEntry], None] | None = None):
        super().__init__(
            parent,
            title=_("Historique des téléchargements"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._on_redownload = on_redownload
        self._entries: list[HistoryEntry] = history.load()
        self._build_ui()
        self._populate()
        self._bind_events()
        self.SetMinSize((720, 460))
        self.Fit()
        self.CentreOnParent()
        # Focus initial sur la liste (contenu, pas bouton)
        if self._entries:
            self.lst.Select(0)
            self.lst.Focus(0)
        self.lst.SetFocus()

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lbl_count = wx.StaticText(self, label="")
        self.lst = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
            name=_("Historique des téléchargements"),
        )
        self.lst.InsertColumn(0, _("Titre"),  width=320)
        self.lst.InsertColumn(1, _("Site"),   width=120)
        self.lst.InsertColumn(2, _("Format"), width=90)
        self.lst.InsertColumn(3, _("Date"),   width=130)
        self.lst.InsertColumn(4, _("Statut"), width=80)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open_file   = wx.Button(self, label=_("Ouvrir le &fichier"))
        self.btn_open_folder = wx.Button(self, label=_("Ouvrir le &dossier"))
        self.btn_copy_url    = wx.Button(self, label=_("&Copier l'URL"))
        self.btn_redownload  = wx.Button(self, label=_("&Re-télécharger"))
        self.btn_clear       = wx.Button(self, label=_("&Vider l'historique"))
        self.btn_close       = wx.Button(self, wx.ID_CLOSE, label=_("Fer&mer"))
        for b in (self.btn_open_file, self.btn_open_folder, self.btn_copy_url,
                  self.btn_redownload, self.btn_clear, self.btn_close):
            btn_sizer.Add(b, 0, wx.RIGHT, 6)

        sizer.Add(self.lbl_count, 0, wx.ALL, 8)
        sizer.Add(self.lst,       1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(btn_sizer,      0, wx.ALL, 8)
        self.SetSizer(sizer)

        self.btn_close.SetDefault()

    def _populate(self) -> None:
        self.lst.DeleteAllItems()
        for i, e in enumerate(self._entries):
            idx = self.lst.InsertItem(i, e.title or e.url)
            self.lst.SetItem(idx, 1, e.site or "")
            self.lst.SetItem(idx, 2, _format_label(e.format_spec))
            self.lst.SetItem(idx, 3, _format_date(e.timestamp))
            self.lst.SetItem(idx, 4, _("Réussi") if e.status == "success" else _("Échec"))
        self.lbl_count.SetLabel(_("{count} entrée(s)").format(count=len(self._entries)))

    def _bind_events(self) -> None:
        self.btn_open_file.Bind(wx.EVT_BUTTON,   self._on_open_file)
        self.btn_open_folder.Bind(wx.EVT_BUTTON, self._on_open_folder)
        self.btn_copy_url.Bind(wx.EVT_BUTTON,    self._on_copy_url)
        self.btn_redownload.Bind(wx.EVT_BUTTON,  self._on_redownload_clicked)
        self.btn_clear.Bind(wx.EVT_BUTTON,       self._on_clear)
        self.btn_close.Bind(wx.EVT_BUTTON,
                            lambda _e: self.EndModal(wx.ID_CLOSE))
        self.lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_open_file)

    def _selected(self) -> HistoryEntry | None:
        sel = self.lst.GetFirstSelected()
        if sel < 0 or sel >= len(self._entries):
            return None
        return self._entries[sel]

    def _on_open_file(self, _event) -> None:
        e = self._selected()
        if not e:
            return
        if not e.filepath or not os.path.exists(e.filepath):
            wx.MessageBox(
                _("Le fichier n'existe plus à cet emplacement."),
                _("Fichier introuvable"), wx.OK | wx.ICON_WARNING, self,
            )
            return
        try:
            os.startfile(e.filepath)
        except OSError as exc:
            wx.MessageBox(str(exc), _("Erreur"), wx.OK | wx.ICON_ERROR, self)

    def _on_open_folder(self, _event) -> None:
        e = self._selected()
        if not e or not e.filepath:
            wx.MessageBox(
                _("Aucun emplacement enregistré pour cette entrée."),
                _("Dossier introuvable"), wx.OK | wx.ICON_INFORMATION, self,
            )
            return
        folder = os.path.dirname(e.filepath)
        if not os.path.isdir(folder):
            wx.MessageBox(
                _("Le dossier n'existe plus :\n{folder}").format(folder=folder),
                _("Dossier introuvable"), wx.OK | wx.ICON_WARNING, self,
            )
            return
        if os.path.exists(e.filepath):
            subprocess.Popen(["explorer", "/select,", e.filepath])
        else:
            os.startfile(folder)

    def _on_copy_url(self, _event) -> None:
        e = self._selected()
        if not e or not e.url:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(e.url))
            finally:
                wx.TheClipboard.Close()
            wx.MessageBox(
                _("L'URL a été copiée dans le presse-papiers."),
                _("URL copiée"), wx.OK | wx.ICON_INFORMATION, self,
            )

    def _on_redownload_clicked(self, _event) -> None:
        e = self._selected()
        if not e:
            return
        if self._on_redownload is None:
            wx.MessageBox(
                _("Action indisponible."), _("Erreur"),
                wx.OK | wx.ICON_ERROR, self,
            )
            return
        self._on_redownload(e)
        self.EndModal(wx.ID_OK)

    def _on_clear(self, _event) -> None:
        if not self._entries:
            return
        if wx.MessageBox(
            _("Vider tout l'historique ? Cette action est irréversible."),
            _("Confirmer"), wx.YES_NO | wx.ICON_QUESTION, self,
        ) != wx.YES:
            return
        history.clear()
        self._entries = []
        self._populate()


def _format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso or ""


def _format_label(spec: str) -> str:
    if spec == "auto":
        return _("Auto")
    if spec == "subtitles_only":
        return _("Sous-titres")
    return (spec or "").upper()
