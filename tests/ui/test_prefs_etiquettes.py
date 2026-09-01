"""Chaque controle des Preferences a-t-il son etiquette juste avant lui ?

Regle a11y non negociable du projet : un `wx.Choice`, un `wx.TextCtrl` ou un
`wx.SpinCtrl` ne porte pas son libelle. C'est le `wx.StaticText` place juste
avant dans le layout qui le nomme pour NVDA et JAWS. Un controle insere au
mauvais endroit laisse une etiquette orpheline, et le lecteur d'ecran annonce
alors le mauvais libelle — ou celui de la section suivante.

Regression reelle : en ajoutant le reglage du moteur de l'extraction guidee,
« Navigateur a utiliser : » s'est retrouve separe de son menu deroulant par
trois widgets. Mathieu l'a entendu depuis la pagination des resultats de
recherche, qui semblait annoncer « Extraction guidee ».
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core import settings as cfg
from app.ui.settings_dialog import SettingsDialog

# Controles qui ne portent PAS leur propre libelle : ils dependent entierement
# du texte qui les precede. Un CheckBox, un Button ou un RadioBox, eux, ont le
# leur et n'ont donc rien a exiger de leur voisin.
SANS_LIBELLE_PROPRE = (wx.Choice, wx.SpinCtrl, wx.TextCtrl, wx.ComboBox)


def _parcours(sizer, trouves, precedent=None):
    """Aplati le sizer dans l'ordre de lecture.

    `precedent` traverse les sous-sizers : une etiquette posee dans le sizer
    parent nomme bien le premier controle d'une rangee horizontale (cas du
    dossier de destination : label, puis [champ + bouton Parcourir]).
    """
    for item in sizer.GetChildren():
        if item.IsSizer():
            precedent = _parcours(item.GetSizer(), trouves, precedent)
            continue
        widget = item.GetWindow()
        if widget is None:
            continue
        if isinstance(widget, wx.StaticText):
            precedent = widget
            continue
        if isinstance(widget, SANS_LIBELLE_PROPRE):
            trouves.append((widget, precedent))
        precedent = None
    return precedent


def _controles_par_onglet(dlg):
    for i in range(dlg.notebook.GetPageCount()):
        page = dlg.notebook.GetPage(i)
        if not page.GetSizer():
            continue
        trouves = []
        _parcours(page.GetSizer(), trouves)
        yield dlg.notebook.GetPageText(i), trouves


@pytest.fixture
def preferences(frame, appdata):
    dlg = SettingsDialog(frame, cfg.load())
    yield dlg
    dlg.Destroy()


class TestEtiquettesDesPreferences:
    def test_chaque_controle_a_une_etiquette_juste_avant(self, preferences):
        orphelins = []
        for onglet, controles in _controles_par_onglet(preferences):
            for widget, etiquette in controles:
                if etiquette is None:
                    orphelins.append(f"{onglet} / {widget.GetName()!r}")
        assert not orphelins, (
            "Controles sans wx.StaticText juste avant eux (NVDA annoncera le "
            "mauvais libelle) : " + ", ".join(orphelins))

    def test_aucune_etiquette_ne_reste_orpheline(self, preferences):
        """Deux etiquettes de suite = la premiere ne nomme plus rien.

        C'est la forme exacte de la regression : « Extraction guidee : »,
        « Navigateur a utiliser : », « Fenetre a utiliser : » se suivaient, et
        le menu du navigateur atterrissait apres un paragraphe d'aide.
        """
        page = preferences.notebook.GetPage(0)
        suite = []
        _aplati(page.GetSizer(), suite)

        # Un titre de section est legitime devant une etiquette : on ne
        # signale que les series de TROIS textes ou plus, qui trahissent un
        # controle parti ailleurs.
        serie = 0
        pires = []
        for widget in suite:
            if isinstance(widget, wx.StaticText):
                serie += 1
                if serie >= 3:
                    pires.append(widget.GetLabel()[:40])
            else:
                serie = 0
        assert not pires, (
            "Trois etiquettes consecutives ou plus : un controle a ete insere "
            f"au mauvais endroit. Vers : {pires}")

    def test_le_reglage_du_moteur_est_bien_etiquete(self, preferences):
        """Le controle ajoute en 0.2.3, nommement."""
        for _onglet, controles in _controles_par_onglet(preferences):
            for widget, etiquette in controles:
                if widget is preferences.choice_uge_engine:
                    assert etiquette is not None
                    assert etiquette.GetLabel().startswith("Fenêtre"), (
                        f"nomme par un paragraphe, pas une etiquette : "
                        f"{etiquette.GetLabel()[:60]!r}")
                    return
        pytest.fail("choice_uge_engine introuvable dans le layout")

    def test_le_choix_du_navigateur_reste_etiquete(self, preferences):
        """Celui que la regression avait rendu orphelin."""
        for _onglet, controles in _controles_par_onglet(preferences):
            for widget, etiquette in controles:
                if widget is preferences.choice_browser:
                    assert etiquette is not None, "etiquette perdue en route"
                    assert etiquette.GetLabel().startswith("Navigateur"), (
                        f"nomme par un paragraphe, pas une etiquette : "
                        f"{etiquette.GetLabel()[:60]!r}")
                    return
        pytest.fail("choice_browser introuvable dans le layout")


def _aplati(sizer, sortie):
    """Tous les widgets d'un sizer, sous-sizers compris, en ordre de lecture."""
    for item in sizer.GetChildren():
        if item.IsSizer():
            _aplati(item.GetSizer(), sortie)
        elif item.GetWindow() is not None:
            sortie.append(item.GetWindow())
