"""
SearchDialog — saisie de la recherche (ou choix d'une catégorie à parcourir)
SearchResultsDialog — sélection des résultats, paginée
"""
import threading

import wx

from app.core import site_search, speech
from app.ui.player_dialog import PlayerDialog

# Code de retour « revenir à l'écran précédent » (bouton Retour). wx.ID_BACKWARD
# est un identifiant standard : NVDA lit le bouton normalement, et le code
# appelant distingue Retour d'une simple annulation.
RESULT_BACK = wx.ID_BACKWARD

# Sites supportés : (label affiché, clé interne).
# Clés yt-dlp (ytsearch/scsearch) = préfixe de recherche yt-dlp.
# Clés site (francetv/arte) = API HTTP dédiée (cf. app/core/site_search.py).
_SITES = [
    ("YouTube",    "ytsearch"),
    ("SoundCloud", "scsearch"),
    ("france.tv",  "francetv"),
    ("Arte",       "arte"),
]


def _search_types() -> list[tuple[str, str]]:
    """Types de résultat filtrables : (libellé affiché, code interne).

    Construits paresseusement pour que `_()` soit installé au moment de l'appel.
    Seul YouTube gère le filtre par type ; SoundCloud ne renvoie que des pistes.
    """
    return [
        (_("Tous types"), "all"),
        (_("Vidéos"),     "video"),
        (_("Playlists"),  "playlist"),
        (_("Chaînes"),    "channel"),
    ]


def _dl_type_label(code: str) -> str:
    """Convertit le code interne ('video' / 'track' / 'playlist' / 'channel')
    vers son libelle localise pour l'affichage dans la liste de resultats."""
    if code == "track":
        return _("Piste")
    if code == "playlist":
        return _("Playlist")
    if code == "channel":
        return _("Chaîne")
    return _("Vidéo")


