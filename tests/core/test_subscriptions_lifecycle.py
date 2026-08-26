"""Cycle de vie d'un abonnement : creation, releve, marquage, persistance.

Le reseau est remplace par les fixtures : chaque test controle exactement ce
que « publie » le flux, ce qui permet de verifier des scenarios impossibles a
provoquer sur un vrai site (une video retiree, un serveur en panne).
"""

import json

import pytest

from app.core import subscriptions as subs
from tests.conftest import read_fixture

ATOM = read_fixture("youtube_channel.atom.xml")


@pytest.fixture
def flux_fige(monkeypatch):
    """Remplace le reseau par un flux qu'on pilote depuis le test."""
    etat = {"data": ATOM}

    def faux_get(url):
        if isinstance(etat["data"], Exception):
            raise etat["data"]
        return etat["data"]

    monkeypatch.setattr(subs, "_http_get", faux_get)
    return etat


def abonnement(**kw):
    defauts = {"sub_id": "abc", "title": "ARTE", "url": "https://youtube.com/@arte",
               "feed_url": "https://youtube.com/feeds/videos.xml?channel_id=UC1",
               "kind": subs.KIND_YOUTUBE}
    defauts.update(kw)
    return subs.Subscription(**defauts)


class TestCreation:
    def test_marque_tout_le_passe_comme_vu(self, flux_fige):
        """S'abonner veut dire « previens-moi de ce qui arrive », pas
        « deverse-moi les quinze dernieres videos »."""
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1")
        assert len(sub.seen_ids) == 3
        assert subs.check(sub) == []

    def test_reprend_le_titre_du_flux(self, flux_fige):
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1")
        assert sub.title == "ARTE"

    def test_titre_impose_par_l_utilisateur(self, flux_fige):
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          title="Ma chaine preferee")
        assert sub.title == "Ma chaine preferee"

    def test_conserve_le_format_et_l_automatisme(self, flux_fige):
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          format_spec="mp3", auto_download=True)
        assert sub.format_spec == "mp3"
        assert sub.auto_download is True

    def test_rattrapage_propose_tout_le_catalogue(self, flux_fige):
        """En decouvrant un podcast on veut souvent ses anciens episodes. Sans
        cette option ils resteraient invisibles a jamais : aucune verification
        ulterieure ne peut faire reapparaitre une entree marquee comme vue."""
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          catch_up=True)
        assert sub.seen_ids == []
        assert len(subs.check(sub)) == 3

    def test_sans_rattrapage_le_passe_reste_invisible(self, flux_fige):
        """Le defaut ne change pas : c'est le comportement voulu."""
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          catch_up=False)
        assert subs.check(sub) == []

    def test_rattrapage_n_empeche_pas_de_marquer_vu(self, flux_fige):
        """Une fois les entrees proposees et traitees, elles ne doivent plus
        revenir a la verification suivante."""
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          catch_up=True)
        subs.mark_seen(sub, subs.check(sub))
        assert subs.check(sub) == []


class TestReleve:
    def test_detecte_ce_qui_est_nouveau(self, flux_fige):
        sub = abonnement(seen_ids=[])
        assert len(subs.check(sub)) == 3

    def test_ne_remonte_que_l_inconnu(self, flux_fige):
        _titre, entries = subs.parse_feed(ATOM)
        sub = abonnement(seen_ids=[entries[0].entry_id])
        nouveaux = subs.check(sub)
        assert len(nouveaux) == 2
        assert entries[0].entry_id not in [e.entry_id for e in nouveaux]

    def test_ne_modifie_pas_l_abonnement(self, flux_fige):
        """Fermer la fenetre sans rien faire ne doit pas perdre les nouveautes :
        c'est l'appelant qui decide quand marquer comme vu."""
        sub = abonnement(seen_ids=[])
        subs.check(sub)
        assert sub.seen_ids == []

    def test_marquage_puis_plus_rien(self, flux_fige):
        sub = abonnement(seen_ids=[])
        subs.mark_seen(sub, subs.check(sub))
        assert subs.check(sub) == []

    def test_marquage_sans_doublon(self, flux_fige):
        sub = abonnement(seen_ids=[])
        nouveaux = subs.check(sub)
        subs.mark_seen(sub, nouveaux)
        subs.mark_seen(sub, nouveaux)
        assert len(sub.seen_ids) == len(set(sub.seen_ids)) == 3

    def test_plafond_des_identifiants_memorises(self):
        """Un abonnement suivi pendant des annees ne doit pas faire enfler le
        fichier de configuration sans fin."""
        sub = abonnement(seen_ids=[str(i) for i in range(subs.MAX_SEEN_IDS + 200)])
        subs.mark_seen(sub, [])
        assert len(sub.seen_ids) == subs.MAX_SEEN_IDS
        # Ce sont les plus RECENTS qu'on garde.
        assert sub.seen_ids[-1] == str(subs.MAX_SEEN_IDS + 199)

    def test_horodatage_de_verification(self, flux_fige):
        sub = abonnement()
        assert sub.last_checked_label() == "jamais"
        subs.touch(sub)
        assert sub.last_checked_label() != "jamais"


