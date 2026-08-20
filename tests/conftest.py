"""Socle commun de la suite de tests DownAccess.

Deux precautions structurent tout le reste :

1. **Aucun test ne touche la vraie configuration.** `%APPDATA%` est redirige
   vers un dossier temporaire pour toute la session : un test ne doit jamais
   pouvoir effacer les abonnements, l'historique ou les reglages de la personne
   qui le lance.
2. **`_` est installe avant le premier import applicatif.** Les modules de
   `app/core` utilisent le wrapper paresseux `_translate`, mais les tests, eux,
   comparent des chaines traduites : la langue doit etre posee explicitement.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Redirection de la configuration AVANT tout import de app.core.* : plusieurs
# modules resolvent leur chemin de stockage a l'appel, mais mieux vaut que la
# variable soit deja bonne si l'un d'eux le faisait a l'import.
_SANDBOX = tempfile.mkdtemp(prefix="downaccess_tests_")
os.environ["APPDATA"] = _SANDBOX

from app.core import i18n


@pytest.fixture(scope="session", autouse=True)
def _french_ui():
    """Langue de reference des tests : le francais, langue source des msgid."""
    i18n.install_language("fr")


@pytest.fixture
def english_ui():
    """Bascule en anglais pour un test, puis restaure le francais."""
    i18n.install_language("en")
    yield
    i18n.install_language("fr")


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Dossier de configuration isole, propre a un seul test.

    A utiliser des qu'un test ecrit dans settings.json, history.json ou
    subscriptions.json : sans lui, deux tests se marcheraient dessus.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="session")
def wx_app():
    """Instance unique de `wx.App` pour les tests d'interface.

    wxPython n'autorise qu'une application par processus et supporte mal
    d'etre detruite puis recreee : la fixture est donc de portee session.
    """
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    yield app
    # Menage : une fenetre encore vivante a la fin de la session fait rouspeter
    # wxWidgets au dechargement de ses classes Win32.
    for fenetre in list(wx.GetTopLevelWindows()):
        fenetre.Destroy()
    app.Yield()


@pytest.fixture
def frame(wx_app):
    """Fenetre parente jetable pour construire un dialogue."""
    import wx
    parent = wx.Frame(None)
    yield parent
    parent.Destroy()


def read_fixture(name: str) -> bytes:
    """Contenu binaire d'un fichier de `tests/fixtures`."""
    return (Path(__file__).parent / "fixtures" / name).read_bytes()


def read_fixture_text(name: str) -> str:
    return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")
