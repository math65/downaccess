"""Construction des options yt-dlp : format, sous-titres, metadonnees.

Ce sont ces dictionnaires qui decident de ce qui est reellement telecharge.
Les tester revient a verifier le comportement du telechargeur sans reseau.
"""

import pytest

from app.core.downloader import (
    _apply_format,
    _apply_metadata,
    _apply_subtitles,
    _looks_already_present,
)


def keys_of(opts):
    return [pp["key"] for pp in opts.get("postprocessors", [])]


class TestFormats:
    def test_auto_prend_le_meilleur(self):
        opts = {}
        _apply_format(opts, "auto")
        assert opts["format"] == "bestvideo+bestaudio/best"
        assert "postprocessors" not in opts

    def test_mp3_extrait_l_audio(self):
        opts = {}
        _apply_format(opts, "mp3")
        assert keys_of(opts) == ["FFmpegExtractAudio"]
        assert opts["postprocessors"][0]["preferredcodec"] == "mp3"

    def test_m4a_extrait_l_audio(self):
        opts = {}
        _apply_format(opts, "m4a")
        assert opts["postprocessors"][0]["preferredcodec"] == "m4a"

    def test_mp4_convertit_la_video(self):
        opts = {}
        _apply_format(opts, "mp4")
        assert keys_of(opts) == ["FFmpegVideoConvertor"]

    def test_format_manuel_ne_pose_aucun_traitement(self):
        opts = {}
        _apply_format(opts, "manual", format_id="137+140")
        assert opts["format"] == "137+140"
        assert "postprocessors" not in opts

    def test_amc_ne_reencode_pas(self):
        """La passerelle vers Access Media Converter passe l'original :
        reencoder ici couterait une seconde perte de qualite."""
        for spec in ("amc_audio", "amc_video"):
            opts = {}
            _apply_format(opts, spec)
            assert "postprocessors" not in opts

    def test_pistes_audio_multiples_autorisees(self):
        opts = {}
        _apply_format(opts, "auto", audio_groups=[["fr-1", "fr-2"], ["ad-1"]])
        assert opts["allow_multiple_audio_streams"] is True
        assert "(fr-1/fr-2)+(ad-1)" in opts["format"]

    def test_une_seule_piste_ne_declenche_pas_le_multiflux(self):
        opts = {}
        _apply_format(opts, "auto", audio_groups=[["fr-1", "fr-2"]])
        assert "allow_multiple_audio_streams" not in opts


class TestSousTitres:
    def test_desactives_par_defaut(self):
        opts = {}
        _apply_subtitles(opts, {"auto_subtitles": False})
        assert opts == {}

    def test_fichier_separe(self):
        opts = {}
        _apply_subtitles(opts, {"auto_subtitles": True, "subtitle_langs": ["fr"],
                                "subtitle_format": "srt", "subtitle_mode": "separate"})
        assert opts["writesubtitles"] is True
        assert opts["writeautomaticsub"] is True
        assert opts["subtitleslangs"] == ["fr"]
        assert keys_of(opts) == ["FFmpegSubtitlesConvertor"]

    def test_incrustation_dans_le_conteneur(self):
        opts = {}
        _apply_subtitles(opts, {"auto_subtitles": True, "subtitle_format": "srt",
                                "subtitle_mode": "embed"})
        assert "FFmpegEmbedSubtitle" in keys_of(opts)

    def test_format_original_evite_la_conversion(self):
        opts = {}
        _apply_subtitles(opts, {"auto_subtitles": True, "subtitle_format": "original",
                                "subtitle_mode": "separate"})
        assert "subtitlesformat" not in opts
        assert keys_of(opts) == []


class TestMetadonnees:
    def test_actives_par_defaut(self):
        opts = {}
        embed, ext = _apply_metadata(opts, {}, "mp3", None)
        assert "FFmpegMetadata" in keys_of(opts)
        assert embed is True
        assert ext == "mp3"

    def test_reglage_decoche_ne_touche_a_rien(self):
        opts = {}
        embed, _ext = _apply_metadata(opts, {"embed_metadata": False}, "mp3", None)
        assert opts == {}
        assert embed is False

    def test_chapitres_toujours_demandes(self):
        """Les reperes de chapitres sont precieux sur les longs formats."""
        opts = {}
        _apply_metadata(opts, {}, "mp3", None)
        meta = next(pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegMetadata")
        assert meta["add_chapters"] is True
        assert meta["add_infojson"] is False

    @pytest.mark.parametrize("spec", ["mp3", "m4a", "mp4"])
    def test_pochette_sur_conteneur_sur(self, spec):
        opts = {}
        embed, _ext = _apply_metadata(opts, {}, spec, None)
        assert embed is True
        assert opts["writethumbnail"] is True

    @pytest.mark.parametrize("spec", ["auto", "amc_audio", "amc_video"])
    def test_pas_de_pochette_si_le_conteneur_est_incertain(self, spec):
        """Regression : en « auto » la fusion peut produire du webm, que
        yt-dlp refuse d'illustrer — et l'erreur ferait echouer le
        telechargement. On ecrit alors les metadonnees seules."""
        opts = {}
        embed, _ext = _apply_metadata(opts, {}, spec, None)
        assert embed is False
        assert "writethumbnail" not in opts
        assert "FFmpegMetadata" in keys_of(opts)

    def test_sous_titres_seuls_n_ecrivent_rien(self):
        opts = {"skip_download": True}
        embed, _ext = _apply_metadata(opts, {}, "subtitles_only", None)
        assert embed is False
        assert "postprocessors" not in opts

    def test_ordre_conversion_puis_metadonnees(self):
        """ffmpeg ecrit les tags dans le fichier final : les metadonnees
        doivent passer APRES l'extraction audio, jamais avant."""
        opts = {}
        _apply_format(opts, "mp3")
        _apply_subtitles(opts, {"auto_subtitles": False})
        _apply_metadata(opts, {}, "mp3", None)
        assert keys_of(opts) == ["FFmpegExtractAudio", "FFmpegMetadata"]


class TestFichierDejaPresent:
    """Regression : tout extrait etait annonce « Deja telecharge ».

    Un extrait passe par ffmpeg (force_keyframes_at_cuts), qui n'emet aucun
    evenement 'downloading' — seulement 'finished'. L'heuristique « finished
    sans downloading = fichier deja la » se declenchait donc a chaque extrait,
    meme dans un dossier vide : l'utilisateur lisait « Deja telecharge » alors
    que le fichier venait d'etre cree.
    """

    def cas(self, **kw):
        base = {"skip_download": False, "format_spec": "mp3", "section": None,
                "completed": 1, "any_download": False}
        base.update(kw)
        return _looks_already_present(**base)

    def test_finished_sans_octet_recu_signale_un_fichier_deja_la(self):
        assert self.cas() is True

    def test_un_extrait_n_est_jamais_deja_present(self):
        assert self.cas(section=(5.0, 12.0)) is False

    def test_un_extrait_reste_honnete_meme_sans_octet_compte(self):
        assert self.cas(section=(0.0, 7.0), completed=3) is False

    def test_des_octets_recus_excluent_le_fichier_deja_la(self):
        assert self.cas(any_download=True) is False

    def test_aucun_fichier_termine_exclut_le_fichier_deja_la(self):
        assert self.cas(completed=0) is False

    def test_sous_titres_seuls_ne_sont_pas_concernes(self):
        assert self.cas(format_spec="subtitles_only") is False

    def test_sans_telechargement_rien_a_signaler(self):
        assert self.cas(skip_download=True) is False