class SearchDialog(wx.Dialog):
    """Saisie de la requête de recherche, ou choix d'une catégorie à parcourir.

    france.tv et Arte exposent un catalogue par catégorie : laisser la recherche
    vide et choisir une catégorie permet de parcourir sans connaître le titre
    exact d'une émission (demande utilisateur).
    """

    def __init__(self, parent):
        super().__init__(parent, title=_("Rechercher des médias"), style=wx.DEFAULT_DIALOG_STYLE)
        self._build_ui()
        self._on_site_change(None)
        self.txt_query.SetFocus()
        speech.speak(
            _("Fenêtre de recherche. Saisissez votre requête, choisissez le site, le type et le nombre de résultats.")
        )

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1)

        # Requête
        lbl_q = wx.StaticText(self, label=_("Recherche :"))
        self.txt_query = wx.TextCtrl(self, name=_("Requête de recherche"), style=wx.TE_PROCESS_ENTER)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        grid.Add(lbl_q, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.txt_query, 1, wx.EXPAND)

        # Site
        lbl_site = wx.StaticText(self, label=_("Site :"))
        self.choice_site = wx.Choice(
            self,
            choices=[s[0] for s in _SITES],
            name=_("Site de recherche"),
        )
        self.choice_site.SetSelection(0)
        self.choice_site.Bind(wx.EVT_CHOICE, self._on_site_change)
        grid.Add(lbl_site, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.choice_site, 1, wx.EXPAND)

        # Catégorie à parcourir (france.tv / Arte)
        lbl_cat = wx.StaticText(self, label=_("Catégorie à parcourir :"))
        self.choice_cat = wx.Choice(self, choices=[_("Aucune")],
                                    name=_("Catégorie à parcourir"))
        self.choice_cat.SetSelection(0)
        grid.Add(lbl_cat, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.choice_cat, 1, wx.EXPAND)

        # Type de résultat (YouTube uniquement)
        lbl_type = wx.StaticText(self, label=_("Type :"))
        self.choice_type = wx.Choice(
            self,
            choices=[t[0] for t in _search_types()],
            name=_("Type de résultat"),
        )
        self.choice_type.SetSelection(0)
        grid.Add(lbl_type, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.choice_type, 1, wx.EXPAND)

        # Nombre de résultats
        lbl_n = wx.StaticText(self, label=_("Résultats par page :"))
        self.spin_n = wx.SpinCtrl(
            self, min=1, max=50, initial=8,
            name=_("Nombre de résultats par page"),
        )
        grid.Add(lbl_n, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.spin_n, 0)

        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        self.lbl_hint = wx.StaticText(self, label="")
        sizer.Add(self.lbl_hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.Centre()

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_site_change(self, _event) -> None:
        """Adapte les contrôles au site : filtre de type (YouTube seulement) et
        catégories à parcourir (france.tv / Arte seulement)."""
        site = self.get_site_prefix()

        is_youtube = site == "ytsearch"
        if not is_youtube:
            self.choice_type.SetSelection(0)
        self.choice_type.Enable(is_youtube)

        cats = site_search.categories(site)
        self._categories = cats
        self.choice_cat.Set([_("Aucune")] + [label for _code, label in cats])
        self.choice_cat.SetSelection(0)
        self.choice_cat.Enable(bool(cats))
        if cats:
            self.lbl_hint.SetLabel(_(
                "Laissez la recherche vide et choisissez une catégorie pour "
                "parcourir le catalogue."
            ))
        else:
            self.lbl_hint.SetLabel(_("Ce site ne permet que la recherche par mots-clés."))
        self.Layout()
        self.Fit()

    def _on_ok(self, _event) -> None:
        if not self.get_query() and not self.get_category():
            msg = _("Saisissez une requête, ou choisissez une catégorie à parcourir.")
            speech.speak(msg)
            wx.MessageBox(msg, _("Champ requis"), wx.OK | wx.ICON_INFORMATION, self)
            self.txt_query.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_query(self) -> str:
        return self.txt_query.GetValue().strip()

    def get_category(self) -> str:
        """Code de la catégorie à parcourir, ou "" si recherche par mots-clés.

        Une requête saisie l'emporte : la catégorie ne sert qu'à parcourir.
        """
        if self.txt_query.GetValue().strip():
            return ""
        idx = self.choice_cat.GetSelection()
        if idx <= 0 or not getattr(self, "_categories", None):
            return ""
        return self._categories[idx - 1][0]

    def get_site_prefix(self) -> str:
        return _SITES[self.choice_site.GetSelection()][1]

    def get_site_label(self) -> str:
        return _SITES[self.choice_site.GetSelection()][0]

    def get_category_label(self) -> str:
        idx = self.choice_cat.GetSelection()
        if idx <= 0 or not getattr(self, "_categories", None):
            return ""
        return self._categories[idx - 1][1]

    def get_search_type(self) -> str:
        if not self.choice_type.IsEnabled():
            return "all"
        return _search_types()[self.choice_type.GetSelection()][1]

    def get_n(self) -> int:
        return self.spin_n.GetValue()


# Etats de coche affiches dans la colonne 0 — internes ET visibles.
# Stockes ici pour referer leur valeur courante apres traduction.
def _checked_label() -> str:
    return _("Coché")


def _unchecked_label() -> str:
    return _("Non coché")


def _entry_key(entry: dict) -> str:
    """Cle stable d'une entree, pour retenir les coches d'une page a l'autre."""
    return str(entry.get("id") or entry.get("webpage_url") or entry.get("url") or id(entry))


class SearchResultsDialog(wx.Dialog):
    """
    Affiche les résultats de recherche dans une ListCtrl avec cases à cocher.
    L'utilisateur sélectionne puis clique Télécharger.

    Pagination (`fetch_page`) selon le réglage `results_paging` :
    - "pages"      : boutons Page précédente / Page suivante ;
    - "continuous" : la suite se charge toute seule en arrivant en bas de liste.

    Les cases cochées sont retenues **d'une page à l'autre** (`_checked`) : sans
    cela, changer de page effacerait silencieusement la sélection.
    """

    def __init__(self, parent, site_label: str, results: list[dict],
                 settings: dict | None = None, fetch_page=None,
                 page: int = 1, total_pages: int = 1, total_count: int = 0,
                 allow_back: bool = False, paging_mode: str = "pages"):
        super().__init__(
            parent,
            title=_("Résultats — {site}").format(site=site_label),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(880, 560),
        )
        self._results = list(results)
        self._settings = settings or {}
        self._fetch_page = fetch_page
        self._page = page
        self._total_pages = max(1, total_pages)
        self._total_count = total_count
        self._allow_back = allow_back
        self._continuous = (paging_mode == "continuous") and fetch_page is not None
        self._loading = False
        # Coches memorisees par cle d'entree (ordre d'insertion = ordre d'ajout
        # a la file). Indispensable en pagination : les entrees d'une autre page
        # ne sont plus dans la liste affichee.
        self._checked: dict[str, dict] = {}

        self._build_ui(site_label)
        self._populate()
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.lst.SetFocus()
        if self.lst.GetItemCount():
            self.lst.Focus(0)
            self.lst.Select(0)
        speech.speak(self._intro_message())

    def _intro_message(self) -> str:
        n = len(self._results)
        if n > 1:
            msg = _("{count} résultats trouvés.").format(count=n)
        else:
            msg = _("{count} résultat trouvé.").format(count=n)
        msg += " " + _(
            "Utilisez les flèches pour naviguer, Espace pour cocher, "
            "Entrée pour l'aperçu, Tabulation pour lire le résumé."
        )
        if self._total_pages > 1 and not self._continuous:
            msg += " " + _("Page {page} sur {total}.").format(
                page=self._page, total=self._total_pages)
        return msg

    def _build_ui(self, site_label: str) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(
            self,
            label=_("Résultats de recherche — {site} :").format(site=site_label),
        )
        sizer.Add(lbl, 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)

        self.lst = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_HRULES | wx.BORDER_SUNKEN,
            name=_("Liste des résultats"),
        )
        self.lst.EnableCheckBoxes()
        self.lst.InsertColumn(0, _("Sélection"), width=100)
        self.lst.InsertColumn(1, _("Titre"),     width=360)
        self.lst.InsertColumn(2, _("Durée"),     width=80)
        self.lst.InsertColumn(3, _("Auteur"),    width=180)
        self.lst.InsertColumn(4, _("Type"),      width=80)
        sizer.Add(self.lst, 1, wx.EXPAND | wx.ALL, 8)

        # Résumé du résultat ayant le focus. TextCtrl lecture seule multiligne :
        # NVDA le lit integralement a la tabulation (un StaticText long est mal
        # restitue et ne peut pas etre parcouru).
        lbl_sum = wx.StaticText(self, label=_("Résumé :"))
        sizer.Add(lbl_sum, 0, wx.LEFT | wx.RIGHT, 10)
        self.txt_summary = wx.TextCtrl(
            self, value="", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
            size=(-1, 56), name=_("Résumé du résultat"),
        )
        sizer.Add(self.txt_summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Compteur de sélection + position dans la pagination
        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_count = wx.StaticText(self, label=_("0 sélectionné(s)"))
        self.lbl_page = wx.StaticText(self, label="")
        info_sizer.Add(self.lbl_count, 0, wx.RIGHT, 16)
        info_sizer.Add(self.lbl_page, 0)
        sizer.Add(info_sizer, 0, wx.LEFT | wx.BOTTOM, 10)

        # Format
        fmt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_fmt = wx.StaticText(self, label=_("Format :"))
        self.choice_fmt = wx.Choice(
            self,
            choices=[_("Auto"), "MP4", "MP3", "M4A"],
            name=_("Format de téléchargement"),
        )
        self.choice_fmt.SetSelection(0)
        fmt_sizer.Add(lbl_fmt, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        fmt_sizer.Add(self.choice_fmt, 0)
        sizer.Add(fmt_sizer, 0, wx.LEFT | wx.BOTTOM, 10)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_preview = wx.Button(self, label=_("Aperçu"), name=_("Aperçu"))
        self.btn_all   = wx.Button(self, label=_("Tout sélectionner"),   name=_("Tout sélectionner"))
        self.btn_none  = wx.Button(self, label=_("Tout désélectionner"), name=_("Tout désélectionner"))
        btn_sizer.Add(self.btn_preview, 0, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_all,   0, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_none,  0, wx.RIGHT, 6)

        # Pagination explicite (mode "pages" uniquement)
        self.btn_prev = self.btn_next = None
        if not self._continuous and self._fetch_page is not None:
            self.btn_prev = wx.Button(self, label=_("Page précédente"),
                                      name=_("Page précédente"))
            self.btn_next = wx.Button(self, label=_("Page suivante"),
                                      name=_("Page suivante"))
            btn_sizer.Add(self.btn_prev, 0, wx.LEFT | wx.RIGHT, 6)
            btn_sizer.Add(self.btn_next, 0, wx.RIGHT, 6)
            self.btn_prev.Bind(wx.EVT_BUTTON, self._on_prev_page)
            self.btn_next.Bind(wx.EVT_BUTTON, self._on_next_page)

        btn_sizer.AddStretchSpacer()
        if self._allow_back:
            self.btn_back = wx.Button(self, RESULT_BACK, label=_("Retour"))
            btn_sizer.Add(self.btn_back, 0, wx.RIGHT, 6)
            self.Bind(wx.EVT_BUTTON, self._on_back, id=RESULT_BACK)
        self.btn_dl    = wx.Button(self, wx.ID_OK, label=_("Télécharger la sélection"))
        self.btn_close = wx.Button(self, wx.ID_CANCEL, label=_("Fermer"))
        btn_sizer.Add(self.btn_dl,    0, wx.RIGHT, 6)
        btn_sizer.Add(self.btn_close, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(sizer)
        self.Centre()

        self.lst.Bind(wx.EVT_LIST_ITEM_CHECKED,   self._on_check)
        self.lst.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self._on_check)
        self.lst.Bind(wx.EVT_LIST_ITEM_FOCUSED,   self._on_item_focused)
        self.lst.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self.lst.Bind(wx.EVT_LEFT_DCLICK, self._on_preview)
        self.btn_preview.Bind(wx.EVT_BUTTON, self._on_preview)
        self.btn_all.Bind(wx.EVT_BUTTON,  self._on_select_all)
        self.btn_none.Bind(wx.EVT_BUTTON, self._on_select_none)
        self.Bind(wx.EVT_BUTTON, self._on_download, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._on_cancel,   id=wx.ID_CANCEL)

    # -- Remplissage -----------------------------------------------------

    def _populate(self, append: bool = False) -> None:
        if not append:
            self.lst.DeleteAllItems()
        for entry in (self._results[self.lst.GetItemCount():] if append else self._results):
            title = entry.get("title") or entry.get("id") or "?"
            if entry.get("_has_ad"):
                # Signale aux utilisateurs deficients visuels que l'audiodescription
                # existe (lu par NVDA dans le titre).
                title = _("{title} — Audiodescription").format(title=title)
            checked = _entry_key(entry) in self._checked
            idx = self.lst.GetItemCount()
            self.lst.InsertItem(idx, _checked_label() if checked else _unchecked_label())
            self.lst.SetItem(idx, 1, title)
            self.lst.SetItem(idx, 2, _fmt_duration(entry.get("duration")))
            self.lst.SetItem(idx, 3, entry.get("uploader") or entry.get("channel") or "—")
            self.lst.SetItem(idx, 4, _dl_type_label(entry.get("_dl_type") or "video"))
            if checked:
                self.lst.CheckItem(idx, True)
        self._update_page_label()
        self._refresh_counter()

    def _update_page_label(self) -> None:
        if self._continuous:
            if self._total_count:
                self.lbl_page.SetLabel(_("{shown} sur {total} résultats").format(
                    shown=len(self._results), total=self._total_count))
            else:
                self.lbl_page.SetLabel("")
            return
        if self._total_pages > 1:
            self.lbl_page.SetLabel(_("Page {page} sur {total}").format(
                page=self._page, total=self._total_pages))
        else:
            self.lbl_page.SetLabel("")
        if self.btn_prev:
            self.btn_prev.Enable(self._page > 1 and not self._loading)
        if self.btn_next:
            self.btn_next.Enable(self._page < self._total_pages and not self._loading)

    # -- Pagination ------------------------------------------------------

    def _load_page(self, page: int, append: bool) -> None:
        """Charge une page en arriere-plan (appel reseau) sans figer l'interface."""
        if self._loading or self._fetch_page is None:
            return
        self._loading = True
        self._update_page_label()
        speech.speak(_("Chargement…"))
        fetch = self._fetch_page

        def worker():
            try:
                result = fetch(page)
            except Exception as exc:
                result = {"error": str(exc)}
            wx.CallAfter(self._on_page_loaded, result, append)

        threading.Thread(target=worker, daemon=True).start()

    def _on_page_loaded(self, result: dict, append: bool) -> None:
        self._loading = False
        if "error" in result:
            self._update_page_label()
            wx.MessageBox(
                _("Impossible de charger la suite des résultats :\n\n{error}").format(
                    error=result["error"]),
                _("Erreur"), wx.OK | wx.ICON_ERROR, self,
            )
            return

        entries = result.get("entries") or []
        self._page = result.get("page", self._page)
        self._total_pages = max(1, result.get("total_pages", self._total_pages))
        self._total_count = result.get("total_count", self._total_count)

        if not entries:
            self._update_page_label()
            speech.speak(_("Aucun résultat supplémentaire."))
            return

        if append:
            first_new = len(self._results)
            self._results.extend(entries)
            self._populate(append=True)
            self.lst.Focus(first_new)
            self.lst.Select(first_new)
            speech.speak(_("{count} résultats supplémentaires chargés.").format(
                count=len(entries)))
        else:
            self._results = entries
            self._populate()
            if self.lst.GetItemCount():
                self.lst.Focus(0)
                self.lst.Select(0)
            speech.speak(_("Page {page} sur {total}. {count} résultats.").format(
                page=self._page, total=self._total_pages, count=len(entries)))
        self.lst.SetFocus()

    def _on_prev_page(self, _event) -> None:
        if self._page > 1:
            self._load_page(self._page - 1, append=False)

    def _on_next_page(self, _event) -> None:
        if self._page < self._total_pages:
            self._load_page(self._page + 1, append=False)

    def _maybe_load_more(self, idx: int) -> None:
        """Mode continu : arriver sur la derniere ligne charge la suite."""
        if not self._continuous or self._loading:
            return
        if self._page >= self._total_pages:
            return
        if idx >= self.lst.GetItemCount() - 1:
            self._load_page(self._page + 1, append=True)

    # -- Selection / resume ----------------------------------------------

    def _on_item_focused(self, event) -> None:
        idx = event.GetIndex()
        if 0 <= idx < len(self._results):
            entry = self._results[idx]
            # `_summary` : sites personnalises (site_search). `description` :
            # entrees yt-dlp, qui en fournissent une meme en extraction a plat.
            summary = entry.get("_summary") or entry.get("description") or ""
            self.txt_summary.SetValue(summary or _("(pas de résumé disponible)"))
        self._maybe_load_more(idx)
        event.Skip()

    def _on_check(self, event) -> None:
        idx = event.GetIndex() if event else -1
        checked = False
        if idx >= 0:
            checked = self.lst.IsItemChecked(idx)
            self.lst.SetItem(idx, 0, _checked_label() if checked else _unchecked_label())
            if 0 <= idx < len(self._results):
                entry = self._results[idx]
                key = _entry_key(entry)
                if checked:
                    self._checked[key] = entry
                else:
                    self._checked.pop(key, None)
        count_msg = self._refresh_counter()
        if idx >= 0:
            speech.speak(
                _("{state}. {title}. {count_msg}").format(
                    state=_("coché") if checked else _("non coché"),
                    title=self.lst.GetItemText(idx, 1),
                    count_msg=count_msg,
                )
            )
        else:
            speech.speak(count_msg)

    def _refresh_counter(self) -> str:
        n = len(self._checked)
        if n > 1:
            self.lbl_count.SetLabel(_("{count} sélectionnés").format(count=n))
            return _("{count} sélectionnés.").format(count=n)
        self.lbl_count.SetLabel(_("{count} sélectionné").format(count=n))
        return _("{count} sélectionné.").format(count=n)

    def _on_select_all(self, _event) -> None:
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, True)
            self.lst.SetItem(i, 0, _checked_label())
            if i < len(self._results):
                self._checked[_entry_key(self._results[i])] = self._results[i]
        speech.speak(self._refresh_counter())

    def _on_select_none(self, _event) -> None:
        """Decoche tout, y compris ce qui a ete coche sur les autres pages."""
        for i in range(self.lst.GetItemCount()):
            self.lst.CheckItem(i, False)
            self.lst.SetItem(i, 0, _unchecked_label())
        self._checked.clear()
        speech.speak(self._refresh_counter())

    # -- Clavier liste --------------------------------------------------

    def _on_list_key(self, event):
        """Entrée → aperçu ; autres touches → comportement natif."""
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_preview(None)
        else:
            event.Skip()

    # -- Aperçu audio --------------------------------------------------

    def _on_preview(self, _event) -> None:
        """Ouvre la fenêtre player pour le résultat ayant le focus."""
        idx = self.lst.GetFocusedItem()
        if idx < 0 or idx >= len(self._results):
            speech.speak(_("Sélectionnez un résultat."))
            return
        entry = self._results[idx]
        entry_type = entry.get("_dl_type") or "video"
        if entry_type in ("channel", "playlist"):
            label = _("une chaîne") if entry_type == "channel" else _("une playlist")
            wx.MessageBox(
                _("L'aperçu n'est pas disponible pour {label}.\n\nCochez l'élément et utilisez « Télécharger la sélection » pour récupérer son contenu.").format(label=label),
                _("Aperçu indisponible"),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        title = entry.get("title") or entry.get("id") or "?"
        url = self._entry_url(entry)
        if not url:
            return
        dlg = PlayerDialog(self, web_url=url, title=title)
        dlg.ShowModal()
        dlg.Destroy()

    def _entry_url(self, entry: dict) -> str:
        """Reconstruit l'URL web d'une entrée."""
        url = entry.get("webpage_url") or entry.get("url") or ""
        if url.startswith("francetv:"):
            return ""  # schéma interne yt-dlp : pas d'aperçu navigateur possible
        if url and not url.startswith("http"):
            ie_key = (entry.get("ie_key") or entry.get("extractor_key") or "").lower()
            vid_id = entry.get("id", "") or url
            if "youtube" in ie_key or not ie_key:
                url = f"https://www.youtube.com/watch?v={vid_id}"
            else:
                url = ""
        return url

    def _on_back(self, _event) -> None:
        self.EndModal(RESULT_BACK)

    def _on_close(self, _event) -> None:
        self.EndModal(wx.ID_CANCEL)

    def _on_cancel(self, _event) -> None:
        self.EndModal(wx.ID_CANCEL)

    def _on_destroy(self, event) -> None:
        event.Skip()

    # -- Téléchargement -------------------------------------------------

    def _on_download(self, _event) -> None:
        selected = self.get_selected_entries()
        if not selected:
            msg = _("Veuillez cocher au moins un résultat à télécharger (touche Espace).")
            speech.speak(msg)
            wx.MessageBox(msg, _("Aucune sélection"), wx.OK | wx.ICON_INFORMATION, self)
            return

        bulk_types = {e.get("_dl_type") for e in selected
                      if e.get("_dl_type") in ("channel", "playlist")}
        if bulk_types:
            from app.ui.confirm_dialog import confirm_with_memory
            labels = []
            if "channel" in bulk_types:
                labels.append(_("une chaîne (potentiellement des centaines de vidéos)"))
            if "playlist" in bulk_types:
                labels.append(_("une playlist complète"))
            joined = _(" et ").join(labels)
            if not confirm_with_memory(
                self, self._settings, "search_bulk_download",
                _("Votre sélection contient {labels}.\n\nLe téléchargement peut prendre beaucoup de temps et d'espace disque. Continuer ?").format(labels=joined),
                _("Téléchargement volumineux"),
            ):
                return

        self.EndModal(wx.ID_OK)

    def get_selected_entries(self) -> list[dict]:
        """Entrées cochées, toutes pages confondues (ordre de cochage)."""
        return list(self._checked.values())

    def get_page_state(self) -> dict:
        """Etat courant de pagination, pour rouvrir le dialogue a l'identique
        (retour depuis la selection des videos d'une playlist)."""
        return {
            "entries": list(self._results),
            "page": self._page,
            "total_pages": self._total_pages,
            "total_count": self._total_count,
        }

    def get_format(self) -> str:
        return ["auto", "mp4", "mp3", "m4a"][self.choice_fmt.GetSelection()]


def _fmt_duration(seconds) -> str:
    if not seconds:
        return "—"
    try:
        s = int(seconds)
        h, m = divmod(s, 3600)
        m, s = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except Exception:
        return "—"
