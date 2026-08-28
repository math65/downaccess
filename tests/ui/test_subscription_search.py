"""La fenetre de recherche d'une source a suivre.

Ce qui est verrouille ici : l'accessibilite structurelle (tout est etiquete, le
focus arrive sur la saisie, l'ordre de tabulation est pose), et l'aiguillage —
un resultat choisi doit remplir le champ d'adresse de la fenetre d'abonnement,
sans creer l'abonnement dans le dos de l'utilisateur.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core import feed_search as fs
from app.ui.subscription_search_dialog import SubscriptionSearchDialog
from app.ui.subscriptions_dialog import AddSubscriptionDialog

CHAINE = {
    "title": "ARTE", "author": "ARTE", "detail": "5 020 000 abonnés",
    "url": "https://www.youtube.com/channel/UCwI-JbGNsojunnHbFAc0M4Q",
    "source": fs.SOURCE_YOUTUBE,
}
PODCAST = {
    "title": "Affaires sensibles", "author": "France Inter",
    "detail": "138 épisodes", "url": "", "source": fs.SOURCE_PODCAST,
    "_apple_id": 912451024, "_apple_page": "https://podcasts.apple.com/x",
}


class FilSynchrone:
    """Execute le travail « de fond » tout de suite : un test ne doit pas
    dependre de l'ordonnancement des fils."""

    def __init__(self, target=None, daemon=None, **_kw):
        self._target = target

    def start(self):
        self._target()


@pytest.fixture
def sans_fils(monkeypatch):
    from app.ui import subscription_search_dialog as mod

    monkeypatch.setattr(mod.threading, "Thread", FilSynchrone)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **kw: fn(*a, **kw))


# Noms que wx attribue tout seul : ils n'apprennent rien au lecteur d'ecran.
NOMS_PAR_DEFAUT = {"", "control", "button", "listCtrl", "text", "choice",
                   "staticText", "panel"}


def muets(parent):
    """Controles interactifs qu'un lecteur d'ecran ne saurait pas nommer.

    Un bouton se lit par son libelle ; les autres controles, par leur nom.
    D'ou les deux exigences, verifiees separement.
    """
    trouves = []
    for enfant in parent.GetChildren():
        if isinstance(enfant, wx.Button):
            if not enfant.GetLabel().strip():
                trouves.append(enfant)
        elif isinstance(enfant, wx.TextCtrl | wx.Choice | wx.ListCtrl):
            if enfant.GetName() in NOMS_PAR_DEFAUT:
                trouves.append(enfant)
        trouves.extend(muets(enfant))
    return trouves


class TestAccessibilite:
    def test_focus_sur_la_saisie(self, frame):
        dlg = SubscriptionSearchDialog(frame)
        assert dlg.FindFocus() is dlg.txt_query
        dlg.Destroy()

    def test_tout_est_etiquete(self, frame):
        dlg = SubscriptionSearchDialog(frame)
        assert muets(dlg) == []
        dlg.Destroy()

    def test_choisir_reste_inactif_sans_selection(self, frame):
        """Un bouton actif qui ne fait rien est un piege au lecteur d'ecran."""
        dlg = SubscriptionSearchDialog(frame)
        assert not dlg.btn_choose.IsEnabled()
        dlg.Destroy()

    def test_les_trois_sources_sont_proposees(self, frame):
        dlg = SubscriptionSearchDialog(frame)
        assert dlg.choice_source.GetCount() == len(fs.SOURCE_CODES)
        assert dlg.choice_source.GetSelection() == 0
        dlg.Destroy()

    def test_un_etat_lisible_des_le_depart(self, frame):
        """La zone d'etat ne doit jamais etre vide : elle est le seul endroit
        ou relire ce qui s'est passe."""
        dlg = SubscriptionSearchDialog(frame)
        assert dlg.lbl_status.GetLabel().strip()
        dlg.Destroy()


