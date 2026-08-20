"""Sante des catalogues de traduction et des textes affiches.

Ces tests attrapent mecaniquement deux erreurs commises a repetition :
une chaine ajoutee au code mais jamais traduite en anglais, et un texte
francais ecrit sans accents.
"""

import re
import subprocess
import sys
from pathlib import Path

import polib
import pytest

ROOT = Path(__file__).resolve().parent.parent
PO_EN = ROOT / "locales" / "en" / "LC_MESSAGES" / "base.po"
POT = ROOT / "locales" / "base.pot"


@pytest.fixture(scope="module")
def catalogue_en():
    return polib.pofile(str(PO_EN))


class TestCatalogueAnglais:
    def test_aucune_chaine_non_traduite(self, catalogue_en):
        manquantes = [e.msgid for e in catalogue_en.untranslated_entries()]
        assert manquantes == [], (
            f"{len(manquantes)} chaine(s) sans traduction anglaise. "
            f"Lancer : uv run python scripts/manage_i18n.py update --lang en")

    def test_aucune_chaine_approximative(self, catalogue_en):
        floues = [e.msgid for e in catalogue_en.fuzzy_entries()]
        assert floues == [], f"{len(floues)} traduction(s) marquee(s) fuzzy a relire"

    def test_aucune_entree_orpheline(self, catalogue_en):
        """Une entree sans occurrence n'existe plus dans le code : elle doit
        etre retiree, pas trainer en doublon d'une version obsolete."""
        orphelines = [e.msgid for e in catalogue_en if not e.occurrences]
        assert orphelines == []

    def test_reperes_de_format_preserves(self, catalogue_en):
        """Une traduction qui perd un {placeholder} provoque un KeyError a
        l'affichage — donc un plantage, en anglais seulement."""
        motif = re.compile(r"\{(\w+)\}")
        fautives = []
        for entry in catalogue_en.translated_entries():
            attendus = set(motif.findall(entry.msgid))
            obtenus = set(motif.findall(entry.msgstr))
            if attendus != obtenus:
                fautives.append((entry.msgid[:60], sorted(attendus), sorted(obtenus)))
        assert fautives == []

    def test_accelerateurs_de_menu_preserves(self, catalogue_en):
        """Un libelle de menu perdant son raccourci le rendrait injoignable."""
        fautives = [
            e.msgid[:60] for e in catalogue_en.translated_entries()
            if "\t" in e.msgid and "\t" not in e.msgstr
        ]
        assert fautives == []


class TestSourceFrancaise:
    """Les msgid sont du francais : ils doivent etre ecrits correctement."""

    # Mots frequemment tapes sans accent dans ce projet.
    SANS_ACCENT = re.compile(
        r"\b("
        r"telecharg\w*|verifi\w*|prefere\w*|preference\w*|parametre\w*|"
        r"nouveaute\w*|resume\w*|selection\w*|selectionn\w*|"
        r"cree|creer|genere|generer|termine|annule|"
        r"deja|apres|tres|etre|meme|"
        r"video|videos|media|medias|"
        r"donnee\w*|systeme|acces|"
        r"chaine|chaines|"
        r"reussi|echec|echoue"
        r")\b",
        re.IGNORECASE,
    )

    # Noms propres contenant des mots qui, en francais, prendraient un accent.
    PRODUITS = ("Access Media Converter", "Prime Video", "Media Converter")

    def test_pas_de_mot_francais_sans_accent(self, catalogue_en):
        fautifs = []
        for entry in catalogue_en:
            texte = entry.msgid
            for produit in self.PRODUITS:
                texte = texte.replace(produit, "")
            for mot in self.SANS_ACCENT.findall(texte):
                fautifs.append(f"{mot!r} dans {entry.msgid[:70]!r}")
        assert fautifs == [], (
            "Textes utilisateur sans accents francais :\n  " + "\n  ".join(fautifs[:20]))


class TestSynchronisation:
    def test_toute_chaine_du_code_est_au_catalogue(self, tmp_path, catalogue_en):
        """Une chaine `_()` ajoutee au code mais jamais extraite resterait en
        francais pour les anglophones, sans que rien ne le signale.

        On compare les msgid, pas le texte du fichier : les numeros de ligne
        du .pot bougent a la moindre edition et n'ont aucune valeur ici.
        """
        modele = tmp_path / "base.pot"
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "manage_i18n.py"), "extract"],
            cwd=ROOT, check=True, capture_output=True,
        )
        modele.write_bytes(POT.read_bytes())
        attendus = {e.msgid for e in polib.pofile(str(modele))}
        connus = {e.msgid for e in catalogue_en}
        manquants = sorted(attendus - connus)
        assert manquants == [], (
            f"{len(manquants)} chaine(s) du code absente(s) du catalogue anglais : "
            f"{manquants[:5]}. Lancer : "
            f"uv run python scripts/manage_i18n.py update --lang en")
