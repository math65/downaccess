"""Faire le menage dans la liste (demande de Brad, 2026-09-13, sur 0.2.3).

Brad enchaine des files de plus de mille videos. Il demandait Ctrl+A puis
Suppr, une commande pour retirer d'un coup les telechargements termines, et
une option pour qu'ils disparaissent seuls. Pause (Espace) et Reessayer (F2)
agissent aussi sur toute la selection : Ctrl+A puis F2 relance tous les echecs.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.settings import DEFAULTS
from app.ui.download_list import (
    DownloadList, STATUS_ACTIVE, STATUS_ALREADY, STATUS_DONE, STATUS_ERROR,
    STATUS_PAUSED, STATUS_PENDING,
)
from app.ui.main_window import MainWindow


class FausseFile:
    def __init__(self, actifs=()):
        self.actifs = set(actifs)
        self.en_pause = set()
        self.annules = []

    def is_active(self, dl_id):
        return dl_id in self.actifs

    def is_paused(self, dl_id):
        return dl_id in self.en_pause

    def pause(self, dl_id):
        self.en_pause.add(dl_id)

    def resume(self, dl_id):
        self.en_pause.discard(dl_id)

    def cancel(self, dl_id):
        self.annules.append(dl_id)


class FausseFenetre:
    """Les vraies methodes de MainWindow autour d'une vraie DownloadList."""

    def __init__(self, parent, statuts: dict[str, str], actifs=()):
        self.settings = dict(DEFAULTS)
        self.download_list = DownloadList(parent)
        for dl_id, code in statuts.items():
            self.download_list.add_item(dl_id, f"Titre {dl_id}", "test")
            self.download_list.set_status(dl_id, code)
        self._queue = FausseFile(actifs)
        self._dl_data = {i: {"url": f"https://a/{i}"} for i in statuts}
        self._progress = {}
        self._gauge_dl_id = None
        self.relances = []
        self.statuts = []
        self.dossier_ouvert = False

    def set_status(self, message):
        self.statuts.append(message)

    def set_count(self, n):
        pass

    def _reset_gauge(self):
        self._gauge_dl_id = None

    def _enqueue_url(self, url, *a, **kw):
        self.relances.append(url)

    def titres(self):
        liste = self.download_list
        return [liste.GetItemText(i, 0) for i in range(liste.GetItemCount())]

    def selectionner(self, *ids):
        liste = self.download_list
        liste._select_only(liste._items[ids[0]])
        for dl_id in ids[1:]:
            liste.Select(liste._items[dl_id])

    # `_on_dl_complete` et ses dependances
    def _clear_error_burst_for_site(self, url):
        pass

    def _announce_download(self, *a, **kw):
        pass

    def _maybe_handoff_to_amc(self, data):
        pass

    def _log_history(self, *a, **kw):
        pass

    def _open_download_folder(self):
        self.dossier_ouvert = True

    _UNFINISHED       = MainWindow._UNFINISHED
    _on_cancel        = MainWindow._on_cancel
    _on_pause         = MainWindow._on_pause
    _pause_many       = MainWindow._pause_many
    _on_retry         = MainWindow._on_retry
    _retry_one        = MainWindow._retry_one
    _forget_items     = MainWindow._forget_items
    _on_clear_done    = MainWindow._on_clear_done
    _on_dl_complete   = MainWindow._on_dl_complete
    _all_done         = MainWindow._all_done


@pytest.fixture(autouse=True)
def oui_a_tout(monkeypatch):
    questions = []

    def repondre(message, *a, **kw):
        questions.append(message)
        return wx.YES

    monkeypatch.setattr(wx, "MessageBox", repondre)
    return questions


class TestListe:
    def test_tout_selectionner(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_ERROR, "c": STATUS_PENDING})
        assert f.download_list.select_all() == 3
        assert f.download_list.get_selected_ids() == ["a", "b", "c"]

    def test_retrait_de_lignes_non_contigues(self, frame):
        f = FausseFenetre(frame, dict.fromkeys("abcde", STATUS_DONE))
        f.download_list.remove_ids(["b", "d"])
        assert f.titres() == ["Titre a", "Titre c", "Titre e"]
        # La correspondance id -> ligne reste juste apres les decalages.
        f.download_list.remove_ids(["e"])
        assert f.titres() == ["Titre a", "Titre c"]


