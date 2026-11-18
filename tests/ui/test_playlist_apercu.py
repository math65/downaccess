"""Apercu audio depuis la fenetre de playlist.

L'apercu n'existait que dans les resultats de recherche, qui ne couvrent pas
ici.fr : impossible d'ecouter une emission d'un programme avant de la
telecharger, alors que plus de la moitie n'ont pour titre que le nom du
programme et une date (2026-11-18).
"""
import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui.playlist_dialog import PlaylistDialog

ENTREES = [
    {"title": "Émission avec page",
     "url": "https://www.ici.fr/emissions/nom-de-la-serie/premiere-emission-1000001"},
    {"title": "Vidéo YouTube", "id": "dQw4w9WgXcQ", "url": "dQw4w9WgXcQ", "ie_key": "Youtube"},
    {"title": "Schéma interne", "id": "x", "url": "francetv:abc", "ie_key": "FranceTV"},
]


def test_bouton_apercu_etiquete_et_dans_l_ordre_de_tabulation(frame):
    dlg = PlaylistDialog(frame, "Programme", ENTREES)
    assert dlg.btn_preview.GetLabel() and dlg.btn_preview.GetName()
    # Juste apres les boutons de selection, avant les reglages.
    ordre = [c for c in dlg.btn_preview.GetParent().GetChildren()]
    assert ordre.index(dlg.btn_preview) == ordre.index(dlg.btn_invert) + 1
    assert dlg.FindFocus() is dlg.lst, "le focus reste sur la liste"
    dlg.Destroy()


def test_adresse_d_apercu_selon_le_site(frame):
    dlg = PlaylistDialog(frame, "Programme", ENTREES)
    assert dlg.preview_url(0) == ENTREES[0]["url"]
    assert dlg.preview_url(1) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert dlg.preview_url(2) == "", "un schema interne a yt-dlp ne se lit pas"
    assert dlg.preview_url(-1) == "" and dlg.preview_url(99) == ""
    dlg.Destroy()


def test_sans_adresse_un_message_et_pas_de_lecteur(frame, monkeypatch):
    vus = []
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **kw: vus.append(a[0]))
    dlg = PlaylistDialog(frame, "Programme", ENTREES)
    dlg.lst.Select(2)
    dlg._on_preview(None)
    assert len(vus) == 1 and "aperçu" in vus[0].lower()
    dlg.Destroy()
