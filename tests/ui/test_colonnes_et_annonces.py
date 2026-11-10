"""Flèches Gauche/Droite dans le tableau et raccourci des annonces (2026-11-10).

Brad : « Gauche ou Droite dans le tableau ne fait rien, même quand une vidéo
est terminée ». Le guide promettait pourtant d'entendre chaque colonne, mais
une liste Windows native ne fait que défiler et NVDA n'annonce rien.

Seb : un raccourci pour couper les annonces « Téléchargement démarré /
terminé » sans passer par les Préférences. Couper puis rétablir doit rendre
le mode choisi avant (« au premier plan » ne doit pas devenir « toujours »).
"""

import pytest

from app.core import settings as cfg

wx = pytest.importorskip("wx")


class TestBasculeAnnonces:
    def test_couper_puis_retablir_rend_le_mode_d_avant(self):
        s = {"download_announcements": "foreground"}
        assert cfg.toggle_download_announcements(s) is False
        assert s["download_announcements"] == "never"
        assert cfg.toggle_download_announcements(s) is True
        assert s["download_announcements"] == "foreground"

    def test_retablir_sans_memoire_donne_toujours(self):
        # Coupé depuis les Préférences : rien à rendre, on rallume en plein.
        s = {"download_announcements": "never"}
        assert cfg.toggle_download_announcements(s) is True
        assert s["download_announcements"] == "always"

    def test_reglage_absent_vaut_toujours(self):
        s = {}
        assert cfg.toggle_download_announcements(s) is False
        assert s["download_announcements"] == "never"
        cfg.toggle_download_announcements(s)
        assert s["download_announcements"] == "always"


@pytest.mark.gui
class TestColonnes:
    @pytest.fixture
    def liste(self, frame):
        from app.ui.download_list import DownloadList, STATUS_DONE
        liste = DownloadList(frame)
        liste.add_item("a", "Tony Robinson", "YouTube", "MP4")
        liste.complete_item("a", size="1,2 Go")
        liste.add_item("b", "Deuxième", "Arte", "")
        liste.set_status("b", STATUS_DONE)
        liste.Focus(0)
        return liste

    def test_droite_part_du_titre_puis_avance(self, liste):
        assert liste.move_column(1) == "Titre : Tony Robinson"
        assert liste.move_column(1) == "Site : YouTube"
        assert liste.move_column(1) == "Format : MP4"

    def test_gauche_sur_nouvelle_ligne_part_de_la_fin(self, liste):
        assert liste.move_column(-1) == "Taille : 1,2 Go"
        assert liste.move_column(-1).startswith("Progression : ")

    def test_colonne_vide_le_dit(self, liste):
        liste.Focus(1)
        liste.move_column(1)
        liste.move_column(1)
        assert liste.move_column(1) == "Format : vide"

    def test_bords_bloquent(self, liste):
        liste.move_column(1)
        assert liste.move_column(-1) == "Titre : Tony Robinson"
        assert liste.move_column(99) == "Taille : 1,2 Go"
        assert liste.move_column(1) == "Taille : 1,2 Go"

    def test_changer_de_ligne_repart_de_zero(self, liste):
        # Haut/Bas : le lecteur d'écran lit la ligne entière ; ensuite
        # Droite doit redonner le titre, pas la colonne de la ligne d'avant.
        for _ in range(4):
            liste.move_column(1)                 # jusqu'à « Statut »
        liste.Focus(1)
        assert liste.move_column(1) == "Titre : Deuxième"

    def test_sans_ligne_rien_a_dire(self, frame):
        from app.ui.download_list import DownloadList
        assert DownloadList(frame).move_column(1) == ""

    def test_anglais(self, liste, english_ui):
        liste.move_column(1)
        assert liste.move_column(1) == "Site: YouTube"


@pytest.mark.gui
def test_raccourci_coupe_sauve_coche_et_confirme(appdata, monkeypatch, wx_app):
    from app.ui import main_window as mw

    dits = []
    monkeypatch.setattr(mw.speech, "speak", lambda t, **kw: dits.append(t))

    menu = wx.Menu()

    class FausseFenetre:
        def __init__(self):
            self.settings = {"download_announcements": "always"}
            self.statut = ""
            self.mi_announce_toggle = menu.AppendCheckItem(wx.ID_ANY, "x")
        def set_status(self, t):
            self.statut = t
        _on_announce_toggle = mw.MainWindow._on_announce_toggle

    f = FausseFenetre()
    f.mi_announce_toggle.Check(True)
    f._on_announce_toggle(None)
    assert not f.mi_announce_toggle.IsChecked()
    assert cfg.load()["download_announcements"] == "never"
    # Confirmé même en coupant : c'est la réponse à la touche.
    assert dits == ["Annonces de téléchargement désactivées."]
    assert f.statut == dits[0]

    f._on_announce_toggle(None)
    assert f.mi_announce_toggle.IsChecked()
    assert cfg.load()["download_announcements"] == "always"
    menu.Destroy()
