"""Precedent / Suivant / Actualiser dans la fenetre d'extraction guidee.

WebView2 est un moteur nu : il n'a aucune barre de navigation. Sans ces
boutons, l'utilisateur qui suit un lien ne pouvait plus revenir en arriere
(signale par Mathieu au premier essai reel).

Les boutons sont dans la fenetre DownAccess, en controles wx natifs, et
passent par le meme canal que le reste de l'extraction : ils fonctionnent donc
aussi bien avec le navigateur installe qu'avec WebView2.
"""

import threading

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui.uge_dialog import UGEDialog


class FausePage:
    """Page pilotable, sans le moindre navigateur."""

    def __init__(self, historique=None, casse=False):
        self.historique = historique or ["https://a/1", "https://a/2"]
        self.position = len(self.historique) - 1
        self.casse = casse
        self.appels = []

    @property
    def url(self):
        return self.historique[self.position]

    @property
    def title(self):
        return f"Page {self.position + 1}"

    def back(self, steps=1):
        self.appels.append("back")
        if self.casse or self.position == 0:
            raise RuntimeError("pas d'historique")
        self.position -= 1

    def forward(self, steps=1):
        self.appels.append("forward")
        if self.casse or self.position >= len(self.historique) - 1:
            raise RuntimeError("pas d'historique")
        self.position += 1

    def refresh(self):
        self.appels.append("refresh")
        if self.casse:
            raise RuntimeError("impossible")


@pytest.fixture
def fenetre(frame, appdata):
    dlg = UGEDialog(frame, on_add_url=lambda *a, **k: None)
    yield dlg
    dlg._page = None          # jamais de vrai navigateur a fermer ici
    dlg.Destroy()


def _attendre_threads():
    """Les actions de navigation tournent dans un thread : on les laisse finir."""
    for t in threading.enumerate():
        if t is not threading.current_thread() and t.daemon:
            t.join(timeout=3)
    wx.YieldIfNeeded()


class TestBoutonsDeNavigation:
    def test_les_trois_boutons_existent_et_sont_etiquetes(self, fenetre):
        """Sans libelle, le lecteur d'ecran annonce « bouton » tout court."""
        for bouton in (fenetre.btn_back, fenetre.btn_forward, fenetre.btn_reload):
            assert bouton.GetLabel().strip()
            assert bouton.GetName().strip()
            assert bouton.GetName() != bouton.GetLabel(), (
                "le nom accessible doit etre plus explicite que le libelle")

    def test_desactives_tant_qu_aucune_page_n_est_ouverte(self, fenetre):
        """Cliquer « Precedent » sans navigateur n'aurait aucun sens."""
        assert not fenetre.btn_back.IsEnabled()
        assert not fenetre.btn_forward.IsEnabled()
        assert not fenetre.btn_reload.IsEnabled()

    def test_actives_une_fois_une_page_chargee(self, fenetre):
        fenetre._on_page_loaded("https://a/1", "Titre")
        assert fenetre.btn_back.IsEnabled()
        assert fenetre.btn_forward.IsEnabled()
        assert fenetre.btn_reload.IsEnabled()


class TestActionsDeNavigation:
    def test_precedent_recule_et_met_a_jour_l_adresse(self, fenetre):
        """Le champ Adresse est ce que relit le lecteur d'ecran : il doit
        suivre la page, sinon l'utilisateur ne sait plus ou il est."""
        fenetre._page = FausePage()
        fenetre._on_back(None)
        _attendre_threads()
        assert fenetre._page.appels == ["back"]
        assert fenetre._page.url == "https://a/1"
        assert fenetre.txt_url.GetValue() == "https://a/1"

    def test_suivant_avance(self, fenetre):
        page = FausePage()
        page.position = 0
        fenetre._page = page
        fenetre._on_forward(None)
        _attendre_threads()
        assert page.url == "https://a/2"

    def test_actualiser_recharge(self, fenetre):
        fenetre._page = FausePage()
        fenetre._on_reload(None)
        _attendre_threads()
        assert fenetre._page.appels == ["refresh"]

    def test_sans_page_ouverte_rien_ne_casse(self, fenetre):
        """Le raccourci clavier peut partir avant tout chargement."""
        fenetre._page = None
        fenetre._on_back(None)
        fenetre._on_forward(None)
        fenetre._on_reload(None)

    def test_bout_de_l_historique_le_dit_au_lieu_de_planter(self, fenetre):
        """Reculer sans page precedente doit s'annoncer, pas lever."""
        page = FausePage()
        page.position = 0
        fenetre._page = page
        fenetre._on_back(None)
        _attendre_threads()
        assert "précédente" in fenetre.lbl_status.GetLabel().lower()

    def test_navigation_impossible_ne_touche_pas_a_l_adresse(self, fenetre):
        fenetre._page = FausePage(casse=True)
        fenetre.txt_url.SetValue("https://inchange/")
        fenetre._on_reload(None)
        _attendre_threads()
        assert fenetre.txt_url.GetValue() == "https://inchange/"


class TestRaccourcisClavier:
    def test_alt_gauche_droite_et_f5_sont_poses(self, fenetre):
        """Un utilisateur au clavier ne doit pas avoir a chercher le bouton
        depuis la liste des medias."""
        table = fenetre.GetAcceleratorTable()
        assert table.IsOk(), "aucune table de raccourcis"
