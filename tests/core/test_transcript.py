"""Nettoyage des sous-titres en texte lisible."""

import pytest

from app.core.transcript import (
    TranscriptError,
    _language_of,
    _pick_subtitle_file,
    fetch_transcript,
    parse_subtitles,
)

VTT_AUTO = """WEBVTT
Kind: captions
Language: fr

00:00:00.030 --> 00:00:02.669 align:start position:0%
bonjour<00:00:00.630><c> a</c><00:00:01.020><c> tous</c>

00:00:02.669 --> 00:00:02.679 align:start position:0%
bonjour a tous

00:00:02.679 --> 00:00:05.099 align:start position:0%
bonjour a tous et bienvenue

00:00:05.099 --> 00:00:07.000
dans cette &amp; nouvelle video
"""

SRT = """1
00:00:01,000 --> 00:00:04,000
<i>Premiere ligne</i>

2
00:00:04,000 --> 00:00:06,500
Deuxieme ligne
"""


class TestNettoyage:
    def test_supprime_l_appareillage_technique(self):
        texte = parse_subtitles(VTT_AUTO)
        assert "WEBVTT" not in texte
        assert "-->" not in texte
        assert "00:00" not in texte
        assert "<c>" not in texte
        assert "align:start" not in texte

    def test_deduplique_la_fenetre_glissante(self):
        """Les sous-titres automatiques de YouTube repetent chaque bribe en la
        rallongeant. Sans deduplication, le texte serait illisible."""
        texte = parse_subtitles(VTT_AUTO)
        assert texte.count("bonjour") == 1
        assert texte.startswith("bonjour a tous et bienvenue")

    def test_decode_les_entites(self):
        assert "&" in parse_subtitles(VTT_AUTO)
        assert "&amp;" not in parse_subtitles(VTT_AUTO)

    def test_srt_index_et_balises(self):
        texte = parse_subtitles(SRT)
        assert texte == "Premiere ligne Deuxieme ligne"

    def test_document_vide(self):
        assert parse_subtitles("WEBVTT\n\n") == ""
        assert parse_subtitles("") == ""

    def test_repetition_exacte_ecartee(self):
        doublon = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nmeme ligne\n\n" \
                  "00:00:02.000 --> 00:00:03.000\nmeme ligne\n"
        assert parse_subtitles(doublon) == "meme ligne"

    def test_reflow_en_paragraphes(self):
        """Des bribes de trois mots par ligne se lisent de facon hachee au
        lecteur d'ecran : on recolle en paragraphes."""
        long_vtt = "WEBVTT\n\n" + "".join(
            f"00:00:{i:02d}.000 --> 00:00:{i + 1:02d}.000\nmot{i} bla bla bla bla\n\n"
            for i in range(60))
        texte = parse_subtitles(long_vtt)
        paragraphes = texte.split("\n\n")
        assert len(paragraphes) > 1
        # Aucun paragraphe demesure
        assert all(len(p) < 600 for p in paragraphes)


class TestChoixDeLangue:
    def test_prefere_la_premiere_langue_demandee(self, tmp_path):
        (tmp_path / "video.en.vtt").write_text("x", encoding="utf-8")
        (tmp_path / "video.fr.vtt").write_text("x", encoding="utf-8")
        choisi = _pick_subtitle_file(str(tmp_path), ["fr", "en"])
        assert choisi.endswith("video.fr.vtt")

    def test_variante_regionale_acceptee(self, tmp_path):
        (tmp_path / "video.en-US.vtt").write_text("x", encoding="utf-8")
        assert _pick_subtitle_file(str(tmp_path), ["en"]).endswith("en-US.vtt")

    def test_repli_sur_ce_qui_existe(self, tmp_path):
        (tmp_path / "video.de.vtt").write_text("x", encoding="utf-8")
        assert _pick_subtitle_file(str(tmp_path), ["fr", "en"]).endswith("de.vtt")

    def test_aucun_fichier(self, tmp_path):
        assert _pick_subtitle_file(str(tmp_path), ["fr"]) == ""

    def test_code_de_langue(self):
        assert _language_of("/a/b/video.fr.vtt") == "fr"
        assert _language_of("/a/b/video.vtt") == ""


class TestRecuperation:
    def test_langue_en_echec_n_annule_pas_les_autres(self, monkeypatch, tmp_path):
        """Regression mesuree : yt-dlp abandonne des qu'UNE langue echoue (429
        de YouTube) alors qu'une autre est deja ecrite sur le disque. Il faut
        regarder le disque avant de declarer forfait."""
        import yt_dlp

        from app.core import transcript

        class FauxYdl:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def download(self, urls):
                dossier = tmp_path
                (dossier / "video.fr.vtt").write_text(SRT, encoding="utf-8")
                raise yt_dlp.utils.DownloadError(
                    "Unable to download video subtitles for 'en': HTTP Error 429")

        monkeypatch.setattr(transcript.yt_dlp, "YoutubeDL", FauxYdl)
        monkeypatch.setattr(transcript.tempfile, "TemporaryDirectory",
                            lambda **kw: _DossierFixe(tmp_path))

        texte, langue = fetch_transcript({}, "https://exemple.org/v")
        assert "Premiere ligne" in texte
        assert langue == "fr"

    def test_aucun_sous_titre(self, monkeypatch, tmp_path):
        from app.core import transcript

        class FauxYdl:
            def __init__(self, opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def download(self, urls):
                return None

        monkeypatch.setattr(transcript.yt_dlp, "YoutubeDL", FauxYdl)
        monkeypatch.setattr(transcript.tempfile, "TemporaryDirectory",
                            lambda **kw: _DossierFixe(tmp_path))
        with pytest.raises(TranscriptError):
            fetch_transcript({}, "https://exemple.org/v")


class _DossierFixe:
    """Remplace tempfile.TemporaryDirectory par un dossier qu'on inspecte."""

    def __init__(self, path):
        self.path = str(path)

    def __enter__(self):
        return self.path

    def __exit__(self, *a):
        return False
