"""Le raccourci propose quand seule la bande-son est accessible.

Sur une emission M6, DownAccess refuse la video et explique qu'il faut
reajouter le lien en MP3. Deux testeurs sont alles changer le format dans les
Preferences a la place — ce qui ne relance pas le telechargement deja refuse.
Le dialogue d'erreur propose donc l'action sur place (2026-08-28).
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.downloader import drm_locked_video_message
from app.core.settings import DEFAULTS
from app.ui.error_dialog import ErrorDialog
from app.ui.main_window import MainWindow

NETFLIX = ("Cette video est protegee contre la copie (DRM).\n\n"
           "DownAccess ne peut pas la telecharger.")


class TestBoutonDuDialogue:

    def test_absent_par_defaut(self, frame):
        """Une panne reseau n'a pas de repli audio a proposer."""
        dlg = ErrorDialog(frame, "Read timed out")
        assert dlg.btn_audio is None
        dlg.Destroy()

    def test_present_a_la_demande_et_etiquete(self, frame):
        dlg = ErrorDialog(frame, drm_locked_video_message(), audio_offer=True)
        assert dlg.btn_audio is not None
        assert dlg.btn_audio.GetLabel() and dlg.btn_audio.GetName()
        dlg.Destroy()

    def test_le_focus_ne_se_pose_pas_sur_lui(self, frame):
        """Regle du projet : le focus n'arrive pas sur un bouton d'action."""
        dlg = ErrorDialog(frame, drm_locked_video_message(), audio_offer=True)
        assert dlg.FindFocus() is dlg.btn_close
        dlg.Destroy()


class FausseListe:
    def __init__(self):
        self.en_erreur = []
        self.retires = []

    def error_item(self, dl_id):
        self.en_erreur.append(dl_id)

    def remove_item(self, dl_id):
        self.retires.append(dl_id)

    def count(self):
        return 0

    def SetFocus(self):
        pass


class FausseFile:
    """File deja vide : un seul echec, pas de rafale."""
    is_idle = True


class FausseFenetre:
    def __init__(self):
        self.settings = dict(DEFAULTS)
        self.download_list = FausseListe()
        self._progress = {}
        self._gauge_dl_id = None
        self._dl_data = {"d1": {"url": "https://www.m6.fr/emission",
                                "format_spec": "auto"}}
        self.enfilees = []
        self.rapports = []
        self.statuts = []
        self._error_bursts = {}
        self._queue = FausseFile()

    def set_status(self, message):
        self.statuts.append(message)

    def set_count(self, n):
        pass

    def _log_history(self, *a, **kw):
        pass

    def _enqueue_url(self, url, format_spec="auto", **kw):
        self.enfilees.append((url, format_spec))

    def _start_error_report(self, dl_id, message):
        self.rapports.append(dl_id)

    # La relance elle-meme est celle de l'application : c'est elle qu'on teste.
    _redownload_as_audio = MainWindow._redownload_as_audio

    # Le garde-fou des erreurs en rafale est traverse a chaque echec : c'est
    # celui de l'application, pas une imitation.
    _claim_error_dialog      = MainWindow._claim_error_dialog
    _error_burst_key         = MainWindow._error_burst_key
    _reset_error_bursts_if_idle = MainWindow._reset_error_bursts_if_idle
    # `staticmethod` : sans le rehabiller, `self` partirait comme URL.
    _site_label              = staticmethod(MainWindow._site_label)


def afficher(monkeypatch, message, clic="close"):
    """Rejoue l'arrivee d'une erreur, avec le bouton eventuellement clique."""
    from app.ui import main_window as mw

    vu = {}

    class FauxDialogue:
        def __init__(self, parent, message, audio_offer=False):
            vu["audio_offer"] = audio_offer

        def ShowModal(self):
            return wx.ID_OK

        def wants_audio(self):
            return clic == "audio"

        def wants_report(self):
            return clic == "report"

        def Destroy(self):
            pass

    monkeypatch.setattr(mw, "ErrorDialog", FauxDialogue)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **kw: fn(*a, **kw))
    faux = FausseFenetre()
    MainWindow._on_dl_error(faux, "d1", message)
    return faux, vu["audio_offer"]


class TestOffreDansLaFenetreDErreur:

    def test_proposee_quand_seul_le_son_est_accessible(self, monkeypatch):
        _faux, offre = afficher(monkeypatch, drm_locked_video_message())
        assert offre is True

    def test_pas_proposee_sur_une_autre_erreur(self, monkeypatch):
        _faux, offre = afficher(monkeypatch, "HTTP Error 403: Forbidden")
        assert offre is False

    def test_pas_proposee_quand_rien_nest_accessible(self, monkeypatch):
        """Netflix : ni image ni son. Proposer le son ne menerait qu'a un
        second echec."""
        _faux, offre = afficher(monkeypatch, NETFLIX)
        assert offre is False

    def test_le_clic_relance_en_mp3(self, monkeypatch):
        faux, _o = afficher(monkeypatch, drm_locked_video_message(), clic="audio")
        assert faux.enfilees == [("https://www.m6.fr/emission", "mp3")]
        assert faux.download_list.retires == ["d1"], (
            "l'item echoue laisse la place a la relance")
        assert faux.rapports == []

    def test_le_rapport_reste_possible(self, monkeypatch):
        faux, _o = afficher(monkeypatch, drm_locked_video_message(), clic="report")
        assert faux.rapports == ["d1"]
        assert faux.enfilees == []

    def test_fermer_ne_fait_rien(self, monkeypatch):
        faux, _o = afficher(monkeypatch, drm_locked_video_message())
        assert faux.enfilees == [] and faux.rapports == []
