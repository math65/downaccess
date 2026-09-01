"""Raccourcis clavier a l'interieur de la fenetre de navigation.

WebView2 est un moteur nu : pywebview ne lui active les touches du navigateur
qu'en mode debug, qui ouvrirait aussi les outils de developpement. On injecte
donc un gestionnaire dans la page.

⚠️ Regle a ne pas casser : l'injection ne vaut QUE pour WebView2. Un vrai
navigateur traite deja Alt+Fleche ; les deux ensemble reculeraient de deux
pages d'un coup.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui import uge_dialog as uge


class TestScriptDesRaccourcis:
    def test_le_script_couvre_les_trois_touches(self):
        script = uge._NAV_KEYS_SCRIPT
        assert "ArrowLeft" in script and "history.back()" in script
        assert "ArrowRight" in script and "history.forward()" in script
        assert "F5" in script and "location.reload()" in script

    def test_le_script_ecoute_en_capture(self):
        """Sinon une page qui gere elle-meme les touches nous prend la main."""
        assert ", true)" in uge._NAV_KEYS_SCRIPT

    def test_le_script_ne_s_installe_qu_une_fois(self):
        """Il est rejoue a chaque page : sans garde, les gestionnaires
        s'empileraient et un Alt+Gauche reculerait de plusieurs pages."""
        assert "__da_nav_keys" in uge._NAV_KEYS_SCRIPT
        assert "if (window.__da_nav_keys) return;" in uge._NAV_KEYS_SCRIPT

    def test_alt_seul_sans_ctrl_ni_maj(self):
        """Ctrl+Alt+Gauche fait tourner l'ecran sous Windows : ne pas s'en
        emparer."""
        assert "!e.ctrlKey" in uge._NAV_KEYS_SCRIPT
        assert "!e.shiftKey" in uge._NAV_KEYS_SCRIPT


class TestInstallationDesRaccourcis:
    class Faux:
        def __init__(self, casse=False):
            self.cdp = []
            self.js = []
            self.casse = casse

        def run_cdp(self, methode, **kw):
            if self.casse:
                raise RuntimeError("refus")
            self.cdp.append((methode, kw.get("source", "")))

        def run_js(self, script):
            self.js.append(script)

    def _fenetre(self, page):
        objet = type("F", (), {})()
        objet._page = page
        objet._install_nav_keys = uge.UGEDialog._install_nav_keys.__get__(objet)
        return objet

    def test_injection_persistante_et_page_courante(self):
        """Persistante pour les pages a venir, immediate pour celle affichee."""
        page = self.Faux()
        self._fenetre(page)._install_nav_keys()
        assert page.cdp[0][0] == "Page.addScriptToEvaluateOnNewDocument"
        assert "__da_nav_keys" in page.cdp[0][1]
        assert page.js and "__da_nav_keys" in page.js[0]

    def test_un_moteur_qui_refuse_ne_casse_pas_l_extraction(self):
        """Les raccourcis sont un confort : les boutons restent la."""
        page = self.Faux(casse=True)
        self._fenetre(page)._install_nav_keys()   # ne doit pas lever
