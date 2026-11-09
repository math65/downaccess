"""État de la file (Ctrl+I) et déplacement Alt+Flèche (Brad, 2026-11-09).

Brad voulait une touche pour savoir ce qui tourne, ce qui attend, et combien
de téléchargements à la fois. Et en déplaçant une vidéo avec Alt+Flèche haut,
l'ordre affiché n'était plus l'ordre réel : la liste échangeait avec la ligne
voisine, la file avec la vidéo en attente voisine.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.queue_manager import QueueManager
from app.core.settings import DEFAULTS
from app.ui.download_list import DownloadList, STATUS_DONE, STATUS_ERROR
from app.ui.main_window import MainWindow


class FausseFenetre:
    def __init__(self, parent):
        self.settings = dict(DEFAULTS)
        self.download_list = DownloadList(parent)
        self._queue = QueueManager(self.settings, lambda f, *a: None,
                                   *(lambda *a: None for _ in range(4)))
        self._queue._try_start_next = lambda: None      # rien ne demarre
        self._progress = {}

    def ajouter(self, titre, statut=None):
        """Ligne de liste ; en attente dans la file si pas de statut."""
        if statut is None:
            dl_id = self._queue.add(f"https://a/{titre}")
        else:
            dl_id = f"fini-{titre}"
        self.download_list.add_item(dl_id, titre, "test")
        if statut is not None:
            self.download_list.set_status(dl_id, statut)
        return dl_id

    def titres(self):
        liste = self.download_list
        return [liste.GetItemText(i, 0) for i in range(liste.GetItemCount())]

    def ordre_file(self):
        return [p["url"].rsplit("/", 1)[1] for p in self._queue.get_state()["pending"]]

    _on_move_up        = MainWindow._on_move_up
    _on_move_down      = MainWindow._on_move_down
    _move_in_queue     = MainWindow._move_in_queue
    _queue_status_text = MainWindow._queue_status_text


@pytest.fixture(autouse=True)
def muet(monkeypatch):
    from app.ui import main_window as mw
    monkeypatch.setattr(mw.speech, "speak", lambda *a, **kw: None)


class TestDeplacement:
    def test_la_liste_suit_l_ordre_reel_de_la_file(self, frame):
        f = FausseFenetre(frame)
        f.ajouter("p1")
        f.ajouter("fini", STATUS_DONE)          # un termine entre les deux
        p2 = f.ajouter("p2")
        f.download_list._select_only(f.download_list._items[p2])
        f._on_move_up(None)
        assert f.ordre_file() == ["p2", "p1"]
        assert f.titres() == ["p2", "fini", "p1"], \
            "les attentes de la liste doivent rester dans l'ordre de la file"
        assert f.download_list.get_selected_id() == p2

    def test_descendre(self, frame):
        f = FausseFenetre(frame)
        p1 = f.ajouter("p1")
        f.ajouter("fini", STATUS_DONE)
        f.ajouter("p2")
        f.download_list._select_only(f.download_list._items[p1])
        f._on_move_down(None)
        assert f.ordre_file() == ["p2", "p1"]
        assert f.titres() == ["p2", "fini", "p1"]

    def test_un_termine_ne_bouge_pas(self, frame):
        f = FausseFenetre(frame)
        f.ajouter("p1")
        fini = f.ajouter("fini", STATUS_DONE)
        f.download_list._select_only(f.download_list._items[fini])
        f._on_move_up(None)
        assert f.titres() == ["p1", "fini"]

    def test_deja_en_tete(self, frame):
        f = FausseFenetre(frame)
        p1 = f.ajouter("p1")
        f.ajouter("p2")
        f.download_list._select_only(f.download_list._items[p1])
        f._on_move_up(None)
        assert f.titres() == ["p1", "p2"] and f.ordre_file() == ["p1", "p2"]


class TestEtatDeLaFile:
    def test_resume(self, frame):
        f = FausseFenetre(frame)
        f.ajouter("p1")
        f.ajouter("p2")
        f.ajouter("ok", STATUS_DONE)
        f.ajouter("ko", STATUS_ERROR)
        texte = f._queue_status_text()
        assert "En cours : 0" in texte
        assert "En attente : 2" in texte
        assert "Terminés : 1" in texte and "en erreur : 1" in texte
        assert "Téléchargements simultanés : 2" in texte
        assert "Délai" not in texte              # 0 : rien a dire

    def test_titres_en_cours_et_progression(self, frame):
        f = FausseFenetre(frame)
        dl_id = f.ajouter("Ma vidéo")
        item = f._queue._queue.pop(0)            # comme si un worker l'avait pris
        f._queue._active[dl_id] = item
        f._progress[dl_id] = 42.7
        texte = f._queue_status_text()
        assert "En cours : 1" in texte
        assert "Ma vidéo (42 %)" in texte

    def test_pause_anti_robot_et_delai(self, frame):
        import time
        f = FausseFenetre(frame)
        f.settings["delay_between_downloads"] = 30
        f._queue._pause_until = time.monotonic() + 600
        texte = f._queue_status_text()
        assert "reprise dans 10 minutes" in texte
        assert "Délai entre deux téléchargements : 30 secondes" in texte

    def test_sondage_apres_pause(self, frame):
        f = FausseFenetre(frame)
        f._queue._probing = True
        assert "un seul téléchargement" in f._queue_status_text()
