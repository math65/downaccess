"""La file survit-elle a la fermeture de l'application ?

Jusqu'ici, non : seul `history.json` etait ecrit, et il ne garde que les
telechargements qui ont abouti. Un utilisateur bloque sur l'analyse d'une
playlist a ferme DownAccess pour s'en sortir et a tout perdu (rapport de Brad,
2026-09-01).
"""

import json
import threading

import pytest

from app.core import queue_store
from app.core.queue_manager import QueueItem


def item(**kw):
    base = {"download_id": "x", "url": "https://a/1"}
    base.update(kw)
    return QueueItem(**base)


class TestCeQuiSeConserve:
    def test_un_telechargement_ordinaire_se_conserve(self):
        assert queue_store.is_restorable(item())

    def test_sans_adresse_rien_a_conserver(self):
        assert not queue_store.is_restorable(item(url=""))

    @pytest.mark.parametrize("champ,valeur", [
        ("cookies", "SID=abc"),
        ("referer", "https://site/page"),
        ("skip_info", True),
    ])
    def test_l_extraction_guidee_ne_se_conserve_pas(self, champ, valeur):
        """Son adresse porte un jeton de session qui expire en quelques
        minutes : la restaurer le lendemain ne produirait qu'un echec
        incomprehensible."""
        assert not queue_store.is_restorable(item(**{champ: valeur}))

    def test_les_reglages_du_telechargement_sont_gardes(self):
        d = queue_store.to_dict(item(
            format_spec="mp3", format_id="140", playlist_title="Ma liste",
            playlist_number=3, subtitles_override=True))
        assert d["format_spec"] == "mp3"
        assert d["format_id"] == "140"
        assert d["playlist_title"] == "Ma liste"
        assert d["playlist_number"] == 3
        assert d["subtitles_override"] is True

    def test_les_evenements_ne_sont_jamais_ecrits(self):
        """Ils ne se serialisent pas et n'auraient aucun sens d'une session a
        l'autre."""
        d = queue_store.to_dict(item())
        assert "stop_event" not in d
        assert "pause_event" not in d
        assert "prefetched_info" not in d


class TestAllerRetourDisque:
    def test_ecrire_puis_relire(self, appdata):
        queue_store.save([item(url="https://a/1", format_spec="mp3"),
                          item(url="https://a/2")])
        relu = queue_store.load()
        assert [e["url"] for e in relu] == ["https://a/1", "https://a/2"]
        assert relu[0]["format_spec"] == "mp3"

    def test_l_extrait_redevient_un_couple(self, appdata):
        """JSON ne connait pas les tuples : sans reconversion, `section`
        reviendrait en liste et casserait le decoupage."""
        queue_store.save([item(section=(10.0, 20.0))])
        assert queue_store.load()[0]["section"] == (10.0, 20.0)

    def test_rien_a_conserver_efface_le_fichier(self, appdata):
        queue_store.save([item()])
        queue_store.save([])
        assert queue_store.load() == []

    def test_fichier_absent(self, appdata):
        assert queue_store.load() == []

    def test_fichier_tronque_ne_bloque_pas_le_demarrage(self, appdata):
        """Coupure de courant pendant l'ecriture : on repart d'une file vide
        plutot que de refuser de demarrer."""
        chemin = appdata / "DownAccess" / "queue.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text('[{"url": "https://a/1"', encoding="utf-8")
        assert queue_store.load() == []

    def test_champ_inconnu_ignore(self, appdata):
        """Un fichier ecrit par une version plus recente ne doit pas faire
        exploser `QueueManager.add()`."""
        chemin = appdata / "DownAccess" / "queue.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(
            json.dumps([{"url": "https://a/1", "champ_du_futur": 42}]),
            encoding="utf-8")
        relu = queue_store.load()
        assert relu[0]["url"] == "https://a/1"
        assert "champ_du_futur" not in relu[0]

    def test_entree_sans_adresse_ecartee(self, appdata):
        chemin = appdata / "DownAccess" / "queue.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps([{"format_spec": "mp3"},
                                      {"url": "https://a/1"}]),
                          encoding="utf-8")
        assert len(queue_store.load()) == 1

    def test_file_monstrueuse_bornee(self, appdata):
        """Une chaine entiere enfilee par erreur ne doit pas ressusciter des
        milliers de telechargements a chaque demarrage."""
        queue_store.save([item(url=f"https://a/{i}")
                          for i in range(queue_store.MAX_ITEMS + 50)])
        assert len(queue_store.load()) == queue_store.MAX_ITEMS


class TestCeQueLaFileRendACConserver:
    """`QueueManager.unfinished()` : ce que l'on ecrit a la fermeture."""

    def _file(self):
        from app.core.queue_manager import QueueManager
        return QueueManager({}, lambda f, *a: None, lambda *a: None,
                            lambda *a: None, lambda *a: None, lambda *a: None)

    def test_les_annules_ne_sont_pas_conserves(self):
        """Annuler puis fermer ne doit pas ramener le telechargement au
        prochain lancement."""
        q = self._file()
        vivant = item(download_id="a")
        annule = item(download_id="b")
        annule.stop_event.set()
        q._active = {"a": vivant, "b": annule}
        q._queue = []
        restants = q.unfinished()
        assert [i.download_id for i in restants] == ["a"]

    def test_les_actifs_passent_devant_les_attente(self):
        """Ils reprennent en premier : c'est l'ordre que l'utilisateur avait."""
        q = self._file()
        q._active = {"a": item(download_id="a")}
        q._queue = [item(download_id="b")]
        assert [i.download_id for i in q.unfinished()] == ["a", "b"]

    def test_restore_remet_en_file(self):
        q = self._file()
        q._try_start_next = lambda: None      # pas de vrai telechargement ici
        ids = q.restore([{"url": "https://a/1", "format_spec": "mp3"},
                         {"url": "https://a/2"}])
        assert len(ids) == 2
        assert [i.url for i in q._queue] == ["https://a/1", "https://a/2"]
        assert q._queue[0].format_spec == "mp3"

    def test_une_entree_illisible_n_empeche_pas_les_autres(self):
        q = self._file()
        q._try_start_next = lambda: None
        ids = q.restore([{"url": "https://a/1", "argument_inconnu": 1},
                         {"url": "https://a/2"}])
        assert len(ids) == 1, "l'entree valide doit passer"
        assert q._queue[0].url == "https://a/2"


class TestEvenementsNeufs:
    def test_les_elements_restaures_repartent_avec_des_evenements_neufs(self):
        from app.core.queue_manager import QueueManager
        q = QueueManager({}, lambda f, *a: None, lambda *a: None,
                         lambda *a: None, lambda *a: None, lambda *a: None)
        q._try_start_next = lambda: None
        q.restore([{"url": "https://a/1"}])
        elem = q._queue[0]
        assert isinstance(elem.stop_event, threading.Event)
        assert not elem.stop_event.is_set()
        assert not elem.pause_event.is_set()
