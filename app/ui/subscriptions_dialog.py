"""Fenetre de gestion des abonnements : chaines suivies et podcasts.

Le releve reseau se fait toujours dans un thread : resoudre un flux ou verifier
dix abonnements prend quelques secondes, et l'interface ne doit jamais se figer.
Les retours passent par `wx.CallAfter`.
"""

import threading

import wx

from app.core import speech
from app.core import subscriptions as subs
from app.core.i18n import _translate as _

# Formats proposes pour un abonnement. La chaine vide = « suivre le format par
# defaut des preferences » : l'utilisateur qui change d'avis dans les
# preferences n'a pas a reprendre chacun de ses abonnements.
FORMAT_CODES = ["", "auto", "mp4", "mp3", "m4a"]


def _format_labels() -> list[str]:
    return [
        _("Format par défaut des préférences"),
        _("Meilleure qualité automatique"),
        _("Vidéo MP4 (H.264)"),
        _("Audio MP3"),
        _("Audio M4A"),
    ]


class AddSubscriptionDialog(wx.Dialog):
    """Saisie d'une adresse a suivre : chaine, playlist, podcast, collection Arte."""

    def __init__(self, parent):
        super().__init__(parent, title=_("Suivre une chaîne ou un podcast"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._build_ui()
        self.SetMinSize((560, 300))
        self.Fit()
        self.CentreOnParent()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_url = wx.StaticText(panel, label=_("Adresse à suivre :"))
        self.txt_url = wx.TextCtrl(panel, name=_("Adresse à suivre"))
        self.txt_url.SetHint("https://www.youtube.com/@arte")

        # Chercher par le nom evite d'avoir a connaitre l'adresse — celle du
        # flux d'un podcast n'est trouvable nulle part pour qui ne lit pas le
        # code source d'une page (demande de Veronique, 2026-08-28).
        self.btn_search = wx.Button(
            panel, label=_("Rechercher une chaîne ou un podcast..."),
            name=_("Rechercher une chaîne ou un podcast"))

        lbl_help = wx.StaticText(panel, label=_(
            "Cherchez par le nom, ou collez directement l'adresse : chaîne "
            "YouTube, playlist, flux de podcast, ou collection Arte (la page "
            "d'un festival ou d'un magazine). La page d'accueil d'un podcast "
            "convient aussi : DownAccess y cherche le flux."))

        lbl_fmt = wx.StaticText(panel, label=_("Format des téléchargements :"))
        self.choice_fmt = wx.Choice(panel, choices=_format_labels(),
                                    name=_("Format des téléchargements"))
        # Preselection du format choisi dans les preferences (onglet
        # Abonnements) : qui suit dix podcasts ne veut pas le repeter dix fois.
        from app.core import settings as cfg
        defaut = cfg.load().get("subscriptions_default_format", "")
        self.choice_fmt.SetSelection(FORMAT_CODES.index(defaut)
                                     if defaut in FORMAT_CODES else 0)

        self.chk_auto = wx.CheckBox(
            panel, label=_("Télécharger automatiquement les nouveautés"),
            name=_("Télécharger automatiquement les nouveautés"))
        self.chk_auto.SetToolTip(_(
            "Sans cette option, DownAccess vous montre les nouveautés et vous "
            "choisissez ce que vous voulez."))

        self.chk_catch_up = wx.CheckBox(
            panel,
            label=_("Considérer les publications déjà en ligne comme des nouveautés"),
            name=_("Considérer les publications déjà en ligne comme des nouveautés"))
        self.chk_catch_up.SetToolTip(_(
            "Pour rattraper le passé de ce que vous découvrez. Sans cette "
            "option, DownAccess ne vous signale que ce qui sera publié à "
            "partir de maintenant."))

        btns = wx.StdDialogButtonSizer()
        self.btn_ok = wx.Button(panel, wx.ID_OK, label=_("Suivre"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        btns.AddButton(self.btn_ok)
        btns.AddButton(self.btn_cancel)
        btns.Realize()

        for widget, flag in ((lbl_url, wx.TOP), (self.txt_url, wx.TOP),
                             (self.btn_search, wx.TOP),
                             (lbl_help, wx.TOP), (lbl_fmt, wx.TOP),
                             (self.choice_fmt, wx.TOP), (self.chk_auto, wx.TOP),
                             (self.chk_catch_up, wx.TOP)):
            sizer.Add(widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | flag, 10)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(sizer)

        self.btn_search.MoveAfterInTabOrder(self.txt_url)
        self.choice_fmt.MoveAfterInTabOrder(self.btn_search)
        self.chk_auto.MoveAfterInTabOrder(self.choice_fmt)
        self.chk_catch_up.MoveAfterInTabOrder(self.chk_auto)
        self.btn_ok.MoveAfterInTabOrder(self.chk_catch_up)
        self.txt_url.SetFocus()

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.btn_search.Bind(wx.EVT_BUTTON, self._on_search)

    def _on_search(self, _event) -> None:
        """Recherche par nom : le resultat retenu remplit le champ d'adresse.

        On ne cree pas l'abonnement dans la foulee : l'utilisateur garde la
        main sur le format et le rattrapage, qui sont dans cette fenetre-ci.
        """
        from app.ui.subscription_search_dialog import SubscriptionSearchDialog

        with SubscriptionSearchDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK or not dlg.get_url():
                self.txt_url.SetFocus()
                return
            self.txt_url.SetValue(dlg.get_url())
            titre = dlg.get_title()

        # Le champ retrouve le focus avec l'adresse dedans : le lecteur d'ecran
        # annonce ce qui vient d'etre choisi, et il reste modifiable.
        self.txt_url.SetInsertionPointEnd()
        self.txt_url.SetFocus()
        if titre:
            speech.speak(_("« {title} » choisi.").format(title=titre),
                         interrupt=False)

    def _on_ok(self, _event) -> None:
        if not self.txt_url.GetValue().strip():
            wx.MessageBox(_("Indiquez l'adresse à suivre."),
                          _("Adresse manquante"), wx.OK | wx.ICON_WARNING, self)
            self.txt_url.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def get_url(self) -> str:
        return self.txt_url.GetValue().strip()

    def get_format(self) -> str:
        idx = self.choice_fmt.GetSelection()
        return FORMAT_CODES[idx] if 0 <= idx < len(FORMAT_CODES) else ""

    def get_auto_download(self) -> bool:
        return self.chk_auto.GetValue()

    def get_catch_up(self) -> bool:
        return self.chk_catch_up.GetValue()


class EditSubscriptionDialog(wx.Dialog):
    """Reglages d'un abonnement deja suivi : format et telechargement auto.

    Jusqu'ici, changer d'avis sur un abonnement demandait de ne plus le suivre
    puis de le recreer — en perdant au passage la memoire de ce qui avait deja
    ete vu (demande de Veronique, 2026-08-31).
    """

    def __init__(self, parent, sub):
        super().__init__(parent,
                         title=_("Réglages de « {title} »").format(title=sub.title),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._sub = sub
        self._build_ui()
        self.SetMinSize((560, 300))
        self.Fit()
        self.CentreOnParent()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_nom = wx.StaticText(panel, label=_("Abonnement : {title} ({kind})")
                                .format(title=self._sub.title,
                                        kind=self._sub.kind_label()))

        lbl_fmt = wx.StaticText(panel, label=_("Format des téléchargements :"))
        self.choice_fmt = wx.Choice(panel, choices=_format_labels(),
                                    name=_("Format des téléchargements"))
        self.choice_fmt.SetSelection(
            FORMAT_CODES.index(self._sub.format_spec)
            if self._sub.format_spec in FORMAT_CODES else 0)

        self.chk_auto = wx.CheckBox(
            panel, label=_("Télécharger automatiquement les nouveautés"),
            name=_("Télécharger automatiquement les nouveautés"))
        self.chk_auto.SetValue(self._sub.auto_download)
        self.chk_auto.SetToolTip(_(
            "Sans cette option, DownAccess vous montre les nouveautés et vous "
            "choisissez ce que vous voulez."))

        # Le rattrapage n'etait proposable qu'a la creation : sans cela, les
        # publications anterieures a l'abonnement restaient invisibles a
        # jamais, aucune verification ulterieure ne pouvant les faire
        # reapparaitre. On le rend donc rejouable ici.
        self.chk_catch_up = wx.CheckBox(
            panel,
            label=_("Me proposer aussi les publications déjà en ligne"),
            name=_("Me proposer aussi les publications déjà en ligne"))
        self.chk_catch_up.SetToolTip(_(
            "Pour rattraper le passé d'une chaîne ou d'un podcast que vous "
            "suivez déjà. Tout ce qui est en ligne vous sera reproposé à la "
            "prochaine vérification."))

        btns = wx.StdDialogButtonSizer()
        self.btn_ok = wx.Button(panel, wx.ID_OK, label=_("Enregistrer"))
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL, label=_("Annuler"))
        btns.AddButton(self.btn_ok)
        btns.AddButton(self.btn_cancel)
        btns.Realize()

        for widget in (lbl_nom, lbl_fmt, self.choice_fmt, self.chk_auto,
                       self.chk_catch_up):
            sizer.Add(widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(sizer)

        self.chk_auto.MoveAfterInTabOrder(self.choice_fmt)
        self.chk_catch_up.MoveAfterInTabOrder(self.chk_auto)
        self.btn_ok.MoveAfterInTabOrder(self.chk_catch_up)
        self.choice_fmt.SetFocus()

    def get_format(self) -> str:
        idx = self.choice_fmt.GetSelection()
        return FORMAT_CODES[idx] if 0 <= idx < len(FORMAT_CODES) else ""

    def get_auto_download(self) -> bool:
        return self.chk_auto.GetValue()

    def get_catch_up(self) -> bool:
        return self.chk_catch_up.GetValue()


class SubscriptionsDialog(wx.Dialog):
    """Liste des abonnements : ajouter, retirer, verifier, voir les nouveautes.

    Le dialogue travaille sur sa propre copie de la liste et l'enregistre a
    chaque changement : fermer la fenetre ne doit jamais perdre un abonnement
    qu'on vient d'ajouter.
    """

    def __init__(self, parent, on_new_items=None, pending=None):
        super().__init__(parent, title=_("Abonnements"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._subs = subs.load()
        self._on_new_items = on_new_items
        # Nouveautes deja relevees au demarrage : on les propose sans refaire
        # une passe reseau que l'utilisateur a deja payee.
        self._pending = pending or {}
        self._build_ui()
        self._bind_events()
        self.SetMinSize((700, 420))
        self.Fit()
        self.CentreOnParent()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lbl = wx.StaticText(panel, label=self._heading())

        self.lst = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
            name=_("Abonnements"),
        )
        self.lst.InsertColumn(0, _("Nom"), width=280)
        self.lst.InsertColumn(1, _("Type"), width=90)
        self.lst.InsertColumn(2, _("Format"), width=110)
        self.lst.InsertColumn(3, _("Automatique"), width=100)
        self.lst.InsertColumn(4, _("Dernière vérification"), width=140)
        self._fill_list()

        self.btn_add    = wx.Button(panel, label=_("Suivre une chaîne..."))
        self.btn_edit   = wx.Button(panel, label=_("Modifier les réglages..."))
        self.btn_remove = wx.Button(panel, label=_("Ne plus suivre"))
        self.btn_check  = wx.Button(panel, label=_("Vérifier maintenant"))
        pending_count = sum(len(v) for v in self._pending.values())
        self.btn_new = wx.Button(panel, label=_("Voir les {n} nouveautés").format(
            n=pending_count) if pending_count else _("Voir les nouveautés"))
        self.btn_new.Enable(bool(pending_count))
        self.btn_close  = wx.Button(panel, wx.ID_CANCEL, label=_("Fermer"))

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.btn_add, 0, wx.RIGHT, 6)
        row.Add(self.btn_edit, 0, wx.RIGHT, 6)
        row.Add(self.btn_remove, 0, wx.RIGHT, 6)
        row.Add(self.btn_check, 0, wx.RIGHT, 6)
        row.Add(self.btn_new, 0)
        row.AddStretchSpacer()
        row.Add(self.btn_close, 0)

        sizer.Add(self.lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.lst, 1, wx.EXPAND | wx.ALL, 12)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(sizer)

        self.btn_add.MoveAfterInTabOrder(self.lst)
        self.btn_edit.MoveAfterInTabOrder(self.btn_add)
        self.btn_remove.MoveAfterInTabOrder(self.btn_edit)
        self.btn_check.MoveAfterInTabOrder(self.btn_remove)
        self.btn_new.MoveAfterInTabOrder(self.btn_check)
        self.btn_close.MoveAfterInTabOrder(self.btn_new)

        if self._subs:
            self.lst.Select(0)
            self.lst.Focus(0)
        self.lst.SetFocus()

    def _bind_events(self) -> None:
        self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        self.btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        self.btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
        # Entree ou double-clic sur une ligne ouvre ses reglages : c'est le
        # geste attendu sur une liste, et il evite d'aller chercher le bouton.
        self.lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)
        self.btn_check.Bind(wx.EVT_BUTTON, self._on_check)
        self.btn_new.Bind(wx.EVT_BUTTON, self._on_show_pending)

    # ------------------------------------------------------------------

    def _heading(self) -> str:
        if not self._subs:
            return _("Vous ne suivez encore aucune chaîne ni podcast.")
        return _("{n} abonnements :").format(n=len(self._subs))

    def _fill_list(self) -> None:
        self.lst.DeleteAllItems()
        labels = _format_labels()
        for i, sub in enumerate(self._subs):
            self.lst.InsertItem(i, sub.title)
            self.lst.SetItem(i, 1, sub.kind_label())
            idx = (FORMAT_CODES.index(sub.format_spec)
                   if sub.format_spec in FORMAT_CODES else 0)
            self.lst.SetItem(i, 2, labels[idx])
            self.lst.SetItem(i, 3, _("oui") if sub.auto_download else _("non"))
            self.lst.SetItem(i, 4, sub.last_checked_label())
        self.lbl.SetLabel(self._heading())

    def _selected(self):
        idx = self.lst.GetFirstSelected()
        return (idx, self._subs[idx]) if 0 <= idx < len(self._subs) else (-1, None)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        for btn in (self.btn_add, self.btn_edit, self.btn_remove,
                    self.btn_check):
            btn.Enable(not busy)
        self.lbl.SetLabel(message if message else self._heading())

    # ------------------------------------------------------------------

    def _on_add(self, _event) -> None:
        with AddSubscriptionDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            url = dlg.get_url()
            fmt = dlg.get_format()
            auto = dlg.get_auto_download()
            catch_up = dlg.get_catch_up()

        self._set_busy(True, _("Recherche du flux..."))

        def worker() -> None:
            try:
                sub = subs.create(url, format_spec=fmt, auto_download=auto,
                                  catch_up=catch_up)
                # Compte reel de ce que l'abonnement va proposer : sert a
                # chiffrer l'avertissement avant un telechargement massif.
                en_attente = len(subs.check(sub)) if catch_up else 0
            except subs.FeedError as exc:
                wx.CallAfter(self._on_add_failed, str(exc))
            except Exception as exc:
                wx.CallAfter(self._on_add_failed, str(exc))
            else:
                wx.CallAfter(self._on_add_done, sub, en_attente)

        threading.Thread(target=worker, daemon=True).start()

    def _on_add_done(self, sub, en_attente: int = 0) -> None:
        self._set_busy(False)

        # Deja suivi : sans ce garde-fou, chaque nouveaute serait proposee (ou
        # telechargee) en double. Le risque a augmente avec la recherche par
        # nom, qui rend l'ajout assez facile pour qu'on le refasse sans y
        # penser. On compare les flux, pas les adresses saisies : la meme
        # chaine s'ecrit @arte, /channel/UC..., ou /c/arte.
        deja = next((a for a in self._subs if a.feed_url == sub.feed_url), None)
        if deja is not None:
            wx.MessageBox(
                _("Vous suivez déjà « {title} ».\n\nRien n'a "
                  "été ajouté : vos réglages pour cet abonnement sont "
                  "inchangés.").format(title=deja.title),
                _("Abonnement déjà suivi"), wx.OK | wx.ICON_INFORMATION, self)
            index = self._subs.index(deja)
            self.lst.Select(index)
            self.lst.Focus(index)
            self.lst.SetFocus()
            return
        # Rattrapage + telechargement automatique : tout le catalogue partirait
        # en file sans que rien ne soit demande. On chiffre avant d'engager.
        if sub.auto_download and en_attente > 1:
            reponse = wx.MessageBox(
                _("« {title} » compte déjà {n} publications en ligne, et vous "
                  "avez demandé le téléchargement automatique : elles partiront "
                  "toutes en téléchargement, ce qui peut occuper beaucoup de "
                  "place.\n\nTout télécharger maintenant ?\n\nSi vous répondez "
                  "Non, l'abonnement est quand même créé : les {n} publications "
                  "vous seront proposées et vous choisirez.")
                .format(title=sub.title, n=en_attente),
                _("Beaucoup de publications à télécharger"),
                wx.YES_NO | wx.ICON_QUESTION, self)
            if reponse != wx.YES:
                sub.auto_download = False

        self._subs.append(sub)
        subs.save(self._subs)
        self._fill_list()
        self.lst.Select(len(self._subs) - 1)
        self.lst.Focus(len(self._subs) - 1)
        if en_attente:
            corps = _("Vous suivez maintenant « {title} ».\n\n{n} publications "
                      "déjà en ligne vous attendent : ouvrez « Voir les "
                      "nouveautés » pour choisir.").format(title=sub.title,
                                                           n=en_attente)
        else:
            corps = _("Vous suivez maintenant « {title} ».\n\nDownAccess vous "
                      "signalera ce qui sera publié à partir de maintenant."
                      ).format(title=sub.title)
        wx.MessageBox(corps, _("Abonnement ajouté"),
                      wx.OK | wx.ICON_INFORMATION, self)
        self.lst.SetFocus()

    def _on_add_failed(self, message: str) -> None:
        self._set_busy(False)
        wx.MessageBox(
            _("Impossible de suivre cette adresse.\n\n{error}\n\nVérifiez "
              "l'adresse, ou essayez celle de la page d'accueil de la chaîne.")
            .format(error=message[:300]),
            _("Flux introuvable"), wx.OK | wx.ICON_WARNING, self)
        self.lst.SetFocus()

    def _on_edit(self, _event) -> None:
        """Reglages d'un abonnement existant.

        Le rattrapage est le seul changement qui ne se voit pas dans la liste :
        on enchaine donc sur une verification pour que les publications
        reproposees arrivent tout de suite, plutot que de laisser
        l'utilisateur deviner qu'il lui reste un bouton a presser.
        """
        idx, sub = self._selected()
        if sub is None:
            wx.MessageBox(_("Sélectionnez d'abord un abonnement."),
                          _("Aucune sélection"), wx.OK | wx.ICON_INFORMATION, self)
            self.lst.SetFocus()
            return

        with EditSubscriptionDialog(self, sub) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                self.lst.SetFocus()
                return
            fmt = dlg.get_format()
            auto = dlg.get_auto_download()
            catch_up = dlg.get_catch_up()

        # Rattrapage + telechargement automatique : tout le catalogue partirait
        # en file sans que rien ne soit demande. On previent avant d'engager.
        if catch_up and auto:
            reponse = wx.MessageBox(
                _("Vous avez demandé le rattrapage des publications déjà en "
                  "ligne, et « {title} » est en téléchargement automatique : "
                  "tout son catalogue partira en téléchargement, ce qui peut "
                  "occuper beaucoup de place.\n\nTout télécharger maintenant ?"
                  "\n\nSi vous répondez Non, le rattrapage a quand même lieu : "
                  "les publications vous seront proposées et vous choisirez.")
                .format(title=sub.title),
                _("Beaucoup de publications à télécharger"),
                wx.YES_NO | wx.ICON_QUESTION, self)
            if reponse != wx.YES:
                auto = False

        sub.format_spec = fmt
        sub.auto_download = auto
        if catch_up:
            # Oublier ce qui a ete vu suffit : la prochaine verification
            # considere tout le flux comme nouveau.
            sub.seen_ids = []
        subs.save(self._subs)
        self._fill_list()
        self.lst.Select(idx)
        self.lst.Focus(idx)
        self.lst.SetFocus()

        if catch_up:
            self._on_check(None)

    def _on_remove(self, _event) -> None:
        idx, sub = self._selected()
        if sub is None:
            wx.MessageBox(_("Sélectionnez d'abord un abonnement."),
                          _("Aucune sélection"), wx.OK | wx.ICON_INFORMATION, self)
            self.lst.SetFocus()
            return
        if wx.MessageBox(
                _("Ne plus suivre « {title} » ?").format(title=sub.title),
                _("Confirmer"), wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            self.lst.SetFocus()
            return
        del self._subs[idx]
        subs.save(self._subs)
        self._fill_list()
        if self._subs:
            new_idx = min(idx, len(self._subs) - 1)
            self.lst.Select(new_idx)
            self.lst.Focus(new_idx)
        self.lst.SetFocus()

    def _on_show_pending(self, _event) -> None:
        """Passe la main a la fenetre des nouveautes deja relevees."""
        if not self._pending or not self._on_new_items:
            return
        pending, self._pending = self._pending, {}
        self.EndModal(wx.ID_OK)
        self._on_new_items(pending, self._subs)

    def _on_check(self, _event) -> None:
        if not self._subs:
            wx.MessageBox(_("Vous ne suivez encore aucune chaîne ni podcast."),
                          _("Aucun abonnement"), wx.OK | wx.ICON_INFORMATION, self)
            self.lst.SetFocus()
            return
        self._set_busy(True, _("Vérification en cours..."))

        def worker() -> None:
            fresh, errors = subs.check_all(self._subs)
            wx.CallAfter(self._on_check_done, fresh, errors)

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self, fresh: dict, errors: list) -> None:
        subs.save(self._subs)
        self._set_busy(False)
        self._fill_list()
        total = sum(len(v) for v in fresh.values())
        if total and self._on_new_items:
            # La fenetre des nouveautes prend le relais : on ferme celle-ci
            # pour ne pas empiler deux fenetres modales.
            self.EndModal(wx.ID_OK)
            self._on_new_items(fresh, self._subs)
            return
        if errors:
            wx.MessageBox(
                _("Aucune nouveauté.\n\nCertains abonnements n'ont pas pu être "
                  "vérifiés :\n{errors}").format(errors="\n".join(errors[:5])),
                _("Vérification terminée"), wx.OK | wx.ICON_INFORMATION, self)
        else:
            wx.MessageBox(_("Aucune nouveauté pour l'instant."),
                          _("Vérification terminée"), wx.OK | wx.ICON_INFORMATION, self)
        self.lst.SetFocus()