class TestRecherche:
    def test_les_resultats_remplissent_la_liste(self, frame, sans_fils, monkeypatch):
        monkeypatch.setattr(fs, "search", lambda *a, **kw: [CHAINE, PODCAST])
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("arte")
        dlg._on_search(None)
        assert dlg.lst.GetItemCount() == 2
        assert dlg.lst.GetItemText(0, 0) == "ARTE"
        assert dlg.lst.GetItemText(0, 1) == "ARTE"
        assert "5 020 000" in dlg.lst.GetItemText(0, 2)
        dlg.Destroy()

    def test_la_recherche_porte_sur_la_source_choisie(self, frame, sans_fils,
                                                      monkeypatch):
        vu = {}

        def faux_search(source, query, *a, **kw):
            vu["source"] = source
            vu["query"] = query
            return []

        monkeypatch.setattr(fs, "search", faux_search)
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("  affaires sensibles  ")
        dlg.choice_source.SetSelection(fs.SOURCE_CODES.index(fs.SOURCE_PODCAST))
        dlg._on_search(None)
        assert vu == {"source": fs.SOURCE_PODCAST, "query": "affaires sensibles"}
        dlg.Destroy()

    def test_zero_resultat_le_dit_et_rend_la_main(self, frame, sans_fils,
                                                  monkeypatch):
        monkeypatch.setattr(fs, "search", lambda *a, **kw: [])
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("zzzz")
        dlg._on_search(None)
        assert dlg.lst.GetItemCount() == 0
        assert "Aucun" in dlg.lbl_status.GetLabel()
        assert not dlg.btn_choose.IsEnabled()
        dlg.Destroy()

    def test_une_nouvelle_recherche_efface_l_ancienne(self, frame, sans_fils,
                                                      monkeypatch):
        monkeypatch.setattr(fs, "search", lambda *a, **kw: [CHAINE, PODCAST])
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("arte")
        dlg._on_search(None)
        monkeypatch.setattr(fs, "search", lambda *a, **kw: [CHAINE])
        dlg._on_search(None)
        assert dlg.lst.GetItemCount() == 1
        dlg.Destroy()

    def test_une_panne_ne_laisse_pas_la_fenetre_bloquee(self, frame, sans_fils,
                                                        monkeypatch):
        """Apres un echec, tout doit redevenir utilisable : sans cela la
        fenetre est morte et il faut la fermer."""
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **kw: wx.OK)
        monkeypatch.setattr(fs, "search", lambda *a, **kw: (_ for _ in ()).throw(
            fs.SearchError("service injoignable")))
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("arte")
        dlg._on_search(None)
        assert dlg.btn_search.IsEnabled()
        assert dlg.txt_query.IsEnabled()
        dlg.Destroy()

    def test_recherche_vide_refusee_sans_appel_reseau(self, frame, monkeypatch):
        appels = []
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **kw: appels.append("boite"))
        monkeypatch.setattr(fs, "search", lambda *a, **kw: appels.append("reseau"))
        dlg = SubscriptionSearchDialog(frame)
        dlg.txt_query.SetValue("   ")
        dlg._on_search(None)
        assert appels == ["boite"]
        dlg.Destroy()


class TestChoix:
    def _prepare(self, frame, monkeypatch, resultats):
        """La fenetre n'est pas modale dans un test : on note le code de sortie
        au lieu de le faire poser par wx."""
        monkeypatch.setattr(fs, "search", lambda *a, **kw: resultats)
        dlg = SubscriptionSearchDialog(frame)
        dlg.sorties = []
        monkeypatch.setattr(dlg, "EndModal", dlg.sorties.append)
        dlg.txt_query.SetValue("x")
        dlg._on_search(None)
        return dlg

    def test_une_chaine_est_retenue_sans_appel_reseau(self, frame, sans_fils,
                                                      monkeypatch):
        monkeypatch.setattr(fs, "resolve", lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("l'adresse est deja connue")))
        dlg = self._prepare(frame, monkeypatch, [CHAINE])
        dlg.lst.Select(0)
        dlg._on_choose(None)
        assert dlg.get_url() == CHAINE["url"]
        assert dlg.get_title() == "ARTE"
        assert dlg.sorties == [wx.ID_OK], "la fenetre se ferme sur un choix"
        dlg.Destroy()

    def test_un_podcast_fait_resoudre_son_flux(self, frame, sans_fils, monkeypatch):
        monkeypatch.setattr(fs, "resolve",
                            lambda entry: "https://radiofrance/rss_13940.xml")
        dlg = self._prepare(frame, monkeypatch, [PODCAST])
        dlg.lst.Select(0)
        dlg._on_choose(None)
        assert dlg.get_url() == "https://radiofrance/rss_13940.xml"
        assert dlg.sorties == [wx.ID_OK]
        dlg.Destroy()

    def test_un_flux_introuvable_ne_ferme_pas_la_fenetre(self, frame, sans_fils,
                                                         monkeypatch):
        boites = []
        monkeypatch.setattr(wx, "MessageBox",
                            lambda *a, **kw: boites.append(a[0]))
        monkeypatch.setattr(fs, "resolve", lambda entry: (_ for _ in ()).throw(
            fs.SearchError("adresse introuvable")))
        dlg = self._prepare(frame, monkeypatch, [PODCAST])
        dlg.lst.Select(0)
        dlg._on_choose(None)
        assert dlg.get_url() == "", "rien ne doit etre retenu"
        assert dlg.sorties == [], "la fenetre reste ouverte pour reessayer"
        assert boites and "introuvable" in boites[0]
        dlg.Destroy()

    def test_sans_selection_rien_ne_se_passe(self, frame, sans_fils, monkeypatch):
        dlg = self._prepare(frame, monkeypatch, [])
        dlg._on_choose(None)
        assert dlg.get_url() == ""
        dlg.Destroy()