class TestSuppr:
    def test_n_annule_que_ce_qui_tourne(self, frame, oui_a_tout):
        f = FausseFenetre(frame, {"fini": STATUS_DONE, "encours": STATUS_ACTIVE,
                                  "pause": STATUS_PAUSED, "echec": STATUS_ERROR})
        f.download_list.select_all()
        f._on_cancel(None)
        assert sorted(f._queue.annules) == ["encours", "pause"]
        assert len(oui_a_tout) == 1            # une seule confirmation
        assert f.titres() == []

    def test_sans_rien_en_cours_pas_de_question(self, frame, oui_a_tout):
        f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_ERROR})
        f.download_list.select_all()
        f._on_cancel(None)
        assert oui_a_tout == [] and f.titres() == []


class TestRetirerTermines:
    def test_garde_les_echecs_et_les_en_cours(self, frame, oui_a_tout):
        f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_ERROR,
                                  "c": STATUS_ALREADY, "d": STATUS_ACTIVE})
        f._on_clear_done(None)
        assert f.titres() == ["Titre b", "Titre d"]
        assert oui_a_tout == [] and f._queue.annules == []


class TestPauseSelection:
    def test_pause_puis_reprise_de_tous(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_ACTIVE, "b": STATUS_ACTIVE,
                                  "fini": STATUS_DONE}, actifs=("a", "b"))
        f.download_list.select_all()
        f._on_pause(None)
        assert f._queue.en_pause == {"a", "b"}
        assert f.download_list.get_status("fini") == STATUS_DONE
        f._on_pause(None)
        assert f._queue.en_pause == set()

    def test_un_seul_en_cours_suffit_a_tout_mettre_en_pause(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_PAUSED, "b": STATUS_ACTIVE},
                          actifs=("a", "b"))
        f._queue.en_pause = {"a"}
        f.download_list.select_all()
        f._on_pause(None)
        assert f._queue.en_pause == {"a", "b"}


class TestReessayerSelection:
    def test_ne_relance_que_les_echecs(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_ERROR, "fini": STATUS_DONE,
                                  "b": STATUS_ERROR, "c": STATUS_ACTIVE})
        f.download_list.select_all()
        f._on_retry(None)
        assert f.relances == ["https://a/a", "https://a/b"]
        assert f.titres() == ["Titre fini", "Titre c"]

    def test_un_seul_element_comme_avant(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_ERROR})
        f.selectionner("a")
        f._on_retry(None)
        assert f.relances == ["https://a/a"]


class TestRetraitAutomatique:
    def test_desactive_par_defaut(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_ACTIVE})
        f._on_dl_complete("a")
        assert f.titres() == ["Titre a"]

    def test_retire_et_ouvre_quand_meme_le_dossier(self, frame):
        f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_ACTIVE})
        f.settings["remove_completed"] = True
        f.settings["open_folder_when_done"] = True
        f._on_dl_complete("b")
        assert f.titres() == ["Titre a"]
        assert f.dossier_ouvert


def test_un_ajout_ne_s_ajoute_pas_a_la_selection(frame):
    """add_item selectionne le nouvel element SEUL : sinon, apres une playlist,
    tout resterait selectionne et Suppr viderait la liste."""
    f = FausseFenetre(frame, {"a": STATUS_DONE, "b": STATUS_DONE, "c": STATUS_DONE})
    assert f.download_list.get_selected_ids() == ["c"]


def test_deplacer_garde_une_seule_selection(frame):
    f = FausseFenetre(frame, {"a": STATUS_PENDING, "b": STATUS_PENDING})
    f.download_list.move_item_up("b")
    assert f.download_list.get_selected_ids() == ["b"]
