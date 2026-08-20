"""L'interface doit tenir debout dans les deux langues.

Une traduction manquante ou un libelle vide ne se voit pas en francais, langue
source : ces tests reconstruisent les memes fenetres en anglais et verifient
que rien ne se perd en route.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.settings import DEFAULTS
from app.core.subscriptions import FeedEntry
from app.ui.add_url_dialog import AddUrlDialog
from app.ui.new_items_dialog import NewItemsDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.subscriptions_dialog import AddSubscriptionDialog
from app.ui.transcript_dialog import TranscriptDialog


def construire(frame):
    """Une instance de chaque fenetre reconstruite a l'identique par langue."""
    entree = FeedEntry(entry_id="1", title="T", url="https://a/1", summary="S")
    return [
        AddUrlDialog(frame),
        AddUrlDialog(frame, with_range=True),
        SettingsDialog(frame, dict(DEFAULTS)),
        TranscriptDialog(frame, "Titre", "texte", "fr"),
        AddSubscriptionDialog(frame),
        NewItemsDialog(frame, [("Source", entree, "")]),
    ]


def libelles(dialogue):
    """Tous les textes affiches par une fenetre."""
    trouves = [dialogue.GetTitle()]

    def parcourir(parent):
        for enfant in parent.GetChildren():
            if isinstance(enfant, wx.Button | wx.StaticText | wx.CheckBox):
                trouves.append(enfant.GetLabel())
            parcourir(enfant)

    parcourir(dialogue)
    return trouves


class TestConstructionBilingue:
    def test_toutes_les_fenetres_se_construisent_en_anglais(self, frame, english_ui):
        dialogues = construire(frame)
        assert len(dialogues) == 6
        for dlg in dialogues:
            dlg.Destroy()

    def test_aucun_libelle_vide(self, frame, english_ui):
        vides = []
        for dlg in construire(frame):
            titre = dlg.GetTitle()
            for texte in libelles(dlg):
                if not texte.strip():
                    vides.append(titre)
            dlg.Destroy()
        assert vides == []

    def test_les_titres_changent_de_langue(self, frame, english_ui):
        """Si un titre est identique dans les deux langues, c'est souvent une
        traduction oubliee (sauf mot identique, ex. « Options »)."""
        dlg = AddUrlDialog(frame)
        titre_en = dlg.GetTitle()
        dlg.Destroy()
        assert titre_en == "Add URLs"

    def test_pas_de_marqueur_de_traduction_visible(self, frame, english_ui):
        """Un libelle contenant encore une accolade non formatee signale un
        `.format()` oublie."""
        suspects = []
        for dlg in construire(frame):
            for texte in libelles(dlg):
                if "{" in texte or "}" in texte:
                    suspects.append(texte)
            dlg.Destroy()
        assert suspects == []


class TestAccentsEnFrancais:
    def test_les_libelles_francais_sont_accentues(self, frame):
        """Detecte un texte utilisateur tape sans accents (regle du projet)."""
        import re
        sans_accent = re.compile(
            r"\b(telecharg\w*|verifi\w*|prefere\w*|nouveaute\w*|resume\w*|"
            r"selection\w*|creer|genere|termine|deja|apres|chaine)\b", re.IGNORECASE)
        fautifs = []
        for dlg in construire(frame):
            for texte in libelles(dlg):
                fautifs.extend(sans_accent.findall(texte))
            dlg.Destroy()
        assert fautifs == []