class TestFenetreAbonnement:
    """Le raccord entre la recherche et la fenetre « Suivre une chaine »."""

    def test_le_bouton_de_recherche_existe_et_parle(self, frame):
        dlg = AddSubscriptionDialog(frame)
        assert dlg.btn_search.GetLabel() and dlg.btn_search.GetName()
        dlg.Destroy()

    def test_le_focus_reste_sur_l_adresse(self, frame):
        """Regle du projet : le focus arrive sur le contenu, pas sur un bouton."""
        dlg = AddSubscriptionDialog(frame)
        assert dlg.FindFocus() is dlg.txt_url
        dlg.Destroy()

    def test_le_resultat_choisi_remplit_le_champ(self, frame, monkeypatch):
        from app.ui import subscription_search_dialog as mod

        class FauxDialogue:
            def __init__(self, _parent):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def ShowModal(self):
                return wx.ID_OK

            def get_url(self):
                return "https://www.youtube.com/feeds/videos.xml?channel_id=UC42"

            def get_title(self):
                return "ARTE"

        monkeypatch.setattr(mod, "SubscriptionSearchDialog", FauxDialogue)
        dlg = AddSubscriptionDialog(frame)
        dlg._on_search(None)
        assert dlg.get_url().endswith("channel_id=UC42")
        dlg.Destroy()

    def test_une_recherche_annulee_ne_touche_a_rien(self, frame, monkeypatch):
        from app.ui import subscription_search_dialog as mod

        class FauxAnnule:
            def __init__(self, _parent):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def ShowModal(self):
                return wx.ID_CANCEL

            def get_url(self):
                return ""

            def get_title(self):
                return ""

        monkeypatch.setattr(mod, "SubscriptionSearchDialog", FauxAnnule)
        dlg = AddSubscriptionDialog(frame)
        dlg.txt_url.SetValue("https://deja-saisi.test/flux.xml")
        dlg._on_search(None)
        assert dlg.get_url() == "https://deja-saisi.test/flux.xml"
        dlg.Destroy()

    def test_le_format_et_le_rattrapage_restent_a_l_utilisateur(self, frame,
                                                                monkeypatch):
        """Choisir dans la recherche ne doit pas creer l'abonnement : le format
        et le rattrapage se decident dans cette fenetre-ci."""
        from app.ui import subscription_search_dialog as mod

        class FauxDialogue:
            def __init__(self, _parent):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def ShowModal(self):
                return wx.ID_OK

            def get_url(self):
                return "https://exemple.test/flux.xml"

            def get_title(self):
                return "Un podcast"

        monkeypatch.setattr(mod, "SubscriptionSearchDialog", FauxDialogue)
        dlg = AddSubscriptionDialog(frame)
        sorties = []
        monkeypatch.setattr(dlg, "EndModal", sorties.append)
        dlg._on_search(None)
        assert sorties == [], "la fenetre d'abonnement reste ouverte"
        assert dlg.get_url() == "https://exemple.test/flux.xml"
        assert dlg.get_auto_download() is False
        assert dlg.get_catch_up() is False
        dlg.Destroy()


