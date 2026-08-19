import wx

# Codes de statut internes (jamais traduits — utilises pour comparaison).
STATUS_PENDING    = "pending"
STATUS_PREPARING  = "preparing"
STATUS_ACTIVE     = "active"
STATUS_PAUSED     = "paused"
STATUS_PROCESSING = "processing"
STATUS_DONE       = "done"
STATUS_ALREADY    = "already"
STATUS_ERROR      = "error"


def _status_label(code: str) -> str:
    """Convertit un code de statut interne en libelle localise pour l'affichage."""
    if code == STATUS_PENDING:
        return _("En attente")
    if code == STATUS_PREPARING:
        return _("Préparation")
    if code == STATUS_ACTIVE:
        return _("En cours")
    if code == STATUS_PAUSED:
        return _("En pause")
    if code == STATUS_PROCESSING:
        return _("Traitement")
    if code == STATUS_DONE:
        return _("Terminé")
    if code == STATUS_ALREADY:
        return _("Déjà téléchargé")
    if code == STATUS_ERROR:
        return _("Erreur")
    return code


def _column_specs():
    """(label_localise, code_interne, largeur_px). Cle interne pour les comparaisons,
    libelle pour l'affichage."""
    return [
        (_("Titre"),       "title", 300),
        (_("Site"),        "site",  120),
        (_("Format"),      "fmt",    90),
        (_("Statut"),      "state", 110),
        (_("Progression"), "pct",   100),
        (_("Taille"),      "size",   80),
    ]


COL_TITLE = 0
COL_SITE  = 1
COL_FMT   = 2
COL_STATE = 3
COL_PCT   = 4
COL_SIZE  = 5


