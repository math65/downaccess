"""Installation de la copie AppData de yt-dlp : robustesse aux coupures.

Regression vecue (novembre 2026, 0.2.8) : la personne accepte la mise a jour de
DownAccess au demarrage. L'app se ferme pour lancer l'installeur alors que la
mise a jour de yt-dlp tourne encore en arriere-plan, en plein effacement de
l'ancien yt_dlp/. Il reste un dossier a moitie vide, charge quand meme a chaque
demarrage : l'app plante avant sa fenetre avec
« cannot import name 'compat_ord' from 'yt_dlp.compat' (unknown location) »
(compat/ avait perdu son __init__.py), sans autre choix que « Close ».

Les tests utilisent un faux wheel minimal, construit en memoire (hors ligne).
"""

import io
import sys
import zipfile

import pytest

from app.core import updater

FAKE_VERSION = "2099.1.1.000000.dev0"  # toujours plus recent que l'embarque


def make_wheel(version=FAKE_VERSION, init_body="__version__ = 'fake'\n"):
    files = {
        "yt_dlp/__init__.py": init_body,
        "yt_dlp/compat/__init__.py": "def compat_ord(c):\n    return c\n",
        "yt_dlp/aes.py": "from .compat import compat_ord\n",
    }
    dist = f"yt_dlp-{version}.dist-info"
    files[f"{dist}/METADATA"] = f"Metadata-Version: 2.1\nName: yt-dlp\nVersion: {version}\n"
    record = "".join(f"{path},sha256=x,1\n" for path in files) + f"{dist}/RECORD,,\n"
    files[f"{dist}/RECORD"] = record
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, body in files.items():
            zf.writestr(path, body)
    return buf.getvalue()


@pytest.fixture
def ytdlp_dir(appdata):
    target = updater.get_ytdlp_dir()
    target.mkdir(parents=True)
    return target


@pytest.fixture
def clean_import_state(monkeypatch):
    """Rejoue activate_appdata_ytdlp() comme au demarrage : yt_dlp pas encore
    importe, aucun finder installe. Tout est restaure apres le test."""
    for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(updater, "_activated", False)
    yield
    for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
        del sys.modules[name]


def _has_appdata_finder():
    return any(isinstance(f, updater._AppDataYtDlpFinder) for f in sys.meta_path)


class TestIntegrite:
    def test_installation_complete(self, ytdlp_dir):
        updater._install_wheel_payload(ytdlp_dir, make_wheel())
        assert updater.is_install_complete(ytdlp_dir)

    def test_compat_sans_init_est_detecte(self, ytdlp_dir):
        """L'etat exact laisse chez la personne : compat/ existe, vide."""
        updater._install_wheel_payload(ytdlp_dir, make_wheel())
        (ytdlp_dir / "yt_dlp" / "compat" / "__init__.py").unlink()
        assert not updater.is_install_complete(ytdlp_dir)

    def test_sans_dist_info_on_ne_s_y_fie_pas(self, ytdlp_dir):
        (ytdlp_dir / "yt_dlp").mkdir()
        (ytdlp_dir / "yt_dlp" / "__init__.py").write_text("")
        assert not updater.is_install_complete(ytdlp_dir)


