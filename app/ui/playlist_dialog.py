import wx

from app.core import speech
from app.ui.search_dialog import RESULT_BACK

# Modes de numérotation des fichiers
NUMBER_ORIGINAL   = 0  # Numéro de la vidéo dans la playlist
NUMBER_SEQUENTIAL = 1  # Numéro séquentiel (1, 2, 3...)
NUMBER_NONE       = 2  # Pas de numérotation


class PlaylistDialog(wx.Dialog):
    """
    Dialogue de sélection des entrées d'une playlist.
    Accessible NVDA : wx.ListCtrl + EnableCheckBoxes() → cases à cocher
    natives UIA/MSAA lues par NVDA (Espace = coché/non coché annoncé).
    """

    def __init__(self, parent, playlist_title: str, entries: list[dict],
                 default_numbering: int = NUMBER_ORIGINAL,
                 allow_back: bool = False):
        super().__init__(
            parent,
            title=_("Playlist — {title}").format(title=playlist_title),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._entries = entries
        self._default_numbering = default_numbering
        # `allow_back` : la playlist a ete ouverte depuis les resultats de
        # recherche. Sans ce bouton, decouvrir que la playlist ne convient pas
        # obligeait a refaire toute la recherche (retour utilisateur).
        self._allow_back = allow_back
        self._build_ui(entries)
        self._bind_events()
        self.SetMinSize((560, 420))
        self.Fit()
        self.CentreOnParent()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self, entries: list[dict]) -> None:
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel,
            label=_("Sélectionnez les vidéos à télécharger ({count} entrées) :").format(count=len(entries)))

        # ListCtrl avec cases à cocher natives (UIA/MSAA → NVDA)
        self.lst = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
            name=_("Entrées de la playlist"),
        )
        self.lst.EnableCheckBoxes()
        self.lst.InsertColumn(0, _("Titre"), width=460)

        for i, entry in enumerate(entries):
            title = entry.get("title") or entry.get("url") or _("Entrée {n}").format(n=i + 1)
            self.lst.InsertItem(i, f"{i + 1}. {title}")
            self.lst.CheckItem(i, True)

        # Boutons de sélection rapide
        row_sel = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_all    = wx.Button(panel, label=_("Tout sélectionner"))
        self.btn_none   = wx.Button(panel, label=_("Tout désélectionner"))
        self.btn_invert = wx.Button(panel, label=_("Inverser la sélection"))
        row_sel.Add(self.btn_all,    0, wx.RIGHT, 6)
        row_sel.Add(self.btn_none,   0, wx.RIGHT, 6)
        row_sel.Add(self.btn_invert, 0)

        # Numérotation des fichiers
        self.radio_number = wx.RadioBox(
            panel,
            label=_("Numérotation des fichiers"),
            choices=[
                _("Numéro dans la playlist (position originale)"),
                _("Numéro séquentiel (1, 2, 3...)"),
                _("Ne pas numéroter"),
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Numérotation des fichiers"),
        )
        self.radio_number.SetSelection(self._default_numbering)

        # Compteur (StaticText mis à jour → NVDA peut le lire en naviguant)
        self.lbl_count = wx.StaticText(panel,
            label=self._count_label(len(entries)))

        # OK / Annuler
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = None
        if self._allow_back:
            self.btn_back = wx.Button(panel, RESULT_BACK,
                                      label=_("Retour aux résultats"),
                                      name=_("Retour aux résultats"))
            btn_sizer.Add(self.btn_back, 0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer()
        self.btn_ok     = wx.Button(panel, wx.ID_OK,     label=_("Télécharger la sélection"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        self.btn_ok.SetDefault()
        btn_sizer.Add(self.btn_ok, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_cancel, 0)

        main_sizer.Add(lbl,            0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        main_sizer.Add(self.lst,       1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        main_sizer.Add(row_sel,            0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        main_sizer.Add(self.radio_number, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        main_sizer.Add(self.lbl_count,    0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        main_sizer.Add(btn_sizer,         0, wx.EXPAND | wx.ALL, 12)

        panel.SetSizer(main_sizer)

        # Ordre Tab : liste → boutons rapides → OK → Annuler
        self.btn_all.MoveAfterInTabOrder(self.lst)
        self.btn_none.MoveAfterInTabOrder(self.btn_all)
        self.btn_invert.MoveAfterInTabOrder(self.btn_none)
        self.radio_number.MoveAfterInTabOrder(self.btn_invert)
        if self.btn_back is not None:
            self.btn_back.MoveAfterInTabOrder(self.radio_number)
            self.btn_ok.MoveAfterInTabOrder(self.btn_back)
        else:
            self.btn_ok.MoveAfterInTabOrder(self.radio_number)
        self.btn_cancel.MoveAfterInTabOrder(self.btn_ok)

        self.lst.SetFocus()

    def _bind_events(self) -> None:
        self.btn_all.Bind(wx.EVT_BUTTON,             self._on_all)
        self.btn_none.Bind(wx.EVT_BUTTON,            self._on_none)
        self.btn_invert.Bind(wx.EVT_BUTTON,          self._on_invert)
        self.btn_ok.Bind(wx.EVT_BUTTON,              self._on_ok)
        if self.btn_back is not None:
            self.btn_back.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(RESULT_BACK))
        self.lst.Bind(wx.EVT_LIST_ITEM_CHECKED,      self._on_check_change)
        self.lst.Bind(wx.EVT_LIST_ITEM_UNCHECKED,    self._on_check_change)

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _on_all(self, _event) -> None:
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, True)
        self._refresh_count(announce=True)

    def _on_none(self, _event) -> None:
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, False)
        self._refresh_count(announce=True)

    def _on_invert(self, _event) -> None:
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, not self.lst.IsItemChecked(i))
        self._refresh_count(announce=True)

    def _on_check_change(self, _event) -> None:
        self._refresh_count(announce=False)

    def _on_ok(self, _event) -> None:
        if not self.get_selected_entries():
            speech.speak(_("Veuillez sélectionner au moins une entrée."))
            wx.MessageBox(
                _("Veuillez sélectionner au moins une entrée."),
                _("Sélection vide"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self.lst.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _refresh_count(self, announce: bool = False) -> None:
        n = sum(1 for i in range(self.lst.GetItemCount()) if self.lst.IsItemChecked(i))
        label = self._count_label(n)
        self.lbl_count.SetLabel(label)
        if announce:
            speech.speak(label)

    def _count_label(self, n: int) -> str:
        return _("{selected} / {total} vidéo(s) sélectionnée(s)").format(
            selected=n, total=len(self._entries)
        )

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_selected_entries(self) -> list[tuple[int, dict]]:
        """Retourne les entrées sélectionnées avec leur index original (1-based)."""
        return [
            (i + 1, self._entries[i])
            for i in range(self.lst.GetItemCount())
            if self.lst.IsItemChecked(i)
        ]

    def get_numbering_mode(self) -> int:
        """Retourne NUMBER_ORIGINAL, NUMBER_SEQUENTIAL ou NUMBER_NONE."""
        return self.radio_number.GetSelection()