class TestReleveGroupe:
    def test_un_flux_en_panne_n_empeche_pas_les_autres(self, monkeypatch):
        """Regression de conception : une chaine dont l'adresse a change ne
        doit jamais masquer les nouveautes des autres abonnements."""
        def faux_get(url):
            if "casse" in url:
                raise subs.FeedError("Le serveur a repondu 404 (Not Found).")
            return ATOM

        monkeypatch.setattr(subs, "_http_get", faux_get)
        bon = abonnement(sub_id="bon", seen_ids=[])
        casse = abonnement(sub_id="casse", title="Chaine morte",
                           feed_url="https://exemple.org/casse.xml")

        fresh, errors = subs.check_all([casse, bon])
        assert len(fresh["bon"]) == 3
        assert "casse" not in fresh
        assert len(errors) == 1
        assert "Chaine morte" in errors[0]

    def test_aucune_nouveaute(self, flux_fige):
        _titre, entries = subs.parse_feed(ATOM)
        sub = abonnement(seen_ids=[e.entry_id for e in entries])
        fresh, errors = subs.check_all([sub])
        assert fresh == {}
        assert errors == []

    def test_erreur_inattendue_est_capturee(self, monkeypatch):
        def explose(url):
            raise RuntimeError("panne imprevue")
        monkeypatch.setattr(subs, "_http_get", explose)
        fresh, errors = subs.check_all([abonnement()])
        assert fresh == {}
        assert len(errors) == 1


class TestPersistance:
    def test_aller_retour(self, appdata, flux_fige):
        sub = subs.create("https://www.youtube.com/feeds/videos.xml?channel_id=UC1",
                          format_spec="mp3", auto_download=True)
        subs.save([sub])
        recharge = subs.load()
        assert len(recharge) == 1
        assert recharge[0].title == sub.title
        assert recharge[0].format_spec == "mp3"
        assert recharge[0].auto_download is True
        assert recharge[0].seen_ids == sub.seen_ids

    def test_fichier_absent(self, appdata):
        assert subs.load() == []

    def test_fichier_corrompu_ne_fait_pas_planter(self, appdata):
        chemin = appdata / "DownAccess" / "subscriptions.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("{ pas du json", encoding="utf-8")
        assert subs.load() == []

    def test_champ_inconnu_ignore(self, appdata):
        """Un fichier ecrit par une version future ne doit pas tout casser."""
        chemin = appdata / "DownAccess" / "subscriptions.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps({"version": 99, "subscriptions": [
            {"sub_id": "x", "title": "T", "champ_du_futur": 1}]}), encoding="utf-8")
        charge = subs.load()
        assert len(charge) == 1
        assert charge[0].title == "T"

    def test_identifiant_manquant_regenere(self, appdata):
        chemin = appdata / "DownAccess" / "subscriptions.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps({"subscriptions": [{"title": "Sans id"}]}),
                          encoding="utf-8")
        assert subs.load()[0].sub_id

    def test_ecriture_atomique_sans_residu(self, appdata, flux_fige):
        """Une coupure pendant la sauvegarde ne doit pas laisser un fichier
        tronque qui ferait perdre tous les abonnements."""
        subs.save([abonnement()])
        fichiers = {p.name for p in (appdata / "DownAccess").iterdir()}
        assert "subscriptions.json" in fichiers
        assert not any(f.endswith(".tmp") for f in fichiers)
