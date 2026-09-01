"""Les dialogues « Comment ca marche » ne doivent apparaitre qu'une fois.

Regression reelle (signalee par Mathieu, 2026-09-01) : ils revenaient a CHAQUE
lancement. `settings.load()` ne conserve que les cles presentes dans DEFAULTS
(`settings.py`, filtre `if k in DEFAULTS`) — or `_uge_intro_shown` n'y etait
pas. Le drapeau etait donc bien ecrit sur le disque, puis jete au demarrage
suivant.
"""

import json

from app.core import settings as cfg

CLES_INTRO = ("_uge_intro_shown", "_login_intro_shown")


class TestDialoguesDIntroduction:
    def test_les_cles_sont_dans_les_valeurs_par_defaut(self):
        """Sans cela, `load()` les filtre et le dialogue revient sans fin."""
        for cle in CLES_INTRO:
            assert cle in cfg.DEFAULTS, (
                f"{cle} absente de DEFAULTS : elle sera jetee au chargement")

    def test_par_defaut_le_dialogue_est_a_montrer(self):
        for cle in CLES_INTRO:
            assert cfg.DEFAULTS[cle] is False

    def test_le_drapeau_survit_a_un_aller_retour_disque(self, appdata):
        """Le coeur du bug : ecrire puis relire."""
        reglages = cfg.load()
        for cle in CLES_INTRO:
            reglages[cle] = True
        cfg.save(reglages)

        relu = cfg.load()
        for cle in CLES_INTRO:
            assert relu[cle] is True, (
                f"{cle} perdue au rechargement : le dialogue reviendrait")

    def test_le_drapeau_est_bien_ecrit_sur_le_disque(self, appdata):
        reglages = cfg.load()
        reglages["_uge_intro_shown"] = True
        cfg.save(reglages)
        brut = json.loads(
            (appdata / "DownAccess" / "settings.json").read_text(encoding="utf-8"))
        assert brut["_uge_intro_shown"] is True

    def test_une_configuration_neuve_montre_les_dialogues(self, appdata):
        neuf = cfg.load()
        assert neuf["_uge_intro_shown"] is False
        assert neuf["_login_intro_shown"] is False