class TestMiseEnPlace:
    def test_repare_une_installation_cassee(self, ytdlp_dir):
        updater._install_wheel_payload(ytdlp_dir, make_wheel("2099.1.1"))
        (ytdlp_dir / "yt_dlp" / "compat" / "__init__.py").unlink()

        updater._install_wheel_payload(ytdlp_dir, make_wheel(FAKE_VERSION))

        assert updater.is_install_complete(ytdlp_dir)
        assert not (ytdlp_dir / "yt_dlp" / "yt_dlp").exists()  # pas d'imbrication
        assert not list(ytdlp_dir.glob(".staging-*"))
        assert not list(ytdlp_dir.glob(".old-*"))

    def test_echec_du_renommage_remet_l_ancien(self, ytdlp_dir, monkeypatch):
        updater._install_wheel_payload(ytdlp_dir, make_wheel("2099.1.1"))
        real_rename = updater._rename

        def flaky(src, dst, attempts=5):
            if ".staging-" in str(src):
                raise OSError("disque plein")
            real_rename(src, dst, attempts)

        monkeypatch.setattr(updater, "_rename", flaky)
        with pytest.raises(OSError):
            updater._install_wheel_payload(ytdlp_dir, make_wheel(FAKE_VERSION))

        assert updater.is_install_complete(ytdlp_dir)
        assert updater.get_installed_version() == "2099.1.1"

    def test_coupure_entre_deux_renommages(self, ytdlp_dir, monkeypatch):
        """Le pire cas restant : l'ancien yt_dlp/ ecarte, l'app tuee avant que
        le nouveau soit en place. yt_dlp/ est absent -> copie embarquee, et la
        verification suivante reinstalle."""
        updater._install_wheel_payload(ytdlp_dir, make_wheel("2099.1.1"))
        calls = []
        real_rename = updater._rename

        def killed(src, dst, attempts=5):
            calls.append(src)
            if len(calls) == 2:
                raise SystemExit  # simule la fermeture brutale
            real_rename(src, dst, attempts)

        monkeypatch.setattr(updater, "_rename", killed)
        with pytest.raises(SystemExit):
            updater._install_wheel_payload(ytdlp_dir, make_wheel(FAKE_VERSION))

        assert not (ytdlp_dir / "yt_dlp").exists()
        assert not updater.is_install_complete(ytdlp_dir)


class TestActivation:
    def test_copie_cassee_ignoree_au_demarrage(self, ytdlp_dir, clean_import_state):
        """Le coeur du bug : la copie cassee ne doit plus etre chargee."""
        updater._install_wheel_payload(ytdlp_dir, make_wheel())
        (ytdlp_dir / "yt_dlp" / "compat" / "__init__.py").unlink()

        assert updater.activate_appdata_ytdlp() is None
        assert not _has_appdata_finder()

    def test_copie_qui_ne_s_importe_pas(self, ytdlp_dir, clean_import_state):
        """Fichiers complets mais import en echec : repli sur l'embarquee."""
        updater._install_wheel_payload(
            ytdlp_dir, make_wheel(init_body="from .compat import absent\n"))

        assert updater.activate_appdata_ytdlp() is None
        assert not _has_appdata_finder()
        assert "yt_dlp" not in sys.modules

    def test_copie_saine_activee(self, ytdlp_dir, clean_import_state):
        updater._install_wheel_payload(ytdlp_dir, make_wheel())

        assert updater.activate_appdata_ytdlp() == FAKE_VERSION
        assert _has_appdata_finder()
        assert sys.modules["yt_dlp"].__version__ == "fake"


class TestReinstallation:
    def test_copie_incomplete_reinstallee_meme_a_jour(self, ytdlp_dir, monkeypatch):
        """Meme version que PyPI, mais incomplete : on reinstalle (avant, l'app
        la declarait « a jour » et restait cassee indefiniment)."""
        updater._install_wheel_payload(ytdlp_dir, make_wheel())
        (ytdlp_dir / "yt_dlp" / "compat" / "__init__.py").unlink()

        installed = []
        monkeypatch.setattr(updater, "get_latest_version", lambda: FAKE_VERSION)
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(updater, "_install_wheel",
                            lambda target, v: updater._install_wheel_payload(target, make_wheel(v)))
        monkeypatch.setattr(updater, "_inject_path", lambda d: installed.append(d))

        results = []
        done = __import__("threading").Event()

        def on_done(status, info):
            results.append((status, info))
            done.set()

        updater.check_and_update(on_done=on_done)
        assert done.wait(5)
        assert results == [("updated", FAKE_VERSION)]
        assert updater.is_install_complete(ytdlp_dir)
