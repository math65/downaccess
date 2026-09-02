"""Le bouton « Supprimer les cookies du site » supprime vraiment.

`Network.deleteCookies` exige un NOM de cookie et ne supprime que ceux qui le
portent. L'appel passait `name=""`, qui ne correspond a aucun cookie reel : le
bouton n'effacait rien. Brad s'est deconnecte, reconnecte, et rien n'a change
(rapport du 2026-09-02, sur 0.2.3).

Deuxieme moitie du meme probleme : les cookies vivent aussi dans le jar que
DownAccess passe a yt-dlp. Vider le navigateur sans l'effacer laissait
l'ancienne session partir a chaque telechargement.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui.login_dialog import _cookie_du_domaine, _oublier_cookies_enregistres


class TestAppartenanceAuDomaine:

    @pytest.mark.parametrize("domaine_cookie", [
        "youtube.com",
        ".youtube.com",            # cookie de session, pose sur la racine
        "accounts.youtube.com",    # cookie de la page de connexion
        ".ACCOUNTS.YouTube.com",   # la casse ne doit rien changer
    ])
    def test_les_cookies_du_site_sont_reconnus(self, domaine_cookie):
        assert _cookie_du_domaine(domaine_cookie, "youtube.com")

    @pytest.mark.parametrize("domaine_cookie", [
        "vimeo.com",
        "notyoutube.com",          # ne doit pas passer par un simple endswith
        "youtube.com.evil.net",
        "",
    ])
    def test_les_autres_sont_ecartes(self, domaine_cookie):
        assert not _cookie_du_domaine(domaine_cookie, "youtube.com")

    def test_sans_domaine_de_reference_rien_ne_correspond(self):
        assert not _cookie_du_domaine(".youtube.com", "")


class FauxParent:
    def __init__(self, sites):
        self.settings = {"cookie_sites": list(sites)}


class FauxDialogue:
    def __init__(self, parent):
        self._parent = parent

    def GetParent(self):
        return self._parent


class TestOubliDesCookiesEnregistres:

    @pytest.fixture(autouse=True)
    def jar_temporaire(self, tmp_path, monkeypatch):
        """Detourne le jar vers un dossier jetable."""
        self.jar = tmp_path / "youtube.com.txt"
        monkeypatch.setattr("app.ui.login_dialog.jar_path_for",
                            lambda url: str(self.jar))
        monkeypatch.setattr("app.core.settings.save", lambda s: None)

    def test_le_jar_est_efface(self):
        self.jar.write_text("# cookies", encoding="utf-8")
        dlg = FauxDialogue(FauxParent([]))
        assert _oublier_cookies_enregistres(dlg, "https://youtube.com/", "youtube.com")
        assert not self.jar.exists(), "yt-dlp enverrait encore l'ancienne session"

    def test_le_site_sort_de_la_liste_des_cookies(self):
        parent = FauxParent(["youtube.com", "vimeo.com"])
        dlg = FauxDialogue(parent)
        _oublier_cookies_enregistres(dlg, "https://youtube.com/", "youtube.com")
        assert parent.settings["cookie_sites"] == ["vimeo.com"]

    def test_rien_a_effacer_se_dit_franchement(self):
        """Sans jar ni site memorise, on ne doit pas annoncer une suppression."""
        dlg = FauxDialogue(FauxParent([]))
        assert not _oublier_cookies_enregistres(
            dlg, "https://youtube.com/", "youtube.com")

    def test_un_jar_verrouille_ne_fait_pas_tout_echouer(self, monkeypatch):
        """Le nettoyage continue meme si le fichier resiste."""
        self.jar.write_text("# cookies", encoding="utf-8")

        def _refuse(self):
            raise OSError("fichier verrouille")

        monkeypatch.setattr("pathlib.Path.unlink", _refuse)
        parent = FauxParent(["youtube.com"])
        dlg = FauxDialogue(parent)
        assert _oublier_cookies_enregistres(
            dlg, "https://youtube.com/", "youtube.com")
        assert parent.settings["cookie_sites"] == []
