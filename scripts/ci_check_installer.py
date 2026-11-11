"""
ci_check_installer.py — Installe DownAccess-Setup.exe et verifie qu'il demarre.

Usage (Windows) :
    python scripts/ci_check_installer.py installer_output/DownAccess-Setup.exe

Lance par le runner GitHub (.github/workflows/release.yml) AVANT toute
publication : une release n'est creee que si ce script reussit.

Pourquoi pas le smoke test de build.py : il verifie que l'exe tourne encore
apres 4 secondes. Or un plantage au demarrage ouvre la fenetre d'erreur de
PyInstaller (« Traceback… », bouton Close) — le processus reste vivant, et le
test passe. C'est exactement ce qu'a vecu une utilisatrice en 0.2.8. Ici on
attend la preuve que l'app a vraiment demarre : la ligne « yt-dlp effectif »
du journal, ecrite une fois la fenetre principale affichee.

Scenarios, chacun avec son propre %APPDATA% vierge :
  1. Premier lancement : demarre sur le yt-dlp embarque, puis installe le
     nightly dans AppData.
  2. Relance : le nightly d'AppData est bien celui qui est charge.
  3. Mise a jour interrompue (le bug de la 0.2.8) : copie AppData abimee
     (compat/__init__.py absent). L'app doit demarrer quand meme, sur la
     copie embarquee, puis reparer la copie AppData toute seule.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.updater import _version_key, is_install_complete  # noqa: E402

STARTED = "yt-dlp effectif"
START_TIMEOUT = 120    # s : premier lancement d'un exe PyInstaller + antivirus
UPDATE_TIMEOUT = 300   # s : telechargement du nightly depuis PyPI


class CheckFailed(Exception):
    pass


def step(msg: str) -> None:
    print(f"\n>> {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"  OK  {msg}", flush=True)


def kill_all() -> None:
    subprocess.run(["taskkill", "/F", "/T", "/IM", "DownAccess.exe"],
                   capture_output=True)
    time.sleep(2)


def show_windows() -> None:
    """Titre des fenetres DownAccess ouvertes : distingue la fenetre principale
    d'une fenetre d'erreur PyInstaller."""
    subprocess.run([
        "powershell", "-NoProfile", "-Command",
        "Get-Process DownAccess -ErrorAction SilentlyContinue | "
        "Format-Table Id, MainWindowTitle -AutoSize",
    ])


def log_path(appdata: Path) -> Path:
    return appdata / "DownAccess" / "downaccess.log"


def read_log(appdata: Path) -> str:
    try:
        return log_path(appdata).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def dump(appdata: Path) -> None:
    print("----- journal DownAccess -----")
    print(read_log(appdata) or "(vide ou absent)")
    print("----- fenetres -----")
    show_windows()


def launch(exe: Path, appdata: Path) -> subprocess.Popen:
    env = dict(os.environ, APPDATA=str(appdata))
    return subprocess.Popen([str(exe)], env=env, cwd=str(exe.parent))


def wait_started(proc: subprocess.Popen, appdata: Path) -> str:
    """Attend la ligne « yt-dlp effectif » et retourne l'emplacement charge."""
    deadline = time.time() + START_TIMEOUT
    while time.time() < deadline:
        for line in read_log(appdata).splitlines():
            if STARTED in line:
                return line
        if proc.poll() is not None:
            raise CheckFailed(f"l'app s'est arretee (code {proc.returncode})")
        time.sleep(1)
    raise CheckFailed(f"pas de « {STARTED} » apres {START_TIMEOUT} s : "
                      "l'app n'a pas demarre (fenetre d'erreur ?)")


def wait_ytdlp_complete(proc: subprocess.Popen, ytdlp_dir: Path) -> None:
    deadline = time.time() + UPDATE_TIMEOUT
    while time.time() < deadline:
        if is_install_complete(ytdlp_dir):
            time.sleep(3)  # laisse finir le menage (.old-*, dist-info)
            return
        if proc.poll() is not None:
            raise CheckFailed(f"l'app s'est arretee (code {proc.returncode})")
        time.sleep(2)
    raise CheckFailed(f"yt-dlp toujours incomplet dans AppData apres {UPDATE_TIMEOUT} s")


