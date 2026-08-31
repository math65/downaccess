"""Moteur WebView2 de Windows pour l'extraction guidee.

Ce qui compte ici n'est pas que WebView2 marche — ca, seul un vrai lancement le
dit — mais que **son absence ne casse jamais rien** : sans le runtime, sans
l'hote, ou avec un hote qui meurt, l'extraction doit retomber sur le navigateur
installe comme elle l'a toujours fait.
"""

import subprocess
import sys

import pytest

from app.core import webview_host as wh


class TestDetectionDuRuntime:
    def test_version_vide_hors_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert wh.runtime_version() == ""
        assert wh.is_runtime_available() is False

    @pytest.mark.skipif(sys.platform != "win32", reason="registre Windows")
    @pytest.mark.parametrize("pv,attendu", [
        ("151.0.4129.107", "151.0.4129.107"),
        # EdgeUpdate laisse la cle en place avec pv=0.0.0.0 apres une
        # desinstallation : la cle existe, le runtime non. Sans ce filtre, on
        # lancerait un hote qui ne demarrerait jamais.
        ("0.0.0.0", ""),
        ("", ""),
    ])
    def test_version_lue_dans_le_registre(self, monkeypatch, pv, attendu):
        import winreg

        class FausseCle:
            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        monkeypatch.setattr(winreg, "OpenKey", lambda *_a, **_k: FausseCle())
        monkeypatch.setattr(winreg, "QueryValueEx", lambda _k, _n: (pv, 1))
        assert wh.runtime_version() == attendu

    def test_disponible_suit_la_version(self, monkeypatch):
        monkeypatch.setattr(wh, "runtime_version", lambda: "151.0.1.1")
        assert wh.is_runtime_available() is True
        monkeypatch.setattr(wh, "runtime_version", lambda: "")
        assert wh.is_runtime_available() is False

    def test_profil_dans_appdata(self, monkeypatch, tmp_path):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        chemin = wh.profile_dir()
        assert chemin.startswith(str(tmp_path))
        assert "WebView2Profile" in chemin

    def test_profil_distinct_de_celui_du_navigateur(self, monkeypatch, tmp_path):
        """Deux moteurs, deux formats de stockage : melanger les profils
        corromprait l'un ou l'autre."""
        from app.core import browser
        monkeypatch.setenv("APPDATA", str(tmp_path))
        assert wh.profile_dir() != browser.downaccess_profile_dir()


class TestLigneDeCommandeDeLHote:
    def test_en_frozen_on_relance_l_executable(self, monkeypatch):
        """Le bundle PyInstaller contient deja pywebview : inutile
        d'empaqueter un second programme, l'exe se relance lui-meme."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", r"C:\DownAccess\DownAccess.exe")
        cmd = wh._host_command(1234, "https://a/", "T")
        assert cmd[0] == r"C:\DownAccess\DownAccess.exe"
        assert cmd[1] == wh.HOST_FLAG
        assert "main.py" not in " ".join(cmd)

    def test_en_developpement_on_relance_main_py(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        cmd = wh._host_command(1234, "https://a/", "T")
        assert cmd[1].endswith("main.py")
        assert wh.HOST_FLAG in cmd

    def test_le_port_et_l_url_sont_transmis(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        cmd = wh._host_command(4242, "https://exemple/x", "Titre")
        assert "4242" in cmd
        assert "https://exemple/x" in cmd


class TestArgumentsCoteHote:
    """L'hote tourne sans console : un analyseur qui quitte sur un argument
    inattendu laisserait un processus mort sans le moindre message."""

    def test_lecture_normale(self):
        args = wh._parse_host_args(
            [wh.HOST_FLAG, "--port", "9000", "--url", "https://a/",
             "--title", "T", "--profile", r"C:\p"])
        assert args == {"port": 9000, "url": "https://a/",
                        "title": "T", "profile": r"C:\p"}

    def test_arguments_manquants_donnent_des_valeurs_sures(self):
        args = wh._parse_host_args([wh.HOST_FLAG])
        assert args["port"] == 0
        assert args["url"] == "about:blank"

    def test_un_argument_inconnu_ne_fait_pas_tout_echouer(self):
        args = wh._parse_host_args(
            [wh.HOST_FLAG, "--inconnu", "x", "--port", "77"])
        assert args["port"] == 77


class TestEchecsDeLancement:
    """Chaque echec doit lever `WebViewUnavailable` — c'est ce que l'appelant
    attrape pour replier sur le navigateur installe."""

    def test_sans_runtime_on_ne_lance_meme_pas(self, monkeypatch):
        monkeypatch.setattr(wh, "is_runtime_available", lambda: False)
        lancements = []
        monkeypatch.setattr(subprocess, "Popen",
                            lambda *a, **k: lancements.append(a))
        with pytest.raises(wh.WebViewUnavailable):
            wh.start_host("https://a/")
        assert lancements == [], "aucun processus ne doit etre cree"

    def test_hote_impossible_a_lancer(self, monkeypatch):
        monkeypatch.setattr(wh, "is_runtime_available", lambda: True)

        def _boom(*_a, **_k):
            raise OSError("introuvable")

        monkeypatch.setattr(subprocess, "Popen", _boom)
        with pytest.raises(wh.WebViewUnavailable):
            wh.start_host("https://a/")

    def test_hote_qui_meurt_au_demarrage(self, monkeypatch):
        monkeypatch.setattr(wh, "is_runtime_available", lambda: True)

        class Mort:
            returncode = 3

            def poll(self):
                return 3

        monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Mort())
        with pytest.raises(wh.WebViewUnavailable) as err:
            wh.start_host("https://a/")
        assert "3" in str(err.value)

    def test_port_qui_n_ouvre_jamais(self, monkeypatch):
        """Delai depasse : on tue l'hote au lieu de le laisser trainer."""
        monkeypatch.setattr(wh, "is_runtime_available", lambda: True)
        tues = []

        class Vivant:
            returncode = None

            def poll(self):
                return None

            def terminate(self):
                tues.append("terminate")

            def wait(self, timeout=None):
                return 0

        monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Vivant())
        monkeypatch.setattr(wh, "_cdp_answers", lambda _p: False)
        with pytest.raises(wh.WebViewUnavailable):
            wh.start_host("https://a/", timeout=0.5)
        assert tues, "l'hote doit etre arrete, pas abandonne"

    def test_arret_sans_processus_ne_leve_pas(self):
        wh.stop_host(None)

    def test_arret_d_un_processus_deja_mort_ne_leve_pas(self):
        class Fini:
            def poll(self):
                return 0

        wh.stop_host(Fini())
