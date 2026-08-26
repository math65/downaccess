"""File de telechargement : concurrence, ordre, annulation, remontee d'erreurs.

Le telechargeur est remplace par un double : on teste l'orchestration, pas
yt-dlp. Les callbacks sont appeles en direct (`post_to_ui` = appel immediat),
ce qui evite toute dependance a wxPython.
"""

import threading
import time
from typing import ClassVar

import pytest

from app.core.downloader import DownloadError, DownloadInfo, LoginRequiredError
from app.core.queue_manager import QueueManager


class FauxDownloader:
    """Telechargeur instrumente : le test decide de ce qui reussit ou echoue."""

    demarres: ClassVar[list] = []
    erreurs: ClassVar[dict] = {}
    duree = 0.0
    barriere = None

    def __init__(self, settings):
        self.settings = settings

    def fetch_info(self, download_id, url, **kw):
        return DownloadInfo(download_id=download_id, url=url,
                            title=f"Titre {url}", site="test", raw_formats=[])

    def download(self, download_id, url, on_progress, stop_event, **kw):
        type(self).demarres.append(url)
        if type(self).barriere is not None:
            try:
                type(self).barriere.wait(timeout=DELAI_BLOCAGE)
            except threading.BrokenBarrierError:
                pass
        if type(self).duree:
            time.sleep(type(self).duree)
        if stop_event.is_set():
            return
        exc = type(self).erreurs.get(url)
        if exc:
            raise exc
        return


@pytest.fixture
def faux(monkeypatch):
    """Un double NEUF par test.

    On cree une sous-classe a chaque fois plutot que de reinitialiser les
    attributs de classe : un thread encore vivant a la fin d'un test (worker
    bloque sur une barriere, telechargement simule en cours) continuerait
    sinon d'ecrire dans les compteurs du test suivant.
    """
    from app.core import queue_manager
    double = type("FauxDownloaderTest", (FauxDownloader,), {
        "demarres": [], "erreurs": {}, "duree": 0.0, "barriere": None,
    })
    monkeypatch.setattr(queue_manager, "Downloader", double)
    yield double
    if double.barriere is not None:
        double.barriere.abort()


class Journal:
    """Collecte les evenements remontes a l'interface."""

    def __init__(self):
        self.completes = []
        self.erreurs = []
        self.infos = []
        self.fini = threading.Event()

    def on_complete(self, dl_id):
        self.completes.append(dl_id)
        self.fini.set()

    def on_error(self, dl_id, message, login_required):
        self.erreurs.append((dl_id, message, login_required))
        self.fini.set()

    def on_info(self, info):
        self.infos.append(info)


def manager(journal, max_concurrent=2):
    return QueueManager(
        settings={"download_folder": ".", "max_concurrent_downloads": max_concurrent},
        post_to_ui=lambda fn, *a: fn(*a),
        on_info=journal.on_info,
        on_progress=lambda p: None,
        on_complete=journal.on_complete,
        on_error=journal.on_error,
    )


# Duree pendant laquelle un worker simule reste bloque sur la barriere. Rien ne
# l'attend jamais : la barriere sert a immobiliser un telechargement le temps
# que le test inspecte la file. Le delai doit donc etre franchement plus long
# que la duree des assertions, sinon le worker repart tout seul sous charge et
# la file avance en plein milieu du test (echecs intermittents). La fixture
# `faux` appelle abort() au demontage : aucun test n'attend reellement ce delai.
DELAI_BLOCAGE = 60


def attendre(condition, delai=5.0):
    """Attend qu'une condition devienne vraie (les workers sont asynchrones)."""
    limite = time.monotonic() + delai
    while time.monotonic() < limite:
        if condition():
            return True
        time.sleep(0.02)
    return False


class TestDeroulementNominal:
    def test_un_telechargement_va_au_bout(self, faux):
        j = Journal()
        q = manager(j)
        dl_id = q.add("https://a/1")
        assert j.fini.wait(5)
        assert j.completes == [dl_id]
        assert faux.demarres == ["https://a/1"]

    def test_les_infos_remontent_avant_le_telechargement(self, faux):
        j = Journal()
        q = manager(j)
        q.add("https://a/1")
        assert j.fini.wait(5)
        assert j.infos[0].title == "Titre https://a/1"

    def test_identifiants_uniques(self, faux):
        j = Journal()
        q = manager(j)
        assert q.add("https://a/1") != q.add("https://a/2")


class TestConcurrence:
    def test_respecte_la_limite(self, faux):
        """Deux telechargements simultanes au maximum : le troisieme attend."""
        faux.barriere = threading.Barrier(3, timeout=DELAI_BLOCAGE)
        j = Journal()
        q = manager(j, max_concurrent=2)
        for i in range(3):
            q.add(f"https://a/{i}")
        assert attendre(lambda: len(faux.demarres) == 2)
        time.sleep(0.2)
        assert len(faux.demarres) == 2, "le 3e ne doit pas avoir demarre"
        assert q.active_count == 2
        faux.barriere.abort()
        assert attendre(lambda: len(faux.demarres) == 3)

    def test_le_creneau_est_rendu_apres_une_erreur(self, faux):
        """Regression : une exception inattendue tuait le thread sans liberer
        le creneau, et la file restait bloquee."""
        faux.erreurs = {"https://a/0": RuntimeError("panne")}
        j = Journal()
        q = manager(j, max_concurrent=1)
        q.add("https://a/0")
        q.add("https://a/1")
        assert attendre(lambda: len(faux.demarres) == 2)
        assert attendre(lambda: q.active_count == 0)