def installed_version(ytdlp_dir: Path) -> str:
    versions = []
    for dist_info in ytdlp_dir.glob("yt_dlp-*.dist-info"):
        for line in (dist_info / "METADATA").read_text(encoding="utf-8").splitlines():
            if line.startswith("Version:"):
                versions.append(line.split(":", 1)[1].strip())
                break
    return max(versions, key=_version_key)


def expect_location(line: str, appdata: Path, want_appdata: bool) -> None:
    in_appdata = str(appdata / "DownAccess" / "yt-dlp").lower() in line.lower()
    if in_appdata != want_appdata:
        where = "AppData" if want_appdata else "embarque (_internal)"
        raise CheckFailed(f"yt-dlp attendu depuis {where}, journal : {line}")


def run_scenario(name: str, exe: Path, appdata: Path, body) -> None:
    step(name)
    proc = launch(exe, appdata)
    try:
        body(proc)
    except CheckFailed:
        dump(appdata)
        raise
    finally:
        proc.kill()
        kill_all()


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    setup = Path(sys.argv[1]).resolve()
    # resolve() : forme longue du chemin. Le TEMP du runner est en nom court
    # (C:\Users\RUNNER~1\...), qui ne se comparerait pas au chemin du journal.
    work = Path(tempfile.mkdtemp(prefix="da-check-")).resolve()
    install_dir = work / "app"

    step(f"Installation silencieuse de {setup.name}...")
    kill_all()
    r = subprocess.run([
        str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
        f"/DIR={install_dir}", f"/LOG={work / 'install.log'}",
    ])
    # L'installeur relance l'app tout seul ([Run] skipifnotsilent) : on la
    # ferme pour repartir de lancements maitrises.
    time.sleep(5)
    kill_all()
    exe = install_dir / "DownAccess.exe"
    if r.returncode != 0 or not exe.exists():
        print((work / "install.log").read_text(encoding="utf-8", errors="replace"))
        print(f"  ERR installation echouee (code {r.returncode})")
        return 1
    ok(f"Installe dans {install_dir}")

    bundled = (install_dir / "_internal" / "ytdlp_bundled.txt").read_text(
        encoding="utf-8").strip()
    ok(f"yt-dlp embarque : {bundled}")

    first = work / "appdata-1"
    first.mkdir()
    first_ytdlp = first / "DownAccess" / "yt-dlp"

    def scenario_first(proc):
        line = wait_started(proc, first)
        expect_location(line, first, want_appdata=False)
        ok("Demarre sur le yt-dlp embarque")
        wait_ytdlp_complete(proc, first_ytdlp)
        ok(f"Nightly installe dans AppData : {installed_version(first_ytdlp)}")

    run_scenario("1. Premier lancement", exe, first, scenario_first)

    nightly = installed_version(first_ytdlp)
    nightly_newer = _version_key(nightly) > _version_key(bundled)

    def scenario_relaunch(proc):
        line = wait_started(proc, first)
        # Le nightly n'est prioritaire que s'il est plus recent que l'embarque.
        expect_location(line, first, want_appdata=nightly_newer)
        ok("Nightly d'AppData charge" if nightly_newer
           else "Nightly = embarque : copie embarquee gardee (normal)")

    run_scenario("2. Relance", exe, first, scenario_relaunch)

    broken = work / "appdata-2"
    broken_ytdlp = broken / "DownAccess" / "yt-dlp"
    shutil.copytree(first / "DownAccess" / "yt-dlp", broken_ytdlp)
    (broken_ytdlp / "yt_dlp" / "compat" / "__init__.py").unlink()

    def scenario_broken(proc):
        line = wait_started(proc, broken)
        expect_location(line, broken, want_appdata=False)
        if "incomplete" not in read_log(broken):
            raise CheckFailed("copie abimee non signalee dans le journal")
        ok("Demarre malgre la copie abimee (repli sur l'embarque)")
        wait_ytdlp_complete(proc, broken_ytdlp)
        ok("Copie AppData reparee toute seule")

    run_scenario("3. Mise a jour interrompue (bug 0.2.8)", exe, broken, scenario_broken)

    print("\nOK  L'installeur demarre dans les 3 scenarios.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckFailed as exc:
        print(f"  ERR {exc}")
        sys.exit(1)
