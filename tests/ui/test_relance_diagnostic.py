"""La relance de diagnostic du rapport d'erreur.

Envoyer un rapport rejoue le telechargement en mode verbeux, pour capturer un
log complet. Ce rejeu contourne l'analyse — donc le garde-fou qui refuse une
video dont seule la bande-son a echappe au verrou. Sur M6, il ramenait le .m4a
que ce garde-fou existe pour eviter, et le rapport annoncait « le fichier est
complet » (Seb, 2026-08-28, 0.2.1).
"""

import threading

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.downloader import drm_locked_video_message
from app.core.settings import DEFAULTS
from app.ui.main_window import MainWindow


class FausseFenetre:
    def __init__(self):
        self.settings = dict(DEFAULTS)


def rejouer(monkeypatch, erreur, echoue=False, fichier="D:\\sortie.mp3"):
    """Appelle la relance en surveillant si un telechargement a lieu."""
    from app.ui import main_window as mw

    essais = []

    class FauxTelechargeur:
        def __init__(self, settings):
            pass

        def download(self, **kw):
            essais.append(kw)
            kw["on_verbose_log"]("log yt-dlp verbeux")
            if echoue:
                raise RuntimeError("toujours pareil")
            from app.core.downloader import DownloadProgress
            kw["on_progress"](DownloadProgress(
                download_id="diagnostic", percent=100.0, status="finished",
                filepath=fichier))

    monkeypatch.setattr(mw, "Downloader", FauxTelechargeur)
    log, recupere = MainWindow._diagnostic_rerun(
        FausseFenetre(), "https://exemple.test/a", "auto", None, None, None,
        erreur, threading.Event(), threading.Event())
    return essais, log, recupere


class TestRelanceDeDiagnostic:

    def test_image_verrouillee_rien_nest_rejoue(self, monkeypatch):
        """Le garde-fou vit a l'analyse : rejouer le telechargement seul le
        contourne et ramene la bande-son. On n'essaie donc pas."""
        essais, log, recupere = rejouer(monkeypatch, drm_locked_video_message())
        assert essais == []
        assert recupere is None, "aucun fichier ne doit etre presente comme recupere"
        assert "non tent" in log

    def test_disque_plein_rien_nest_rejoue(self, monkeypatch):
        essais, _log, recupere = rejouer(
            monkeypatch, "ERROR: unable to write data: [Errno 28] "
                         "No space left on device")
        assert essais == []
        assert recupere is None

    def test_le_log_dorigine_reste_dans_le_rapport(self, monkeypatch):
        """Ne pas rejouer ne doit pas priver le rapport de l'erreur initiale."""
        _essais, log, _r = rejouer(monkeypatch, drm_locked_video_message())
        assert "DRM" in log

    def test_une_erreur_transitoire_est_bien_rejouee(self, monkeypatch):
        """L'inverse : c'est tout l'interet de la relance, elle recupere
        souvent le fichier."""
        essais, log, recupere = rejouer(
            monkeypatch, "ERROR: unable to download video data: Read timed out")
        assert len(essais) == 1
        assert essais[0]["verbose"] is True
        assert recupere == "D:\\sortie.mp3"
        assert "log yt-dlp verbeux" in log

    def test_relance_qui_echoue_ne_pretend_rien(self, monkeypatch):
        essais, log, recupere = rejouer(
            monkeypatch, "HTTP Error 403: Forbidden", echoue=True)
        assert len(essais) == 1
        assert recupere is None
        assert log == "log yt-dlp verbeux"
