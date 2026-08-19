"""Fenetre « Nouveautes » : ce qui est arrive dans les abonnements.

Meme patron d'accessibilite que la selection d'une playlist : un `wx.ListCtrl`
avec cases a cocher natives (lues par NVDA), un compteur en texte, et le focus
qui arrive sur la liste et non sur un bouton.
"""

import wx

from app.core.i18n import _translate as _


class NewItemsDialog(wx.Dialog):
    """Liste les nouveautes de tous les abonnements et laisse choisir.

    `items` : liste de (titre_abonnement, FeedEntry, format_spec).
    """

    def __init__(self, parent, items: list):
        super().__init__(
            parent,
            title=_("Nouveautés de vos abonnements"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._items = items
        self._build_ui()
        self._bind_events()
        self.SetMinSize((720, 460))
        self.Fit()
        self.CentreOnParent()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label=_(
            "Sélectionnez ce que vous voulez télécharger ({count} nouveautés) :"
        ).format(count=len(self._items)))

        self.lst = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
            name=_("Nouveautés"),
        )
        self.lst.EnableCheckBoxes()
        self.lst.InsertColumn(0, _("Titre"), width=380)
        self.lst.InsertColumn(1, _("Source"), width=180)
        self.lst.InsertColumn(2, _("Date"), width=100)
        for i, (source, entry, _fmt) in enumerate(self._items):
            self.lst.InsertItem(i, entry.title or entry.url)
            self.lst.SetItem(i, 1, source)
            self.lst.SetItem(i, 2, entry.published_label())
            self.lst.CheckItem(i, True)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_all    = wx.Button(panel, label=_("Tout sélectionner"))
        self.btn_none   = wx.Button(panel, label=_("Tout désélectionner"))
        row.Add(self.btn_all, 0, wx.RIGHT, 6)
        row.Add(self.btn_none, 0)

        self.lbl_count = wx.StaticText(panel, label=self._count_label(len(self._items)))

        # Zone de resume : le programme sur lequel on est positionne.
        lbl_sum = wx.StaticText(panel, label=_("Résumé :"))
        self.txt_summary = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 70),
            name=_("Résumé"),
        )

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ok   = wx.Button(panel, wx.ID_OK, label=_("Télécharger la sélection"))
        self.btn_seen = wx.Button(panel, wx.ID_NO, label=_("Tout marquer comme vu"))
        self.btn_later = wx.Button(panel, wx.ID_CANCEL, label=_("Plus tard"))
        btns.AddStretchSpacer()
        btns.Add(self.btn_ok, 0, wx.RIGHT, 6)
        btns.Add(self.btn_seen, 0, wx.RIGHT, 6)
        btns.Add(self.btn_later, 0)

        sizer.Add(lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.lst, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.lbl_count, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(lbl_sum, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(sizer)

        self.btn_all.MoveAfterInTabOrder(self.lst)
        self.btn_none.MoveAfterInTabOrder(self.btn_all)
        self.txt_summary.MoveAfterInTabOrder(self.btn_none)
        self.btn_ok.MoveAfterInTabOrder(self.txt_summary)
        self.btn_seen.MoveAfterInTabOrder(self.btn_ok)
        self.btn_later.MoveAfterInTabOrder(self.btn_seen)

        if self._items:
            self.lst.Select(0)
            self.lst.Focus(0)
            self._show_summary(0)
        self.lst.SetFocus()

    def _bind_events(self) -> None:
        self.btn_all.Bind(wx.EVT_BUTTON, lambda _e: self._check_all(True))
        self.btn_none.Bind(wx.EVT_BUTTON, lambda _e: self._check_all(False))
        self.lst.Bind(wx.EVT_LIST_ITEM_CHECKED, self._on_check_change)
        self.lst.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self._on_check_change)
        self.lst.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.Bind(wx.EVT_BUTTON, self._on_seen, id=wx.ID_NO)

    # ------------------------------------------------------------------

    def _check_all(self, value: bool) -> None:
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, value)
        self._refresh_count()
        self.lst.SetFocus()

    def _on_check_change(self, _event) -> None:
        self._refresh_count()

    def _on_select(self, event) -> None:
        self._show_summary(event.GetIndex())
        event.Skip()

    def _show_summary(self, index: int) -> None:
        if 0 <= index < len(self._items):
            summary = self._items[index][1].summary or _("Aucun résumé disponible.")
            self.txt_summary.SetValue(summary)

    def _count_label(self, n: int) -> str:
        return _("{n} sélectionnées").format(n=n)

    def _refresh_count(self) -> None:
        n = sum(1 for i in range(self.lst.GetItemCount()) if self.lst.IsItemChecked(i))
        self.lbl_count.SetLabel(self._count_label(n))

    def _on_seen(self, _event) -> None:
        self.EndModal(wx.ID_NO)

    # ------------------------------------------------------------------

    def get_selected(self) -> list:
        """(titre_abonnement, FeedEntry, format_spec) des lignes cochees."""
        return [self._items[i] for i in range(self.lst.GetItemCount())
                if self.lst.IsItemChecked(i)]
