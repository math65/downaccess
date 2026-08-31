"""Choix du moteur de l'extraction guidee : WebView2 ou navigateur installe.

Ce qui est teste ici, c'est l'aiguillage — pas WebView2 lui-meme. La regle a
tenir : l'absence de WebView2 ne doit JAMAIS empecher une extraction. Elle
fonctionnait avant qu'il existe, elle doit fonctionner sans lui.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui import uge_dialog as uge


class Faux:
    """Fenetre reduite a ce dont `_ensure_browser` a besoin.

    Construire la vraie fenetre lancerait un navigateur : ici on teste
    l'aiguillage, pas l'interface.
    """

    def __init__(self, engine_reglage="auto"):
        self._page = None
        self._wv_proc = None
        self._engine = ""
        self._intercept_enabled = False
        self._browser_name = ""
        self._reglage = engine_reglage
        self.statuts = []

    def _set_status(self, texte):
        self.statuts.append(texte)

    _ensure_browser = uge.UGEDialog._ensure_browser


@pytest.fixture
def reglage(monkeypatch):
    """Pilote la valeur de `uge_engine` lue par `_ensure_browser`."""
    valeurs = {"uge_engine": "auto"}
    from app.core import settings as cfg
    monkeypatch.setattr(cfg, "load", lambda: dict(valeurs))
    return valeurs


class TestChoixDuMoteur:
    def test_webview2_est_essaye_en_premier(self, reglage, monkeypatch):
        appels = []
        monkeypatch.setattr(Faux, "_start_webview2",
                            lambda self: appels.append("wv2") or True,
                            raising=False)
        monkeypatch.setattr(Faux, "_start_installed_browser",
                            lambda self: appels.append("navigateur") or True,
                            raising=False)
        assert Faux()._ensure_browser() is True
        assert appels == ["wv2"], "le navigateur ne doit pas etre lance en plus"

    def test_repli_silencieux_sur_le_navigateur(self, reglage, monkeypatch):
        """Sans WebView2, l'extraction se deroule comme avant. Ce n'est pas
        une panne : aucun dialogue ne doit s'ouvrir."""
        appels = []
        monkeypatch.setattr(Faux, "_start_webview2",
                            lambda self: appels.append("wv2") or False,
                            raising=False)
        monkeypatch.setattr(Faux, "_start_installed_browser",
                            lambda self: appels.append("navigateur") or True,
                            raising=False)
        boites = []
        monkeypatch.setattr(wx, "MessageBox",
                            lambda *a, **k: boites.append(a))
        assert Faux()._ensure_browser() is True
        assert appels == ["wv2", "navigateur"]
        assert boites == [], "un repli qui marche ne se signale pas"

    def test_reglage_navigateur_saute_webview2(self, reglage, monkeypatch):
        """Qui choisit son navigateur ne doit pas payer une tentative
        WebView2 a chaque extraction."""
        reglage["uge_engine"] = "browser"
        appels = []
        monkeypatch.setattr(Faux, "_start_webview2",
                            lambda self: appels.append("wv2") or True,
                            raising=False)
        monkeypatch.setattr(Faux, "_start_installed_browser",
                            lambda self: appels.append("navigateur") or True,
                            raising=False)
        Faux()._ensure_browser()
        assert appels == ["navigateur"]

    def test_moteur_deja_ouvert_n_est_pas_relance(self, reglage, monkeypatch):
        appels = []
        monkeypatch.setattr(Faux, "_start_webview2",
                            lambda self: appels.append("wv2") or True,
                            raising=False)
        f = Faux()
        f._page = object()
        assert f._ensure_browser() is True
        assert appels == []

    def test_reglages_illisibles_ne_bloquent_pas(self, monkeypatch):
        """Un settings.json corrompu ne doit pas empecher de telecharger."""
        from app.core import settings as cfg

        def _boom():
            raise OSError("illisible")

        monkeypatch.setattr(cfg, "load", _boom)
        monkeypatch.setattr(Faux, "_start_webview2", lambda self: True,
                            raising=False)
        assert Faux()._ensure_browser() is True


class TestDemarrageWebView2:
    """`_start_webview2` doit rendre False, jamais lever : c'est ce False qui
    declenche le repli."""

    def test_hote_indisponible_rend_false(self, monkeypatch):
        from app.core import webview_host
        monkeypatch.setattr(
            webview_host, "start_host",
            lambda *a, **k: (_ for _ in ()).throw(
                webview_host.WebViewUnavailable("pas de runtime")))
        f = Faux()
        f._start_webview2 = uge.UGEDialog._start_webview2.__get__(f)
        assert f._start_webview2() is False
        assert f._page is None
        assert f._wv_proc is None

    def test_attache_qui_echoue_arrete_l_hote(self, monkeypatch):
        """Sinon un processus WebView2 orphelin resterait en memoire."""
        from app.core import webview_host
        arretes = []

        class FauxProc:
            pass

        monkeypatch.setattr(webview_host, "start_host",
                            lambda *a, **k: (FauxProc(), "127.0.0.1:1"))
        monkeypatch.setattr(webview_host, "stop_host",
                            lambda p: arretes.append(p))
        import DrissionPage
        monkeypatch.setattr(
            DrissionPage, "ChromiumPage",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("refus")))
        f = Faux()
        f._start_webview2 = uge.UGEDialog._start_webview2.__get__(f)
        assert f._start_webview2() is False
        assert len(arretes) == 1, "l'hote lance doit etre arrete"
        assert isinstance(arretes[0], FauxProc)
