from urllib.parse import urlparse

import wx


# Choix de format (valeur retournée par get_format_choice())
FORMAT_AUTO       = "auto"
FORMAT_MP4        = "mp4"
FORMAT_MP3        = "mp3"
FORMAT_M4A        = "m4a"
FORMAT_SUBS_ONLY  = "subtitles_only"
FORMAT_MANUAL     = "manual"

# Codes internes des formats (jamais traduits). _format_labels() retourne les
# libelles localises au moment de la construction du dialogue.
_FORMAT_CODES = [
    FORMAT_AUTO,
    FORMAT_MP4,
    FORMAT_MP3,
    FORMAT_M4A,
    FORMAT_SUBS_ONLY,
    FORMAT_MANUAL,
]


def _format_labels() -> list[str]:
    return [
        _("Meilleure qualité automatique"),
        _("Vidéo MP4 (H.264)"),
        _("Audio MP3"),
        _("Audio M4A"),
        _("Sous-titres uniquement"),
        _("Choisir le format manuellement…"),
    ]


class AddUrlDialog(wx.Dialog):
    """
    Dialogue de saisie d'URL(s) à télécharger.
    Supporte plusieurs URLs (une par ligne) + choix de format.
    100 % accessible NVDA.
    """

    def __init__(self, parent, default_format: str = "auto",
                 initial_urls: str = "",
                 default_subtitles: bool = False):
        super().__init__(
            parent,
            title=_("Ajouter des URLs"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._default_format = default_format
        self._initial_urls = initial_urls
        self._default_subtitles = default_subtitles
        self._build_ui()
        self._bind_events()
        self.SetMinSize((480, 360))
        self.Fit()
        self.CentreOnParent()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Label + TextCtrl URLs
        lbl_urls = wx.StaticText(panel, label=_("URL(s) à télécharger (une par ligne) :"))
        self.txt_urls = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
            size=(-1, 120),
            name=_("URLs"),
        )
        self.txt_urls.SetHint("https://www.youtube.com/watch?v=...")

        # Format
        lbl_fmt = wx.StaticText(panel, label=_("Format de téléchargement :"))
        self.choice_fmt = wx.Choice(
            panel,
            choices=_format_labels(),
            name=_("Format de téléchargement"),
        )
        # Sélection par défaut selon les préférences (post_processing)
        try:
            default_idx = _FORMAT_CODES.index(self._default_format)
        except ValueError:
            default_idx = 0
        self.choice_fmt.SetSelection(default_idx)

        if self._initial_urls:
            self.txt_urls.SetValue(self._initial_urls)
            self.txt_urls.SetInsertionPointEnd()

        # Sous-titres (override par URL)
        self.chk_subtitles = wx.CheckBox(
            panel,
            label=_("Télécharger les sous-titres avec ce média"),
            name=_("Télécharger les sous-titres avec ce média"),
        )
        self.chk_subtitles.SetValue(self._default_subtitles)

        # Avertissement "Manuel + plusieurs URLs"
        self.lbl_manual_warn = wx.StaticText(
            panel,
            label=_("⚠ Mode manuel disponible pour une seule URL à la fois."),
        )
        self.lbl_manual_warn.Hide()

        # Boutons
        btn_sizer = wx.StdDialogButtonSizer()
        self.btn_ok     = wx.Button(panel, wx.ID_OK,     label=_("Ajouter à la file"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        self.btn_ok.SetDefault()
        btn_sizer.AddButton(self.btn_ok)
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.Realize()

        main_sizer.Add(lbl_urls,              0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        main_sizer.Add(self.txt_urls,         1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        main_sizer.Add(lbl_fmt,               0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        main_sizer.Add(self.choice_fmt,       0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        main_sizer.Add(self.chk_subtitles,    0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        main_sizer.Add(self.lbl_manual_warn,  0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
        main_sizer.Add(btn_sizer,             0, wx.EXPAND | wx.ALL, 12)

        panel.SetSizer(main_sizer)

        # Ordre Tab
        self.choice_fmt.MoveAfterInTabOrder(self.txt_urls)
        self.chk_subtitles.MoveAfterInTabOrder(self.choice_fmt)
        self.btn_ok.MoveAfterInTabOrder(self.chk_subtitles)
        self.btn_cancel.MoveAfterInTabOrder(self.btn_ok)

        self.txt_urls.SetFocus()

    def _bind_events(self) -> None:
        self.btn_ok.Bind(wx.EVT_BUTTON, self._on_ok)
        self.choice_fmt.Bind(wx.EVT_CHOICE, self._on_format_change)
        self.txt_urls.Bind(wx.EVT_TEXT, self._on_text_change)

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _on_format_change(self, _event) -> None:
        self._update_manual_warn()

    def _on_text_change(self, _event) -> None:
        self._update_manual_warn()

    def _update_manual_warn(self) -> None:
        is_manual   = self.get_format_choice() == FORMAT_MANUAL
        multi_urls  = len(self.get_urls()) > 1
        show_warn   = is_manual and multi_urls
        if show_warn:
            self.lbl_manual_warn.Show()
        else:
            self.lbl_manual_warn.Hide()
        self.Layout()

    def _on_ok(self, _event) -> None:
        urls = self.get_urls()
        if not urls:
            wx.MessageBox(
                _("Veuillez saisir au moins une URL."),
                _("URL manquante"),
                wx.OK | wx.ICON_WARNING,
                self,
            )
            self.txt_urls.SetFocus()
            return

        # Valider que les URLs pointent vers un contenu (pas un domaine nu)
        for url in urls:
            parsed = urlparse(url if "://" in url else f"https://{url}")
            path = parsed.path.rstrip("/")
            query = parsed.query
            if not path and not query:
                wx.MessageBox(
                    _("L'URL « {url} » semble pointer vers la page d'accueil d'un site et non vers une vidéo.\n\nCopiez l'URL complète d'une vidéo spécifique.").format(url=url),
                    _("URL invalide"),
                    wx.OK | wx.ICON_WARNING,
                    self,
                )
                self.txt_urls.SetFocus()
                return

        # Manuel + plusieurs URLs → forcer Auto
        if self.get_format_choice() == FORMAT_MANUAL and len(urls) > 1:
            if wx.MessageBox(
                _("Le mode 'Choisir le format manuellement' n'est disponible que pour une seule URL à la fois.\n\nContinuer en mode 'Meilleure qualité automatique' ?"),
                _("Format manuel indisponible"),
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            ) == wx.YES:
                self.choice_fmt.SetSelection(0)
            else:
                return

        self.EndModal(wx.ID_OK)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_urls(self) -> list[str]:
        raw = self.txt_urls.GetValue()
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def get_format_choice(self) -> str:
        idx = self.choice_fmt.GetSelection()
        if 0 <= idx < len(_FORMAT_CODES):
            return _FORMAT_CODES[idx]
        return FORMAT_AUTO

    def get_subtitles(self) -> bool:
        return self.chk_subtitles.GetValue()
