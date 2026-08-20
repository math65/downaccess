"""Classification et reformulation des erreurs de telechargement.

Ces tests encodent des bugs reellement vecus : un disque plein qu'on reessayait,
et un message brut en anglais que les utilisateurs prenaient pour une panne de
l'application.
"""

import pytest

from app.core.downloader import (
    _humanize_error,
    _is_login_required,
    disk_full_message,
    is_disk_full_error,
    is_transient_error,
    not_enough_space_message,
)

DISK_FULL_RAW = "ERROR: unable to write data: [Errno 28] No space left on device"


class TestDisquePlein:
    @pytest.mark.parametrize("message", [
        DISK_FULL_RAW,
        "OSError: [Errno 28] No space left on device",
        "ERROR: Unable to download video: [Errno 28] No space left on device",
        "There is not enough space on the disk",
        "Not enough space on the device",
        "Espace insuffisant sur le disque",
    ])
    def test_reconnait_les_formulations(self, message):
        assert is_disk_full_error(message)

    @pytest.mark.parametrize("message", [
        "HTTP Error 403: Forbidden",
        "Video unavailable",
        "",
    ])
    def test_ne_confond_pas_avec_autre_chose(self, message):
        assert not is_disk_full_error(message)

    def test_n_est_jamais_transitoire(self):
        """Regression : reessayer un disque plein ne fait que le remplir encore."""
        assert not is_transient_error(DISK_FULL_RAW)

    def test_message_remplace_le_texte_brut(self, tmp_path):
        friendly = _humanize_error(DISK_FULL_RAW, str(tmp_path))
        assert "Errno 28" not in friendly
        assert "No space left" not in friendly
        assert "disque est plein" in friendly
        # Le message doit dire ou regarder et quoi faire.
        assert str(tmp_path) in friendly
        assert "Préférences" in friendly

    def test_message_sans_dossier_reste_utilisable(self):
        assert "disque est plein" in disk_full_message("")

    def test_message_prealable_chiffre_le_manque(self, tmp_path):
        msg = not_enough_space_message(str(tmp_path), 2_360_000_000, 41_000_000)
        assert "2.2 Go" in msg      # ce qu'il faut
        assert "39 Mo" in msg       # ce qu'il reste


class TestErreursTransitoires:
    @pytest.mark.parametrize("message", [
        "HTTP Error 403: Forbidden",
        "ERROR: unable to download video data: HTTP Error 403",
        "HTTP Error 500: Internal Server Error",
        "HTTP Error 502: Bad Gateway",
        "HTTP Error 503: Service Unavailable",
        "IncompleteRead(960 bytes read, 1024 more expected)",
        "ERROR: content too short",
    ])
    def test_merite_une_nouvelle_extraction(self, message):
        assert is_transient_error(message)

    @pytest.mark.parametrize("message", [
        "Annulé par l'utilisateur",
        "Download cancelled",
    ])
    def test_une_annulation_ne_se_reessaie_jamais(self, message):
        assert not is_transient_error(message)

    def test_une_erreur_definitive_ne_se_reessaie_pas(self):
        assert not is_transient_error("Video unavailable: private video")


class TestConnexionRequise:
    @pytest.mark.parametrize("message", [
        "ERROR: Sign in to confirm your age",
        "ERROR: Join this channel to get access to members-only content",
        "Use --cookies-from-browser or --cookies",
        "Please log in to continue",
    ])
    def test_detecte_le_besoin_de_connexion(self, message):
        assert _is_login_required(message)

    def test_reformule_en_message_clair(self):
        friendly = _humanize_error("ERROR: Sign in to confirm your age")
        assert "connecté" in friendly

    def test_cookies_verrouilles_explique_la_manoeuvre(self):
        raw = "Could not copy Chrome cookie database, Permission denied"
        friendly = _humanize_error(raw)
        assert "navigateur" in friendly
        assert "Fermez" in friendly

    def test_une_erreur_inconnue_passe_telle_quelle(self):
        raw = "ERROR: something nobody anticipated"
        assert _humanize_error(raw) == raw
