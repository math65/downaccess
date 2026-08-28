"""Le format applique aux ajouts qui ne passent pas par la fenetre d'ajout.

Le reglage « Format par defaut » des Preferences vaut pour TOUT ajout ou
l'utilisateur n'a pas de liste sous les yeux. L'extraction guidee l'ignorait
et enfilait toujours en « auto » : Seb avait choisi MP3, l'emission M6 partait
en video, et le garde-fou la refusait — precisement au motif qu'elle n'etait
disponible qu'en son (rapport du 2026-08-28).
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.settings import DEFAULTS


class FausseFenetre:
    """Fenetre principale reduite a ce que les methodes testees utilisent."""

    def __init__(self, **reglages):
        self.settings = dict(DEFAULTS)
        self.settings["_uge_intro_shown"] = True
        self.settings.update(reglages)
        self.enfilees = []

    def _enqueue_url(self, url, format_spec="auto", **kw):
        self.enfilees.append((url, format_spec))

    # Reprise telle quelle : c'est elle que l'extraction guidee doit appeler.
    from app.ui.main_window import MainWindow
    _default_format = MainWindow._default_format


class TestExtractionGuidee:

    def _ajouter(self, faux, monkeypatch, url="https://exemple.test/flux.mpd"):
        """Ouvre l'extraction guidee et rejoue l'ajout d'un media detecte."""
        from app.ui import main_window as mw

        captures = {}

        class FauxDialogue:
            def __init__(self, parent, on_add_url):
                captures["ajout"] = on_add_url

            def Show(self):
                pass

        monkeypatch.setattr(mw, "UGEDialog", FauxDialogue)
        mw.MainWindow._on_uge(faux, None)
        captures["ajout"](url)

    def test_le_format_par_defaut_est_applique(self, monkeypatch):
        """MP3 dans les Preferences : le media detecte part en MP3, pas en video
        (sans quoi une emission M6 se fait refuser alors que son son est
        justement ce qui est demande)."""
        faux = FausseFenetre(post_processing="mp3")
        self._ajouter(faux, monkeypatch)
        assert faux.enfilees == [("https://exemple.test/flux.mpd", "mp3")]

    def test_sans_preference_on_reste_en_auto(self, monkeypatch):
        faux = FausseFenetre(post_processing="auto")
        self._ajouter(faux, monkeypatch)
        assert faux.enfilees == [("https://exemple.test/flux.mpd", "auto")]

    def test_ancien_code_none_replie_sur_auto(self, monkeypatch):
        """« none » est l'ancien code d'avant le format par defaut : un fichier
        de reglages ancien ne doit pas produire un format inconnu."""
        faux = FausseFenetre(post_processing="none")
        self._ajouter(faux, monkeypatch)
        assert faux.enfilees == [("https://exemple.test/flux.mpd", "auto")]
