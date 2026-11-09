"""La file reprise au lancement doit se voir (rapport de Brad, 2026-11-09, 0.2.6).

De 0.2.3 a 0.2.6, `restore_queue_at_startup` remettait les telechargements
dans la file sans creer leur ligne : ils tournaient en silence, et NVDA lisait
« Aucun telechargement pour le moment ». Brad rajoutait alors ses playlists,
d'ou des doublons et une rafale de requetes vers YouTube.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core import queue_store
from app.core.queue_manager import QueueManager
from app.core.settings import DEFAULTS
from app.ui.download_list import DownloadList
from app.ui.main_window import MainWindow


class FausseFenetre:
    """Les vraies methodes de reprise autour d'une vraie DownloadList et
    d'une vraie QueueManager (sans telechargement)."""

    def __init__(self, parent):
        self.settings = dict(DEFAULTS)
        self.lbl_empty = wx.TextCtrl(parent, style=wx.TE_READONLY)
        self.download_list = DownloadList(parent)
        self._queue = QueueManager(self.settings, lambda f, *a: None,
                                   *(lambda *a: None for _ in range(4)))
        self._queue._try_start_next = lambda: None
        self._dl_data = {}
        self.statuts = []
        self.compte = None

    def set_status(self, message):
        self.statuts.append(message)

    def set_count(self, n):
        self.compte = n

    def titres(self):
        liste = self.download_list
        return [liste.GetItemText(i, 0) for i in range(liste.GetItemCount())]

    restore_queue_at_startup = MainWindow.restore_queue_at_startup
    _initial_focus           = MainWindow._initial_focus
    _format_label            = staticmethod(MainWindow._format_label)


@pytest.fixture
def file_conservee(monkeypatch):
    entrees = [{"url": "https://a/1", "format_spec": "mp3",
                "playlist_title": "Ma liste", "playlist_number": 1},
               {"url": "https://a/2"}]
    monkeypatch.setattr(queue_store, "load", lambda: [dict(e) for e in entrees])
    monkeypatch.setattr(queue_store, "clear", lambda: None)
    return entrees


class TestRepriseVisible:
    def test_chaque_telechargement_repris_a_sa_ligne(self, frame, file_conservee):
        f = FausseFenetre(frame)
        f.restore_queue_at_startup()
        assert f.titres() == ["https://a/1", "https://a/2"]
        assert f.compte == 2, "le message de liste vide doit ceder la place"
        ids = f.download_list.get_all_ids()
        assert ids == [i.download_id for i in f._queue._queue]

    def test_relance_et_rapport_retrouvent_leurs_donnees(self, frame, file_conservee):
        f = FausseFenetre(frame)
        f.restore_queue_at_startup()
        premier = f.download_list.get_all_ids()[0]
        assert f._dl_data[premier]["url"] == "https://a/1"
        assert f._dl_data[premier]["format_spec"] == "mp3"
        assert f._dl_data[premier]["playlist_title"] == "Ma liste"

    def test_reprise_desactivee_rien_n_apparait(self, frame, file_conservee):
        f = FausseFenetre(frame)
        f.settings["resume_queue_on_start"] = False
        f.restore_queue_at_startup()
        assert f.titres() == [] and f.compte is None


class TestFocusInitial:
    def test_sur_la_liste_quand_la_file_a_repris(self, frame, file_conservee):
        f = FausseFenetre(frame)
        f.restore_queue_at_startup()
        f._initial_focus()
        assert f.download_list.get_selected_ids() == [f.download_list.get_all_ids()[0]]

    def test_sur_le_message_quand_la_liste_est_vide(self, frame):
        f = FausseFenetre(frame)
        f._initial_focus()
        assert f.download_list.get_selected_ids() == []