class TestErreurs:
    def test_erreur_de_telechargement_remontee(self, faux):
        faux.erreurs = {"https://a/1": DownloadError("disque plein")}
        j = Journal()
        q = manager(j)
        dl_id = q.add("https://a/1")
        assert j.fini.wait(5)
        assert j.erreurs[0][0] == dl_id
        assert "disque plein" in j.erreurs[0][1]
        assert j.erreurs[0][2] is False

    def test_connexion_requise_signalee_a_part(self, faux):
        """L'interface propose la connexion guidee sur ce drapeau."""
        faux.erreurs = {"https://a/1": LoginRequiredError("connexion requise")}
        j = Journal()
        q = manager(j)
        q.add("https://a/1")
        assert j.fini.wait(5)
        assert j.erreurs[0][2] is True

    def test_exception_inattendue_ne_tue_pas_le_worker(self, faux):
        faux.erreurs = {"https://a/1": RuntimeError("imprevu")}
        j = Journal()
        q = manager(j)
        q.add("https://a/1")
        assert j.fini.wait(5)
        assert len(j.erreurs) == 1


class TestAnnulation:
    def test_annuler_avant_le_demarrage(self, faux):
        faux.barriere = threading.Barrier(2, timeout=DELAI_BLOCAGE)
        j = Journal()
        q = manager(j, max_concurrent=1)
        q.add("https://a/0")
        en_attente = q.add("https://a/1")
        assert attendre(lambda: len(faux.demarres) == 1)
        q.cancel(en_attente)
        faux.barriere.abort()
        time.sleep(0.3)
        assert "https://a/1" not in faux.demarres

    def test_annulation_n_est_pas_une_erreur(self, faux):
        """Annuler est un choix de l'utilisateur : aucune fenetre d'erreur."""
        faux.duree = 0.3
        j = Journal()
        q = manager(j)
        dl_id = q.add("https://a/1")
        assert attendre(lambda: len(faux.demarres) == 1)
        q.cancel(dl_id)
        time.sleep(0.5)
        assert j.erreurs == []

    def test_tout_annuler_vide_la_file(self, faux):
        faux.duree = 0.2
        j = Journal()
        q = manager(j, max_concurrent=2)
        for i in range(4):
            q.add(f"https://a/{i}")
        q.cancel_all()
        assert q.get_state()["pending"] == []
        assert attendre(lambda: q.active_count == 0)


class TestOrdre:
    def test_reordonner_l_attente(self, faux):
        faux.barriere = threading.Barrier(2, timeout=DELAI_BLOCAGE)
        j = Journal()
        q = manager(j, max_concurrent=1)
        q.add("https://a/0")                 # part immediatement
        assert attendre(lambda: len(faux.demarres) == 1)
        second = q.add("https://a/1")
        troisieme = q.add("https://a/2")

        assert [e["id"] for e in q.get_state()["pending"]] == [second, troisieme]
        assert q.move_up(troisieme) is True
        assert [e["id"] for e in q.get_state()["pending"]] == [troisieme, second]
        assert q.move_down(troisieme) is True
        assert [e["id"] for e in q.get_state()["pending"]] == [second, troisieme]
        faux.barriere.abort()

    def test_bornes_de_deplacement(self, faux):
        faux.barriere = threading.Barrier(2, timeout=DELAI_BLOCAGE)
        j = Journal()
        q = manager(j, max_concurrent=1)
        q.add("https://a/0")
        assert attendre(lambda: len(faux.demarres) == 1)
        premier = q.add("https://a/1")
        dernier = q.add("https://a/2")
        assert q.move_up(premier) is False       # deja en tete
        assert q.move_down(dernier) is False     # deja en queue
        faux.barriere.abort()

    def test_deplacer_un_inconnu(self, faux):
        j = Journal()
        q = manager(j)
        assert q.move_up("inexistant") is False
        assert q.move_down("inexistant") is False


class TestPause:
    def test_pause_puis_reprise(self, faux):
        faux.duree = 0.4
        j = Journal()
        q = manager(j)
        dl_id = q.add("https://a/1")
        assert attendre(lambda: q.is_active(dl_id))
        q.pause(dl_id)
        assert q.is_paused(dl_id) is True
        q.resume(dl_id)
        assert q.is_paused(dl_id) is False

    def test_etat_d_un_inconnu(self, faux):
        j = Journal()
        q = manager(j)
        assert q.is_paused("inexistant") is False
        assert q.is_active("inexistant") is False
