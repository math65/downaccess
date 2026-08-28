"""Chercher par son nom la chaine, la collection ou le podcast a suivre.

Le pendant, pour les abonnements, du dialogue de recherche de medias : on tape
un nom, on choisit dans une liste, et l'adresse du flux est trouvee toute seule
(demande de Veronique, 2026-08-28 — jusqu'ici il fallait connaitre l'adresse).

Tout le travail reseau part dans un thread : chercher, puis resoudre l'adresse
d'un podcast, prennent chacun quelques secondes.
"""

import threading

import wx

from app.core import feed_search, speech
from app.core.i18n import _translate as _


class SubscriptionSearchDialog(wx.Dialog):
    """Recherche d'une source a suivre. `get_url()` apres un retour OK."""

    def __init__(self, parent):
        super().__init__(parent, title=_("Rechercher une chaîne ou un podcast"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._results: list[dict] = []
        self._chosen_url = ""
        self._chosen_title = ""
        # Une recherche lancee continue apres la fermeture de la fenetre : son
        # retour arrive par `wx.CallAfter` sur un objet C++ deja detruit, ce
        # qui fait tomber l'application. On note donc quand la fenetre s'en va.
        self._alive = True
        self._build_ui()
        self._bind_events()
        self.SetMinSize((640, 460))
        self.Fit()
        self.CentreOnParent()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_query = wx.StaticText(panel, label=_("Nom à rechercher :"))
        self.txt_query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER,
                                     name=_("Nom à rechercher"))
        self.txt_query.SetHint(_("France Inter, Arte, un titre d'émission…"))

        lbl_source = wx.StaticText(panel, label=_("Où chercher :"))
        self.choice_source = wx.Choice(panel, choices=feed_search.source_labels(),
                                       name=_("Où chercher"))
        self.choice_source.SetSelection(0)

        self.btn_search = wx.Button(panel, label=_("Rechercher"),
                                    name=_("Rechercher"))

        # Zone d'etat : le lecteur d'ecran doit pouvoir relire ce qui se passe
        # (recherche en cours, nombre de resultats, echec) sans que rien ne
        # soit annonce deux fois.
        self.lbl_status = wx.StaticText(panel, label=_("Aucune recherche lancée."))

        self.lst = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
            name=_("Résultats"),
        )
        self.lst.InsertColumn(0, _("Nom"), width=280)
        self.lst.InsertColumn(1, _("Publié par"), width=170)
        self.lst.InsertColumn(2, _("Détail"), width=160)

        self.btn_choose = wx.Button(panel, wx.ID_OK, label=_("Choisir"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        self.btn_choose.Enable(False)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(self.btn_choose, 0, wx.RIGHT, 8)
        row.Add(self.btn_cancel, 0)

        for widget in (lbl_query, self.txt_query, lbl_source,
                       self.choice_source, self.btn_search, self.lbl_status):
            sizer.Add(widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer.Add(self.lst, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(sizer)

        self.choice_source.MoveAfterInTabOrder(self.txt_query)
        self.btn_search.MoveAfterInTabOrder(self.choice_source)
        self.lst.MoveAfterInTabOrder(self.btn_search)
        self.btn_choose.MoveAfterInTabOrder(self.lst)
        self.btn_cancel.MoveAfterInTabOrder(self.btn_choose)

        self.txt_query.SetFocus()

    def _bind_events(self) -> None:
        self.btn_search.Bind(wx.EVT_BUTTON, self._on_search)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self.lst.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection)
        self.lst.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection)
        self.lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_choose)
        self.Bind(wx.EVT_BUTTON, self._on_choose, id=wx.ID_OK)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    def _on_destroy(self, event) -> None:
        # Filtre sur self : l'evenement remonte aussi pour chaque enfant.
        if event.GetWindow() is self:
            self._alive = False
        event.Skip()

    def _vivante(self) -> bool:
        """Faux des que la fenetre a disparu, de l'une ou l'autre facon.

        `bool(self)` devient faux quand l'objet C++ est reellement supprime,
        ce qui n'arrive qu'au tour de boucle suivant : le drapeau pose a la
        destruction couvre l'intervalle, ou un retour de thread arriverait
        sinon sur une fenetre en sursis.
        """
        return bool(self) and self._alive

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------

    def _source_code(self) -> str:
        idx = self.choice_source.GetSelection()
        if 0 <= idx < len(feed_search.SOURCE_CODES):
            return feed_search.SOURCE_CODES[idx]
        return feed_search.SOURCE_CODES[0]

    def _on_search(self, _event) -> None:
        query = self.txt_query.GetValue().strip()
        if not query:
            wx.MessageBox(_("Indiquez ce que vous cherchez."),
                          _("Recherche vide"), wx.OK | wx.ICON_WARNING, self)
            self.txt_query.SetFocus()
            return

        source = self._source_code()
        self._set_busy(True, _("Recherche en cours…"))

        def worker() -> None:
            try:
                results = feed_search.search(source, query)
            except feed_search.SearchError as exc:
                wx.CallAfter(self._on_search_failed, str(exc))
            except Exception as exc:
                wx.CallAfter(self._on_search_failed, str(exc))
            else:
                wx.CallAfter(self._on_search_done, results)

        threading.Thread(target=worker, daemon=True).start()

    def _on_search_done(self, results: list[dict]) -> None:
        if not self._vivante():
            return
        self._results = results
        self.lst.DeleteAllItems()
        for entry in results:
            idx = self.lst.InsertItem(self.lst.GetItemCount(), entry["title"])
            self.lst.SetItem(idx, 1, entry.get("author") or "—")
            self.lst.SetItem(idx, 2, entry.get("detail") or "")

        if results:
            if len(results) > 1:
                message = _("{n} résultats. Choisissez dans la liste.").format(
                    n=len(results))
            else:
                message = _("1 résultat. Choisissez dans la liste.")
            self.lst.Select(0)
            self.lst.Focus(0)
            self._set_busy(False, message)
            self.lst.SetFocus()
        else:
            message = _("Aucun résultat. Essayez un autre nom, ou une autre "
                        "source de recherche.")
            self._set_busy(False, message)
            self.txt_query.SetFocus()
        speech.speak(message)

    def _on_search_failed(self, error: str) -> None:
        if not self._vivante():
            return
        self._set_busy(False, _("La recherche a échoué."))
        wx.MessageBox(error, _("Recherche impossible"),
                      wx.OK | wx.ICON_ERROR, self)
        self.txt_query.SetFocus()

    # ------------------------------------------------------------------
    # Choix
    # ------------------------------------------------------------------

    def _on_selection(self, event) -> None:
        self.btn_choose.Enable(self.lst.GetFirstSelected() >= 0)
        event.Skip()

    def _on_choose(self, _event) -> None:
        idx = self.lst.GetFirstSelected()
        if not (0 <= idx < len(self._results)):
            return
        entry = self._results[idx]

        # Un podcast n'expose pas son adresse dans les resultats : on va la
        # chercher maintenant, pour le seul podcast retenu.
        if entry.get("url"):
            self._chosen_url = entry["url"]
            self._chosen_title = entry.get("title", "")
            self.EndModal(wx.ID_OK)
            return

        self._set_busy(True, _("Recherche de l'adresse du flux…"))

        def worker() -> None:
            try:
                url = feed_search.resolve(entry)
            except feed_search.SearchError as exc:
                wx.CallAfter(self._on_resolve_failed, str(exc))
            except Exception as exc:
                wx.CallAfter(self._on_resolve_failed, str(exc))
            else:
                wx.CallAfter(self._on_resolved, entry, url)

        threading.Thread(target=worker, daemon=True).start()

    def _on_resolved(self, entry: dict, url: str) -> None:
        if not self._vivante():
            return
        self._set_busy(False)
        self._chosen_url = url
        self._chosen_title = entry.get("title", "")
        self.EndModal(wx.ID_OK)

    def _on_resolve_failed(self, error: str) -> None:
        if not self._vivante():
            return
        self._set_busy(False, _("Adresse introuvable."))
        wx.MessageBox(error, _("Adresse introuvable"),
                      wx.OK | wx.ICON_ERROR, self)
        self.lst.SetFocus()

    # ------------------------------------------------------------------
    # Divers
    # ------------------------------------------------------------------

    def _set_busy(self, busy: bool, message: str = "") -> None:
        for widget in (self.btn_search, self.choice_source, self.txt_query):
            widget.Enable(not busy)
        self.btn_choose.Enable(not busy and self.lst.GetFirstSelected() >= 0)
        if message:
            self.lbl_status.SetLabel(message)
        if busy and message:
            speech.speak(message, interrupt=False)

    def get_url(self) -> str:
        return self._chosen_url

    def get_title(self) -> str:
        return self._chosen_title