class TestFenetreFermeePendantLaRecherche:
    """Une recherche lancee ne s'arrete pas parce qu'on ferme la fenetre.

    Son resultat revient par `wx.CallAfter` sur un objet C++ deja detruit :
    sans garde-fou, l'application tombe — et elle tombe d'autant plus
    facilement que la recherche prend plusieurs secondes, largement de quoi
    changer d'avis et fermer.
    """

    def test_un_resultat_tardif_ne_touche_pas_a_la_fenetre_detruite(self, frame):
        dlg = SubscriptionSearchDialog(frame)
        dlg.Destroy()
        wx.SafeYield()
        # Le thread revient maintenant : cet appel ne doit rien tenter.
        dlg._on_search_done([CHAINE])

    def test_un_echec_tardif_est_ignore_de_meme(self, frame, monkeypatch):
        boites = []
        monkeypatch.setattr(wx, "MessageBox", lambda *a, **kw: boites.append(a))
        dlg = SubscriptionSearchDialog(frame)
        dlg.Destroy()
        wx.SafeYield()
        dlg._on_search_failed("panne")
        assert boites == [], "aucune boite ne doit surgir apres la fermeture"

    def test_une_adresse_resolue_trop_tard_est_ignoree(self, frame):
        dlg = SubscriptionSearchDialog(frame)
        dlg.Destroy()
        wx.SafeYield()
        dlg._on_resolved(PODCAST, "https://exemple.test/flux.xml")

    def test_la_fenetre_vivante_traite_normalement(self, frame, sans_fils):
        """Contre-epreuve : le garde-fou ne doit pas tout bloquer."""
        dlg = SubscriptionSearchDialog(frame)
        dlg._on_search_done([CHAINE])
        assert dlg.lst.GetItemCount() == 1
        dlg.Destroy()


def abonnement(sub_id="s1", titre="ARTE",
               feed="https://www.youtube.com/feeds/videos.xml?channel_id=UC42"):
    from app.core.subscriptions import Subscription
    return Subscription(sub_id=sub_id, title=titre,
                        url="https://www.youtube.com/@arte", feed_url=feed,
                        kind="youtube")


class FausseListe:
    def __init__(self):
        self.selection = None
        self.focus = None

    def Select(self, index):
        self.selection = index

    def Focus(self, index):
        self.focus = index

    def SetFocus(self):
        pass


class FausseFenetreAbonnements:
    """La fenetre des abonnements reduite a ce que `_on_add_done` utilise."""

    def __init__(self, existants):
        self._subs = list(existants)
        self.lst = FausseListe()
        self.remplissages = 0

    def _set_busy(self, *_a, **_kw):
        pass

    def _fill_list(self):
        self.remplissages += 1


class TestDoublon:
    """S'abonner deux fois a la meme chose doublerait les nouveautes — et les
    telechargements, quand l'abonnement est automatique. La recherche par nom
    rend l'ajout assez facile pour qu'on le refasse sans y penser."""

    def _ajouter(self, monkeypatch, existants, nouveau):
        from app.core import subscriptions as subs_mod
        from app.ui import subscriptions_dialog as mod

        boites = []
        monkeypatch.setattr(mod.wx, "MessageBox",
                            lambda *a, **kw: boites.append(a[1]) or wx.OK)
        monkeypatch.setattr(subs_mod, "save", lambda *_a: None)
        faux = FausseFenetreAbonnements(existants)
        mod.SubscriptionsDialog._on_add_done(faux, nouveau, 0)
        return faux, boites

    def test_le_meme_flux_n_est_pas_ajoute_deux_fois(self, monkeypatch):
        faux, boites = self._ajouter(
            monkeypatch, [abonnement()],
            abonnement(sub_id="s2", titre="ARTE (copie)"))
        assert len(faux._subs) == 1
        assert boites and "déjà" in boites[0]

    def test_l_abonnement_existant_est_montre(self, monkeypatch):
        """Plutot que de laisser croire a un echec : le lecteur d'ecran doit
        atterrir sur la ligne concernee."""
        faux, _boites = self._ajouter(
            monkeypatch, [abonnement(sub_id="a"), abonnement(sub_id="b",
                                                             feed="https://autre/x")],
            abonnement(sub_id="c"))
        assert faux.lst.selection == 0 and faux.lst.focus == 0

    def test_une_autre_chaine_s_ajoute_normalement(self, monkeypatch):
        faux, boites = self._ajouter(
            monkeypatch, [abonnement()],
            abonnement(sub_id="s2", titre="France Inter",
                       feed="https://radiofrance/rss_13940.xml"))
        assert len(faux._subs) == 2
        assert faux.remplissages == 1
        assert boites and "ajouté" in boites[0]

    def test_deux_ecritures_de_la_meme_chaine_sont_le_meme_flux(self, monkeypatch):
        """@arte et /channel/UC42 donnent le meme flux Atom : c'est lui qui
        compte, pas l'adresse saisie."""
        existant = abonnement()
        existant.url = "https://www.youtube.com/@arte"
        nouveau = abonnement(sub_id="s2")
        nouveau.url = "https://www.youtube.com/channel/UC42"
        faux, _boites = self._ajouter(monkeypatch, [existant], nouveau)
        assert len(faux._subs) == 1
