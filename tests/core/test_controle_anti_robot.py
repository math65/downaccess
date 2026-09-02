"""Le controle anti-robot n'est pas une demande de connexion.

Quand trop de telechargements partent coup sur coup de la meme adresse IP,
YouTube repond « Sign in to confirm you're not a bot » et yt-dlp y ajoute son
conseil habituel sur les cookies. DownAccess y lisait une demande de connexion
et ouvrait sa fenetre « Connexion necessaire » — une par video en echec.

Brad a enfile ses fictions audio et s'est retrouve devant des centaines de
fenetres, a se deconnecter et se reconnecter sans que rien ne change : la
limite porte sur l'adresse Internet, pas sur le compte (rapport du 2026-09-02,
sur 0.2.3).
"""

import pytest

from app.core.downloader import (
    DownloadError,
    LoginRequiredError,
    _humanize_error,
    _is_login_required,
    _raise_download_error,
    bot_check_message,
    is_bot_check_error,
    is_transient_error,
    should_retry_without_cookies,
)

# Le message tel que yt-dlp le remonte, conseil sur les cookies compris.
ANTI_ROBOT = (
    "ERROR: [youtube] dQw4w9WgXcQ: Sign in to confirm you're not a bot. "
    "Use --cookies-from-browser or --cookies for the authentication. "
    "See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ  for how to manually "
    "pass cookies."
)

# La variante sans apostrophe typographique, vue aussi dans les rapports.
ANTI_ROBOT_BIS = "ERROR: Sign in to confirm you are not a bot"


class TestReconnaissance:

    @pytest.mark.parametrize("message", [ANTI_ROBOT, ANTI_ROBOT_BIS])
    def test_le_controle_est_reconnu(self, message):
        assert is_bot_check_error(message)

    @pytest.mark.parametrize("message", [ANTI_ROBOT, ANTI_ROBOT_BIS])
    def test_ce_n_est_pas_une_demande_de_connexion(self, message):
        """Le coeur du bug : trois motifs de la liste « connexion requise »
        repondent a ce message (« sign in to confirm », « cookies-from-browser »,
        « for the authentication »)."""
        assert not _is_login_required(message)

    def test_une_vraie_video_privee_reste_une_demande_de_connexion(self):
        """Le garde-fou ne doit pas avoir emporte les vrais cas avec lui."""
        assert _is_login_required(
            "ERROR: Private video. Sign in if you've been granted access")
        assert _is_login_required("ERROR: This video is age-restricted")

    def test_un_message_ordinaire_n_est_pas_un_controle(self):
        assert not is_bot_check_error("HTTP Error 403: Forbidden")
        assert not is_bot_check_error("")


class TestConsequences:

    def test_l_erreur_levee_ne_propose_pas_de_se_connecter(self):
        """`LoginRequiredError` declenche la fenetre de connexion guidee :
        c'est precisement ce qu'il ne faut pas ouvrir ici."""
        with pytest.raises(DownloadError) as pris:
            _raise_download_error(ANTI_ROBOT, Exception("boum"))
        assert not isinstance(pris.value, LoginRequiredError)

    def test_le_message_dit_que_se_connecter_n_y_changera_rien(self):
        texte = _humanize_error(ANTI_ROBOT)
        assert texte == bot_check_message()
        assert "robot" in texte.lower()
        # Le contresens que Brad a vecu : chercher du cote du compte.
        assert "connecter n'y changera" in texte

    def test_on_ne_reessaie_pas_tout_de_suite(self):
        """C'est le nombre de requetes qui a declenche la limite : en ajouter
        est exactement ce qu'il ne faut pas faire."""
        assert not is_transient_error(ANTI_ROBOT)

    def test_on_ne_retente_pas_sans_les_cookies(self):
        """La limite porte sur l'adresse IP : retirer les cookies ne ferait
        qu'une requete de plus."""
        assert not should_retry_without_cookies(ANTI_ROBOT)
