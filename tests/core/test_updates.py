"""Mises a jour : comparaison de versions et langue des notes de version.

Les deux fonctions couvertes ici ont chacune cause un bug livre :
- un tri lexicographique des versions yt-dlp faisait re-telecharger en boucle ;
- des notes de version sans marqueur affichaient du francais aux anglophones.
"""

import pytest

from app.core.app_updater import _parse_version, _select_notes_for_language
from app.core.updater import _version_key


class TestVersionsYtDlp:
    def test_comparaison_numerique_pas_lexicographique(self):
        """Regression : en tri de chaines, '2026.3.17' passe APRES '2026.10.5'
        (car '3' > '1'), donc l'app choisissait la mauvaise version et la
        re-telechargeait a chaque demarrage."""
        assert _version_key("2026.10.5") > _version_key("2026.3.17")
        assert _version_key("2026.9.1") < _version_key("2026.10.1")

    def test_ordre_general(self):
        versions = ["2026.3.17", "2026.10.5", "2025.12.31", "2026.10.15"]
        assert sorted(versions, key=_version_key) == [
            "2025.12.31", "2026.3.17", "2026.10.5", "2026.10.15"]

    def test_versions_nightly(self):
        """Le canal nightly ajoute un suffixe .devN : il doit se comparer."""
        assert _version_key("2026.8.4.234419.dev0") > _version_key("2026.8.4.234418.dev0")
        assert _version_key("2026.8.5.000000.dev0") > _version_key("2026.8.4.999999.dev0")

    @pytest.mark.parametrize("valeur", ["", None, "inconnue"])
    def test_valeur_absurde_ne_casse_pas(self, valeur):
        assert isinstance(_version_key(valeur), tuple)

    def test_partie_non_numerique_vaut_zero(self):
        assert _version_key("2026.x.1") == (2026, 0, 1)


class TestVersionApplication:
    @pytest.mark.parametrize("tag,attendu", [
        ("v0.2.1", (0, 2, 1)),
        ("0.2.1", (0, 2, 1)),
        (" v1.0.0 ", (1, 0, 0)),
    ])
    def test_lecture(self, tag, attendu):
        assert _parse_version(tag) == attendu

    def test_comparaison(self):
        assert _parse_version("v0.1.35") > _parse_version("v0.1.34")
        assert _parse_version("v0.2.0") > _parse_version("v0.1.99")

    def test_tag_illisible(self):
        assert _parse_version("pas-une-version") == (0,)


CORPS_BILINGUE = """<!-- notes:fr -->
## DownAccess 0.1.34

Un message clair quand le disque est plein.

<!-- notes:en -->
## DownAccess 0.1.34

A clear message when your disk is full.
"""


class TestLangueDesNotes:
    def test_francais(self):
        notes = _select_notes_for_language(CORPS_BILINGUE, "fr")
        assert "disque est plein" in notes
        assert "disk is full" not in notes

    def test_anglais(self):
        """Regression : sans selection, les anglophones voyaient le francais."""
        notes = _select_notes_for_language(CORPS_BILINGUE, "en")
        assert "disk is full" in notes
        assert "disque est plein" not in notes

    def test_marqueur_absent_du_texte_affiche(self):
        assert "notes:" not in _select_notes_for_language(CORPS_BILINGUE, "fr")

    def test_langue_inconnue_retombe_sur_l_anglais(self):
        assert "disk is full" in _select_notes_for_language(CORPS_BILINGUE, "de")

    def test_corps_sans_marqueur_rendu_tel_quel(self):
        """Les anciennes releases n'etaient pas balisees : ne rien perdre."""
        brut = "## 0.1.10\n\nDes corrections."
        assert _select_notes_for_language(brut, "en") == brut

    def test_corps_vide(self):
        assert _select_notes_for_language("", "fr") == ""

    def test_une_seule_langue_disponible(self):
        corps = "<!-- notes:fr -->\nSeulement du francais."
        assert "Seulement du francais." in _select_notes_for_language(corps, "en")