class DownloadList(wx.ListCtrl):
    """
    File de téléchargement affichée sous forme de tableau.
    Utilise wx.ListCtrl (Report) pour un support NVDA/MSAA natif optimal.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES | wx.BORDER_SUNKEN,
        )
        self.SetName(_("File de téléchargement"))
        self._setup_columns()
        # download_id (str) -> row index (int)
        self._items: dict[str, int] = {}
        # download_id (str) -> code de statut interne (str)
        self._status_codes: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_columns(self) -> None:
        for i, (label, _code, width) in enumerate(_column_specs()):
            self.InsertColumn(i, label, width=width)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_item(self, download_id: str, title: str, site: str, fmt: str = "") -> int:
        """Ajoute un item dans la liste. Retourne l'index de la ligne."""
        idx = self.GetItemCount()
        self.InsertItem(idx, title)
        self.SetItem(idx, COL_SITE,  site)
        self.SetItem(idx, COL_FMT,   fmt)
        self.SetItem(idx, COL_STATE, _status_label(STATUS_PENDING))
        self.SetItem(idx, COL_PCT,   "0 %")
        self.SetItem(idx, COL_SIZE,  "")
        self._items[download_id] = idx
        self._status_codes[download_id] = STATUS_PENDING
        # Sélectionner le nouvel item → NVDA l'annonce
        self.Select(idx)
        self.Focus(idx)
        return idx

    def update_info(self, download_id: str, title: str, site: str, fmt: str = "") -> None:
        """Met à jour titre, site et format une fois les métadonnées récupérées."""
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_TITLE, title)
        self.SetItem(idx, COL_SITE,  site)
        if fmt:
            self.SetItem(idx, COL_FMT, fmt)

    def update_progress(self, download_id: str, percent: float, size: str = "") -> None:
        """Met à jour la progression d'un téléchargement en cours."""
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_STATE, _status_label(STATUS_ACTIVE))
        self._status_codes[download_id] = STATUS_ACTIVE
        self.SetItem(idx, COL_PCT, f"{percent:.0f} %")
        if size:
            self.SetItem(idx, COL_SIZE, size)

    def set_status(self, download_id: str, code: str) -> None:
        """Definit le statut a partir d'un code interne (STATUS_*)."""
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_STATE, _status_label(code))
        self._status_codes[download_id] = code

    def complete_item(self, download_id: str, size: str = "") -> None:
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_STATE, _status_label(STATUS_DONE))
        self._status_codes[download_id] = STATUS_DONE
        self.SetItem(idx, COL_PCT, "100 %")
        if size:
            self.SetItem(idx, COL_SIZE, size)

    def already_downloaded_item(self, download_id: str, size: str = "") -> None:
        """Marque un item comme « Déjà téléchargé » (fichier déjà présent,
        yt-dlp n'a rien retéléchargé)."""
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_STATE, _status_label(STATUS_ALREADY))
        self._status_codes[download_id] = STATUS_ALREADY
        self.SetItem(idx, COL_PCT, "100 %")
        if size:
            self.SetItem(idx, COL_SIZE, size)

    def error_item(self, download_id: str) -> None:
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.SetItem(idx, COL_STATE, _status_label(STATUS_ERROR))
        self._status_codes[download_id] = STATUS_ERROR

    def remove_item(self, download_id: str) -> None:
        """Supprime un item par son download_id."""
        idx = self._items.get(download_id)
        if idx is None:
            return
        self.DeleteItem(idx)
        del self._items[download_id]
        self._status_codes.pop(download_id, None)
        self._items = {k: (v - 1 if v > idx else v) for k, v in self._items.items()}

    def count_by_status(self, code: str) -> int:
        """Compte les items ayant un code de statut donné."""
        return sum(1 for c in self._status_codes.values() if c == code)

    def remove_selected(self) -> str | None:
        """Supprime l'item sélectionné. Retourne son download_id ou None."""
        idx = self.GetFirstSelected()
        if idx == -1:
            return None
        dl_id = next((k for k, v in self._items.items() if v == idx), None)
        self.DeleteItem(idx)
        if dl_id:
            del self._items[dl_id]
            self._status_codes.pop(dl_id, None)
        # Réindexer les items dont le rang était supérieur à idx
        self._items = {
            k: (v - 1 if v > idx else v)
            for k, v in self._items.items()
        }
        return dl_id

    def get_selected_id(self) -> str | None:
        idx = self.GetFirstSelected()
        if idx == -1:
            return None
        return next((k for k, v in self._items.items() if v == idx), None)

    def get_selected_status(self) -> str | None:
        """Retourne le code de statut interne de l'item sélectionné, ou None."""
        dl_id = self.get_selected_id()
        if dl_id is None:
            return None
        return self._status_codes.get(dl_id)

    def get_selected_title(self) -> str:
        """Titre affiche de l'item selectionne (vide si aucune selection)."""
        dl_id = self.get_selected_id()
        if dl_id is None:
            return ""
        idx = self._items.get(dl_id)
        if idx is None:
            return ""
        return self.GetItemText(idx, COL_TITLE)

    def move_item_up(self, download_id: str) -> bool:
        idx = self._items.get(download_id)
        if idx is None or idx == 0:
            return False
        self._swap_rows(idx, idx - 1)
        for k in self._items:
            if self._items[k] == idx - 1 and k != download_id:
                self._items[k] = idx
                break
        self._items[download_id] = idx - 1
        self.Select(idx - 1)
        self.Focus(idx - 1)
        return True

    def move_item_down(self, download_id: str) -> bool:
        idx = self._items.get(download_id)
        if idx is None or idx >= self.GetItemCount() - 1:
            return False
        self._swap_rows(idx, idx + 1)
        for k in self._items:
            if self._items[k] == idx + 1 and k != download_id:
                self._items[k] = idx
                break
        self._items[download_id] = idx + 1
        self.Select(idx + 1)
        self.Focus(idx + 1)
        return True

    def _swap_rows(self, row_a: int, row_b: int) -> None:
        n_cols = len(_column_specs())
        data_a = [self.GetItemText(row_a, col) for col in range(n_cols)]
        data_b = [self.GetItemText(row_b, col) for col in range(n_cols)]
        for col, val in enumerate(data_b):
            self.SetItem(row_a, col, val)
        for col, val in enumerate(data_a):
            self.SetItem(row_b, col, val)

    def count(self) -> int:
        return self.GetItemCount()

    def get_all_ids(self) -> list[str]:
        """Retourne tous les download_id de la liste."""
        return list(self._items.keys())

    def clear_all(self) -> None:
        """Supprime tous les items de la liste."""
        self.DeleteAllItems()
        self._items.clear()
        self._status_codes.clear()
