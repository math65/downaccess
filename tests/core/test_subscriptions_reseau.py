"""Resilience reseau du releve d'abonnements.

Mesure du 2026-08-20 : le flux Atom d'une chaine YouTube repond 404 ou 500
environ une fois sur trois, sur une adresse pourtant valide. Sans reprise, un
abonnement sain serait declare en panne — et l'utilisateur, lisant « 404 »,
croirait son adresse fausse.
"""

import io
from urllib.error import HTTPError, URLError

import pytest

from app.core import subscriptions as subs


@pytest.fixture(autouse=True)
def sans_attente(monkeypatch):
    """Neutralise les pauses entre tentatives : les tests doivent rester rapides."""
    monkeypatch.setattr(subs.time, "sleep", lambda _s: None)


def faux_urlopen(reponses):
    """Renvoie un urlopen qui rejoue `reponses` (exception ou contenu)."""
    restant = list(reponses)

    def _open(req, timeout=None):
        item = restant.pop(0)
        if isinstance(item, Exception):
            raise item
        return _Reponse(item)

    return _open


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def erreur_http(code):
    return HTTPError("https://a/f.xml", code, "Erreur", {}, None)


class TestReprise:
    def test_404_passager_est_reessaye(self, monkeypatch):
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([erreur_http(404), b"<ok/>"]))
        assert subs._http_get("https://a/f.xml") == b"<ok/>"

    def test_500_passager_est_reessaye(self, monkeypatch):
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([erreur_http(500), erreur_http(503), b"<ok/>"]))
        assert subs._http_get("https://a/f.xml") == b"<ok/>"

    def test_panne_reseau_reessayee(self, monkeypatch):
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([URLError("timed out"), b"<ok/>"]))
        assert subs._http_get("https://a/f.xml") == b"<ok/>"

    def test_abandon_apres_trois_tentatives(self, monkeypatch):
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([erreur_http(500)] * subs._TENTATIVES))
        with pytest.raises(subs.FeedError, match="500"):
            subs._http_get("https://a/f.xml")

    def test_erreur_definitive_echoue_tout_de_suite(self, monkeypatch):
        """Un 403 ne se resoudra pas tout seul : inutile de faire patienter."""
        appels = {"n": 0}

        def _open(req, timeout=None):
            appels["n"] += 1
            raise erreur_http(403)

        monkeypatch.setattr(subs, "urlopen", _open)
        with pytest.raises(subs.FeedError, match="403"):
            subs._http_get("https://a/f.xml")
        assert appels["n"] == 1

    def test_message_reste_lisible(self, monkeypatch):
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([erreur_http(500)] * subs._TENTATIVES))
        with pytest.raises(subs.FeedError) as exc:
            subs._http_get("https://a/f.xml")
        assert "500" in str(exc.value)
        assert "Traceback" not in str(exc.value)

    def test_contenu_plafonne(self, monkeypatch):
        """Un serveur qui repondrait un fichier enorme ne doit pas tout charger."""
        monkeypatch.setattr(subs, "urlopen",
                            faux_urlopen([b"x" * (subs.MAX_FEED_BYTES + 5000)]))
        assert len(subs._http_get("https://a/f.xml")) == subs.MAX_FEED_BYTES
