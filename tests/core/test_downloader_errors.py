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
    drm_locked_video_message,
    is_disk_full_error,
    is_drm_error,
    is_hopeless_error,
    is_network_down_error,
    accepts_audio_only,
    video_is_drm_locked,
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


# Erreur reellement remontee par un testeur le 2026-08-22 : sa connexion a
# laché une seconde pendant l'analyse d'une page france.tv.
DNS_RAW = ("ERROR: [francetv:site] 8542604-dans-cette-tribu: Unable to download "
           "webpage: HTTPSConnection(host='www.france.tv', port=443): Failed to "
           "resolve 'www.france.tv' ([Errno 11001] getaddrinfo failed)")

DRM_RAW = ("ERROR: [francetv] 29b2c7ed-8542-4e01-9195-28ef9a28aefd: "
           "This video is DRM protected")


class TestCoupureReseau:
    """Regression : une coupure de connexion n'etait pas reessayee, et son
    message brut en anglais faisait croire a une panne de l'application."""

    def test_coupure_dns_est_transitoire(self):
        assert is_transient_error(DNS_RAW) is True

    def test_coupure_dns_reconnue(self):
        assert is_network_down_error(DNS_RAW) is True

    @pytest.mark.parametrize("brut", [
        "Failed to resolve 'www.france.tv'",
        "[Errno 11001] getaddrinfo failed",
        "Name or service not known",
        "Temporary failure in name resolution",
        "Network is unreachable",
        "Connection refused",
    ])
    def test_variantes_de_coupure(self, brut):
        assert is_network_down_error(brut) is True
        assert is_transient_error(brut) is True

    @pytest.mark.parametrize("brut", [
        "Connection reset by peer",
        "Connection aborted",
    ])
    def test_connexion_interrompue_reessayee(self, brut):
        """Reessayable, mais pas forcement une connexion coupee : le serveur
        peut avoir ferme la porte. Le message reste generique."""
        assert is_transient_error(brut) is True

    def test_message_en_francais(self):
        message = _humanize_error(DNS_RAW)
        assert "connexion" in message.lower()
        assert "getaddrinfo" not in message
        assert "F2" in message, "l'utilisateur doit savoir comment relancer"

    def test_le_disque_plein_n_est_pas_une_coupure(self):
        assert is_network_down_error(DISK_FULL_RAW) is False


class TestDrm:
    """Le DRM est sans issue : aucun reglage n'y changera rien. Le dire
    clairement evite a l'utilisateur de chercher ce qu'il a mal fait."""

    def test_drm_reconnu(self):
        assert is_drm_error(DRM_RAW) is True

    def test_drm_jamais_reessaye(self):
        """Reessayer un contenu protege ne peut mener nulle part."""
        assert is_transient_error(DRM_RAW) is False

    def test_message_en_francais(self):
        message = _humanize_error(DRM_RAW)
        assert "protégée" in message
        assert "DRM protected" not in message

    def test_pas_de_faux_positif(self):
        assert is_drm_error("ERROR: unable to download video data") is False
        assert is_drm_error(DISK_FULL_RAW) is False


class TestNouvelleTentativeALAnalyse:
    """Regression : l'analyse n'a jamais retente, meme sur une coupure reseau.

    Un testeur a perdu sa connexion une seconde pendant l'analyse d'une page
    france.tv ; le telechargement a echoue net, avec un message technique en
    anglais. Le telechargement, lui, retentait deja trois fois : c'est l'etape
    d'avant qui abandonnait au premier echec.
    """

    @pytest.fixture(autouse=True)
    def sans_attente(self, monkeypatch):
        """Neutralise la pause entre deux tentatives : on teste la logique de
        reprise, pas la montre. Sans cela la classe couterait six secondes."""
        from app.core import downloader
        monkeypatch.setattr(downloader.time, "sleep", lambda _s: None)

    def telechargeur(self, tmp_path):
        from app.core.downloader import Downloader
        return Downloader({"download_folder": str(tmp_path)})

    def faux_extract(self, echecs, resultat):
        """Echoue `echecs` fois avec une coupure DNS, puis reussit."""
        import yt_dlp
        etat = {"appels": 0}

        def _extract(self, download_id, url, flat_opts, **_kw):
            etat["appels"] += 1
            if etat["appels"] <= echecs:
                raise yt_dlp.utils.DownloadError(DNS_RAW)
            return resultat

        return etat, _extract

    def test_une_coupure_passagere_ne_fait_plus_echouer(self, tmp_path, monkeypatch):
        from app.core.downloader import DownloadInfo, Downloader
        attendu = DownloadInfo(download_id="x", url="https://a/1", title="Titre")
        etat, faux = self.faux_extract(echecs=1, resultat=attendu)
        monkeypatch.setattr(Downloader, "_extract_info", faux)
        info = self.telechargeur(tmp_path).fetch_info("x", "https://a/1")
        assert info is attendu
        assert etat["appels"] == 2, "la deuxieme tentative doit avoir eu lieu"

    def test_abandon_apres_trois_tentatives(self, tmp_path, monkeypatch):
        from app.core.downloader import DownloadError, Downloader
        etat, faux = self.faux_extract(echecs=99, resultat=None)
        monkeypatch.setattr(Downloader, "_extract_info", faux)
        with pytest.raises(DownloadError) as err:
            self.telechargeur(tmp_path).fetch_info("x", "https://a/1")
        assert etat["appels"] == 3
        assert "connexion" in str(err.value).lower(), "message clair, pas le brut"

    def test_une_erreur_definitive_n_est_pas_reessayee(self, tmp_path, monkeypatch):
        """Le DRM ne s'arrangera pas en reessayant : echouer tout de suite."""
        import yt_dlp
        from app.core.downloader import DownloadError, Downloader
        etat = {"appels": 0}

        def _extract(self, download_id, url, flat_opts, **_kw):
            etat["appels"] += 1
            raise yt_dlp.utils.DownloadError(DRM_RAW)

        monkeypatch.setattr(Downloader, "_extract_info", _extract)
        with pytest.raises(DownloadError):
            self.telechargeur(tmp_path).fetch_info("x", "https://a/1")
        assert etat["appels"] == 1

    def test_annulation_interrompt_l_attente(self, tmp_path, monkeypatch):
        """Annuler pendant l'attente entre deux essais doit rendre la main."""
        import threading
        from app.core.downloader import DownloadError, Downloader
        arret = threading.Event()
        etat = {"appels": 0}

        def _extract(self, download_id, url, flat_opts, **_kw):
            import yt_dlp
            etat["appels"] += 1
            arret.set()          # l'utilisateur annule pendant l'analyse
            raise yt_dlp.utils.DownloadError(DNS_RAW)

        monkeypatch.setattr(Downloader, "_extract_info", _extract)
        with pytest.raises(DownloadError):
            self.telechargeur(tmp_path).fetch_info("x", "https://a/1",
                                                   stop_event=arret)
        assert etat["appels"] == 1, "aucune nouvelle tentative apres annulation"


