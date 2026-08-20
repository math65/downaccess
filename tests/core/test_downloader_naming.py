"""Timecodes, noms de fichiers et estimation de taille."""

import pytest

from app.core.downloader import (
    _domain_from_url,
    _fmt_size,
    _normalize_youtube_channel_url,
    _sanitize_dirname,
    _should_use_cookies,
    _target_ext,
    _timecode_for_filename,
    estimate_total_bytes,
    format_timecode,
    parse_timecode,
)


class TestTimecodes:
    @pytest.mark.parametrize("texte,secondes", [
        ("0", 0),
        ("42", 42),
        ("4:20", 260),
        ("1:05:30", 3930),
        ("00:00:05", 5),
        (" 2:00 ", 120),
        ("1:30,5", 90.5),
    ])
    def test_lecture(self, texte, secondes):
        assert parse_timecode(texte) == pytest.approx(secondes)

    @pytest.mark.parametrize("texte", [
        "", "   ", "bidule", "1:2:3:4", "::", "1::30", "-5",
    ])
    def test_refuse_ce_qui_n_est_pas_un_moment(self, texte):
        with pytest.raises(ValueError):
            parse_timecode(texte)

    @pytest.mark.parametrize("secondes,attendu", [
        (0, "0:00"),
        (65, "1:05"),
        (260, "4:20"),
        (3930, "1:05:30"),
        (3600, "1:00:00"),
    ])
    def test_ecriture(self, secondes, attendu):
        assert format_timecode(secondes) == attendu

    def test_aller_retour(self):
        for secondes in (0, 7, 61, 599, 3661, 86399):
            assert parse_timecode(format_timecode(secondes)) == secondes

    def test_nom_de_fichier_sans_deux_points(self):
        """Windows interdit « : » dans un nom de fichier."""
        assert ":" not in _timecode_for_filename(3930)
        assert _timecode_for_filename(3930) == "1-05-30"

    def test_extrait_sans_fin_se_lit_fin(self):
        assert _timecode_for_filename(float("inf")) == "fin"


class TestNomsDeDossier:
    @pytest.mark.parametrize("brut,attendu", [
        ("Ma playlist", "Ma playlist"),
        (r'a/b\c:d*e?f"g<h>i|j', "a_b_c_d_e_f_g_h_i_j"),
        ("  espaces  ", "espaces"),
        ("...", "Playlist"),
        ("", "Playlist"),
    ])
    def test_nettoyage(self, brut, attendu):
        assert _sanitize_dirname(brut) == attendu


class TestTailleLisible:
    @pytest.mark.parametrize("octets,attendu", [
        (0, "0 Ko"),
        (2048, "2 Ko"),
        (1_048_576, "1 Mo"),
        (41_000_000, "39 Mo"),
        (2_360_000_000, "2.2 Go"),
    ])
    def test_formatage(self, octets, attendu):
        assert _fmt_size(octets) == attendu

    def test_valeur_negative_ne_casse_pas(self):
        assert _fmt_size(-1) == "0 Ko"


class TestExtensionCible:
    @pytest.mark.parametrize("spec,attendu", [
        ("mp3", "mp3"),
        ("m4a", "m4a"),
        ("mp4", "mp4"),
        ("auto", ""),            # le conteneur depend de la fusion
        ("amc_audio", ""),
        ("amc_video", ""),
        ("subtitles_only", ""),
    ])
    def test_connue_seulement_quand_c_est_certain(self, spec, attendu):
        assert _target_ext(spec, None) == attendu

    def test_format_manuel_reste_inconnu(self):
        """Regression : poser une pochette sur un conteneur inconnu ferait
        echouer un telechargement pourtant reussi."""
        assert _target_ext("mp4", "137+140") == ""


class TestEstimationTaille:
    def test_video_plus_audio(self):
        formats = [
            {"vcodec": "avc1", "acodec": "none", "filesize": 1000},
            {"vcodec": "none", "acodec": "mp4a", "filesize": 100},
        ]
        assert estimate_total_bytes(formats, "auto") == 1100

    def test_audio_seul_ne_compte_que_l_audio(self):
        formats = [
            {"vcodec": "avc1", "acodec": "none", "filesize": 1000},
            {"vcodec": "none", "acodec": "mp4a", "filesize": 100},
        ]
        assert estimate_total_bytes(formats, "mp3") == 100

    def test_repli_sur_debit_fois_duree(self):
        """france.tv n'annonce aucun filesize : sans ce repli la barre reste plate."""
        formats = [{"vcodec": "none", "acodec": "mp4a", "tbr": 128}]
        estime = estimate_total_bytes(formats, "mp3", duration=60)
        assert estime == pytest.approx(128 * 1000 / 8 * 60, rel=0.01)

    def test_sans_format_retourne_zero(self):
        assert estimate_total_bytes([], "auto") == 0


class TestUrlsYouTube:
    @pytest.mark.parametrize("url,attendu", [
        # Playlist « envois » auto-generee -> onglet Videos de la chaine
        ("https://www.youtube.com/playlist?list=UUabcdefghijklmnopqrstuv",
         "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv/videos"),
        # Chaine nue -> ajout de /videos
        ("https://www.youtube.com/@arte", "https://www.youtube.com/@arte/videos"),
        ("https://www.youtube.com/channel/UCabc", "https://www.youtube.com/channel/UCabc/videos"),
        ("https://www.youtube.com/user/quelquun", "https://www.youtube.com/user/quelquun/videos"),
    ])
    def test_reecrit_vers_l_onglet_videos(self, url, attendu):
        assert _normalize_youtube_channel_url(url) == attendu

    @pytest.mark.parametrize("url", [
        # Playlist curee : la reecrire perdrait le contenu demande
        "https://www.youtube.com/playlist?list=PLabcdef",
        # Onglet deja specifique
        "https://www.youtube.com/@arte/videos",
        # Autre site
        "https://vimeo.com/12345",
        # Video simple
        "https://www.youtube.com/watch?v=abc123",
    ])
    def test_laisse_le_reste_intact(self, url):
        assert _normalize_youtube_channel_url(url) == url


class TestDomainesEtCookies:
    @pytest.mark.parametrize("url,domaine", [
        ("https://www.youtube.com/watch?v=x", "youtube.com"),
        ("https://WWW.Arte.TV/fr/", "arte.tv"),
        ("https://sub.example.org/a", "sub.example.org"),
    ])
    def test_domaine(self, url, domaine):
        assert _domain_from_url(url) == domaine

    def test_cookies_par_site(self):
        settings = {"cookie_sites": ["youtube.com"]}
        assert _should_use_cookies(settings, "https://www.youtube.com/watch?v=x")
        assert _should_use_cookies(settings, "https://music.youtube.com/watch?v=x")
        assert not _should_use_cookies(settings, "https://vimeo.com/1")

    def test_liste_vide(self):
        assert not _should_use_cookies({"cookie_sites": []}, "https://youtube.com/x")
