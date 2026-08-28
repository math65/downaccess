import wx

from app.core import speech
from app.core.custom_sites import lang_name

# Largeurs fixes des colonnes du tableau de formats (les libelles sont
# resolus a la construction du dialogue via _format_columns()).
_FORMAT_COLUMN_WIDTHS = [80, 70, 100, 110, 110, 90, 100, 120]


def _format_columns():
    return [
        (_("Format ID"),   _FORMAT_COLUMN_WIDTHS[0]),
        (_("Extension"),   _FORMAT_COLUMN_WIDTHS[1]),
        (_("Résolution"),  _FORMAT_COLUMN_WIDTHS[2]),
        (_("Codec vidéo"), _FORMAT_COLUMN_WIDTHS[3]),
        (_("Codec audio"), _FORMAT_COLUMN_WIDTHS[4]),
        # Sans cette colonne, les deux pistes d'une serie doublee (francais et
        # version originale, souvent au meme debit) sont indiscernables : le
        # choix manuel ne servait a rien pour en preferer une (Veronique,
        # 2026-08-28).
        (_("Langue"),      _FORMAT_COLUMN_WIDTHS[5]),
        (_("Taille est."), _FORMAT_COLUMN_WIDTHS[6]),
        (_("Note"),        _FORMAT_COLUMN_WIDTHS[7]),
    ]


class FormatDialog(wx.Dialog):
    """
    Sélecteur de format yt-dlp.
    Affiche la liste des formats disponibles pour une URL.
    100 % accessible NVDA.
    """

    def __init__(self, parent, title: str, formats: list[dict]):
        super().__init__(
            parent,
            title=_("Choisir le format — {title}").format(title=title),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._formats = formats
        self._selected_format_id: str | None = None
        self._build_ui()
        self._populate(formats)
        self._bind_events()
        self.SetMinSize((680, 380))
        self.Fit()
        self.CentreOnParent()
        speech.speak(
            _("Sélection du format pour {title}. {count} formats disponibles.").format(
                title=title, count=len(formats)
            )
        )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel,
            label=_("Sélectionnez le format à télécharger :"))
        self.lst = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SUNKEN,
            name=_("Liste des formats disponibles"),
        )
        for i, (col, width) in enumerate(_format_columns()):
            self.lst.InsertColumn(i, col, width=width)

        btn_sizer = wx.StdDialogButtonSizer()
        self.btn_ok     = wx.Button(panel, wx.ID_OK,     label=_("Télécharger ce format"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        self.btn_ok.SetDefault()
        self.btn_ok.Disable()
        btn_sizer.AddButton(self.btn_ok)
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.Realize()

        main_sizer.Add(lbl,       0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        main_sizer.Add(self.lst,  1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 12)

        panel.SetSizer(main_sizer)

        self.lst.MoveAfterInTabOrder(lbl)
        self.btn_ok.MoveAfterInTabOrder(self.lst)
        self.lst.SetFocus()

    def _populate(self, formats: list[dict]) -> None:
        # Afficher du meilleur au moins bon (inverser la liste yt-dlp)
        for fmt in reversed(formats):
            idx = self.lst.GetItemCount()
            fmt_id = fmt.get("format_id", "")
            ext    = fmt.get("ext", "")
            height = fmt.get("height")
            res    = f"{height}p" if height else (fmt.get("format_note") or "—")
            vcodec = _short_codec(fmt.get("vcodec", ""))
            acodec = _short_codec(fmt.get("acodec", ""))
            size   = _fmt_size(fmt.get("filesize") or fmt.get("filesize_approx"))
            note   = fmt.get("format_note") or ""
            # Pas de son -> pas de langue a annoncer (un flux video seul).
            langue = (lang_name(fmt.get("language"))
                      if fmt.get("language") else "—")

            self.lst.InsertItem(idx, fmt_id)
            self.lst.SetItem(idx, 1, ext)
            self.lst.SetItem(idx, 2, res)
            self.lst.SetItem(idx, 3, vcodec)
            self.lst.SetItem(idx, 4, acodec)
            self.lst.SetItem(idx, 5, langue)
            self.lst.SetItem(idx, 6, size)
            self.lst.SetItem(idx, 7, note)

    def _bind_events(self) -> None:
        self.lst.Bind(wx.EVT_LIST_ITEM_SELECTED,   self._on_select)
        self.lst.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_deselect)
        self.lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED,  self._on_activate)
        self.btn_ok.Bind(wx.EVT_BUTTON, self._on_ok)

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _on_select(self, event) -> None:
        self.btn_ok.Enable(True)
        event.Skip()

    def _on_deselect(self, _event) -> None:
        if self.lst.GetFirstSelected() == -1:
            self.btn_ok.Disable()

    def _on_activate(self, _event) -> None:
        # Double-clic ou Entrée → valider directement
        if self.lst.GetFirstSelected() != -1:
            self._on_ok(None)

    def _on_ok(self, _event) -> None:
        idx = self.lst.GetFirstSelected()
        if idx == -1:
            return
        # Récupérer le format_id depuis la liste (colonne 0)
        self._selected_format_id = self.lst.GetItemText(idx, 0)
        self.EndModal(wx.ID_OK)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_format_id(self) -> str | None:
        return self._selected_format_id


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _short_codec(codec: str) -> str:
    if not codec or codec == "none":
        return "—"
    return codec.split(".")[0][:10]


def _fmt_size(size) -> str:
    if not size:
        return "?"
    size = int(size)
    if size >= 1_073_741_824:
        return _("{n:.1f} Go").format(n=size / 1_073_741_824)
    if size >= 1_048_576:
        return _("{n:.0f} Mo").format(n=size / 1_048_576)
    if size >= 1024:
        return _("{n:.0f} Ko").format(n=size / 1024)
    return _("{n} o").format(n=size)
