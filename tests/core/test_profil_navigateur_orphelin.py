"""Un navigateur orphelin sur le profil dedie ne doit plus capter les lancements.

Regression (Brad, 2026-11-12, 0.2.9) : Edge choisi dans les Preferences, mais la
page s'ouvrait dans Chrome. Un Chrome de DownAccess reste en vie sur le profil
dedie recoit tout nouveau lancement sur ce profil, quel que soit l'executable.
"""
import os

import psutil
import pytest

from app.core import browser

PROFILE = r"C:\Users\x\AppData\Roaming\DownAccess\BrowserProfile"


class FakeProc:
    def __init__(self, pid, name, cmdline, parent_pids=()):
        self.pid = pid
        self.info = {"name": name}
        self._cmdline = cmdline
        self._parents = [type("P", (), {"pid": p})() for p in parent_pids]
        self.terminated = False

    def cmdline(self):
        return self._cmdline

    def parents(self):
        return self._parents

    def terminate(self):
        self.terminated = True


@pytest.fixture
def procs(monkeypatch):
    listed = []
    monkeypatch.setattr(browser, "downaccess_profile_dir", lambda: PROFILE)
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: list(listed))
    monkeypatch.setattr(psutil, "wait_procs", lambda ps, timeout=None: (ps, []))
    return listed


def test_chrome_orphelin_ferme_meme_si_edge_est_demande(procs):
    orphan = FakeProc(10, "chrome.exe", ["chrome.exe", "--user-data-dir=" + PROFILE.upper()])
    procs.append(orphan)
    assert browser.release_dedicated_profile() == 1
    assert orphan.terminated


def test_navigateur_de_la_session_en_cours_epargne(procs):
    ours = FakeProc(11, "msedge.exe", ["msedge.exe", "--user-data-dir=" + PROFILE],
                    parent_pids=[os.getpid()])
    procs.append(ours)
    assert browser.release_dedicated_profile() == 0
    assert not ours.terminated


def test_navigateur_habituel_de_l_utilisateur_jamais_touche(procs):
    perso = FakeProc(12, "chrome.exe", ["chrome.exe"])
    autre = FakeProc(13, "chrome.exe", ["chrome.exe", r"--user-data-dir=C:\Autre\Profil"])
    procs.extend([perso, autre])
    assert browser.release_dedicated_profile() == 0
    assert not perso.terminated and not autre.terminated


def test_processus_auxiliaires_ignores(procs):
    renderer = FakeProc(14, "chrome.exe",
                        ["chrome.exe", "--type=renderer", "--user-data-dir=" + PROFILE])
    procs.append(renderer)
    assert browser.release_dedicated_profile() == 0
    assert not renderer.terminated


def test_processus_inaccessible_ne_casse_rien(procs):
    class Denied(FakeProc):
        def cmdline(self):
            raise psutil.AccessDenied()

    procs.append(Denied(15, "chrome.exe", []))
    assert browser.release_dedicated_profile() == 0