class TestImageVerrouillee:
    """M6 : les six qualites video du manifeste sont chiffrees, deux pistes
    audio de 96 kbit/s restent lisibles. yt-dlp ecarte les formats proteges
    puis prend « le meilleur disponible » — le son. Signale par Veronique le
    2026-08-27 : tous ses programmes M6 arrivaient en .m4a, sans avertissement.
    """

    def test_detecte_l_image_verrouillee(self):
        m6 = {"_has_drm": True,
              "formats": [{"vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a"},
                          {"vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a"}]}
        assert video_is_drm_locked(m6)

    def test_un_podcast_reste_telechargeable(self):
        """Un media audio par nature n'a pas d'image non plus : se fier a la
        seule absence d'image casserait les podcasts et SoundCloud."""
        assert not video_is_drm_locked(
            {"formats": [{"vcodec": "none", "acodec": "mp3"}]})

    def test_video_partiellement_protegee_passe(self):
        """Si une qualite lisible subsiste, on telecharge au lieu de refuser."""
        assert not video_is_drm_locked(
            {"_has_drm": True,
             "formats": [{"vcodec": "avc1.64001F"}, {"vcodec": "none"}]})

    def test_sans_information_on_ne_pretend_rien(self):
        assert not video_is_drm_locked({})

    def test_tout_est_protege(self):
        """Plus rien n'a survecu au verrou : meme diagnostic."""
        assert video_is_drm_locked({"_has_drm": True, "formats": []})

    def test_le_son_demande_explicitement_reste_telechargeable(self):
        """Veronique, 2026-08-28 : elle veut ses emissions M6 « meme en audio ».
        Refuser un MP3 demande expressement lui retirerait le seul acces qui
        reste — le garde-fou ne vise que la demande de VIDEO."""
        assert accepts_audio_only("mp3")
        assert accepts_audio_only("m4a")
        assert accepts_audio_only("amc_audio")
        assert accepts_audio_only("subtitles_only")

    def test_un_format_choisi_dans_la_liste_passe_aussi(self):
        """Choisir soi-meme un format = aucune surprise possible."""
        assert accepts_audio_only("manual", "audio-96k")

    def test_une_demande_de_video_reste_protegee(self):
        assert not accepts_audio_only("auto")
        assert not accepts_audio_only("mp4")
        assert not accepts_audio_only("manual", None)

    def test_message_explique_le_fichier_audio(self):
        """L'utilisateur a deja recu des .m4a : le message doit faire le lien,
        pas seulement dire « impossible »."""
        message = drm_locked_video_message()
        assert "DRM" in message
        assert "bande-son" in message
        assert "M6" in message

    def test_message_indique_la_sortie_de_secours(self):
        """Sans cette phrase, l'utilisateur croit l'emission hors de portee
        alors que le son, lui, se telecharge."""
        message = drm_locked_video_message()
        assert "MP3" in message and "M4A" in message

    def test_message_dit_ou_se_choisit_le_format(self):
        """Seb, 2026-08-28 : il a lu « choisissez le format MP3 » et l'a change
        dans les Preferences — le telechargement deja refuse ne repart pas pour
        autant. Le message doit designer la fenetre d'ajout, et dire que
        changer la preference ne relance pas celui-ci."""
        message = drm_locked_video_message()
        assert "Format de téléchargement" in message
        assert "Préférences" in message and "relance pas" in message


class TestErreurSansIssue:
    """Ce qu'on ne relance jamais.

    La relance de diagnostic du rapport d'erreur rejouait TOUT, y compris ce
    qu'aucune nouvelle tentative ne peut resoudre. Sur une video dont seule la
    bande-son a echappe au verrou, elle contournait le garde-fou (pose a
    l'analyse, pas au telechargement) : Seb recevait le .m4a que ce garde-fou
    existe pour eviter, et le rapport annoncait « le fichier est complet ».
    """

    def test_image_verrouillee_jamais_relancee(self):
        assert is_hopeless_error(drm_locked_video_message())
        assert is_hopeless_error(DRM_RAW)

    def test_disque_plein_jamais_relance(self):
        assert is_hopeless_error(DISK_FULL_RAW)

    def test_une_coupure_reseau_se_relance(self):
        """L'inverse : la relance a du sens et recupere souvent le fichier."""
        assert not is_hopeless_error("ERROR: unable to download video data: "
                                     "Read timed out")
        assert not is_hopeless_error("HTTP Error 403: Forbidden")
