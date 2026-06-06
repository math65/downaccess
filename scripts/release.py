"""
release.py — Bump version, build, génère l'installeur et publie la release GitHub.

Usage :
    python scripts/release.py 0.1.13

Les release notes sont prises depuis RELEASE_NOTES.md (FR) et
RELEASE_NOTES.en.md (EN) si presents, concatenes dans le body de la release
GitHub. Sinon, generes depuis git log (commits depuis le dernier tag).

Prérequis :
  - venv activé (pour PyInstaller via build.py)
  - gh CLI installé et authentifié
  - Inno Setup 6 installé dans le chemin standard

Étapes (ordre important — la version DOIT être bumpée AVANT le build,
sinon l'auto-update boucle car l'exe contiendrait l'ancienne version) :
  1. Bumpe la version dans app/version.py et installer/downaccess.iss
  2. Lance scripts/build.py (PyInstaller + smoke test)
  3. Génère les release notes
  4. Commit + push
  5. Lance Inno Setup → installer_output/DownAccess-Setup.exe
  6. Calcule SHA-256 de l'installeur → DownAccess-Setup.exe.sha256
  7. Crée la release GitHub avec installeur + .sha256 en pièces jointes
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT         = Path(__file__).parent.parent
EXE          = ROOT / "dist" / "DownAccess" / "DownAccess.exe"
VERSION_PY   = ROOT / "app" / "version.py"
ISS_FILE     = ROOT / "installer" / "downaccess.iss"
INSTALLER    = ROOT / "installer_output" / "DownAccess-Setup.exe"
SHA_FILE     = ROOT / "installer_output" / "DownAccess-Setup.exe.sha256"
BUILD_PY     = ROOT / "scripts" / "build.py"
ISCC         = Path(r"C:\Users\mathi\AppData\Local\Programs\Inno Setup 6\ISCC.exe")
VENV_PY      = ROOT / "venv" / "Scripts" / "python.exe"


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    cmd_str = ' '.join(str(c) for c in cmd)
    try:
        print(f"  $ {cmd_str}")
    except UnicodeEncodeError:
        print(f"  $ {cmd_str.encode('ascii', errors='replace').decode()}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"  ERR Echec (code {r.returncode})")
        sys.exit(1)
    return r


def step(msg: str) -> None:
    print(f"\n>> {msg}")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _generate_notes(tag: str) -> str:
    """
    Genere les release notes.
    Priorite :
      1. RELEASE_NOTES.md (FR) + RELEASE_NOTES.en.md (EN) a la racine,
         concatenes avec separateur de langue
      2. Auto-genere depuis git log (commits depuis le dernier tag)
    """
    rn_fr = ROOT / "RELEASE_NOTES.md"
    rn_en = ROOT / "RELEASE_NOTES.en.md"

    if rn_fr.exists() or rn_en.exists():
        # Avertir si l'un des deux est en retard sur l'autre
        if rn_fr.exists() and rn_en.exists():
            mt_diff = abs(rn_fr.stat().st_mtime - rn_en.stat().st_mtime)
            if mt_diff > 60 * 60:  # plus d'une heure d'ecart
                older = "RELEASE_NOTES.md" if rn_fr.stat().st_mtime < rn_en.stat().st_mtime else "RELEASE_NOTES.en.md"
                print(f"  WARN {older} semble plus ancien que sa contrepartie — pense a le mettre a jour.")
        elif rn_fr.exists():
            print("  WARN RELEASE_NOTES.en.md absent — la release sera FR uniquement.")
        else:
            print("  WARN RELEASE_NOTES.md absent — la release sera EN uniquement.")

        # Chaque langue est precedee d'un marqueur HTML invisible sur GitHub
        # ('<!-- notes:fr -->'). L'app (app_updater._select_notes_for_language)
        # s'en sert pour n'afficher que la section de la langue courante.
        parts = []
        if rn_fr.exists():
            parts.append("<!-- notes:fr -->\n" + rn_fr.read_text(encoding="utf-8").strip())
        if rn_en.exists():
            parts.append("<!-- notes:en -->\n" + rn_en.read_text(encoding="utf-8").strip())
        notes = "\n\n".join(parts)
        print("  (source : RELEASE_NOTES.md + RELEASE_NOTES.en.md)")
        return notes

    # Auto-generation depuis git log
    print(f"  (source : git log automatique)")
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=ROOT, capture_output=True, text=True,
    )
    last_tag = result.stdout.strip() if result.returncode == 0 else ""
    ref = f"{last_tag}..HEAD" if last_tag else "HEAD"
    log = subprocess.run(
        ["git", "log", ref, "--pretty=format:- %s", "--no-merges"],
        cwd=ROOT, capture_output=True, text=True,
    )
    commits = log.stdout.strip()

    ffmpeg_ver = ""
    vf = ROOT / "assets" / "ffmpeg_version.txt"
    if vf.exists():
        for line in vf.read_text(encoding="utf-8").splitlines():
            if line.startswith("updated="):
                ffmpeg_ver = line.split("=", 1)[1]

    notes = f"## DownAccess {tag}\n\n"
    if commits:
        notes += "### Changements\n" + commits + "\n"
    else:
        notes += "- Mise a jour interne\n"
    if ffmpeg_ver:
        notes += f"\n### Dependances\n- ffmpeg : {ffmpeg_ver}\n"
    return notes


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage : python scripts/release.py <version>")
        print("  Ex  : python scripts/release.py 0.1.13")
        return 1

    version = sys.argv[1].lstrip("v")
    tag     = f"v{version}"

    # 1. Bumper version AVANT le build (l'exe doit contenir la nouvelle version)
    step(f"Bump version -> {version}...")
    content = VERSION_PY.read_text(encoding="utf-8")
    content = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{version}"', content)
    VERSION_PY.write_text(content, encoding="utf-8")
    ok(f"app/version.py -> {version}")

    content = ISS_FILE.read_text(encoding="utf-8")
    content = re.sub(r'AppVersion=[\d.]+', f'AppVersion={version}', content)
    ISS_FILE.write_text(content, encoding="utf-8")
    ok(f"installer/downaccess.iss -> {version}")

    # 2. Build (PyInstaller + smoke test)
    step("Build PyInstaller...")
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    run([py, str(BUILD_PY)], cwd=ROOT)
    if not EXE.exists():
        print(f"  ERR Exe introuvable apres build : {EXE}")
        return 1
    ok(f"Exe genere : {EXE}")

    # 3. Generer les release notes
    step("Generation des release notes...")
    notes = _generate_notes(tag)
    try:
        print(notes)
    except UnicodeEncodeError:
        print(notes.encode("ascii", errors="replace").decode())
    ok("Release notes generees")

    # 4. Commit + push
    step("Commit et push...")
    run(["git", "add", str(VERSION_PY), str(ISS_FILE)], cwd=ROOT)
    run(["git", "commit", "-m", f"chore: version {version}"], cwd=ROOT)
    run(["git", "push"], cwd=ROOT)
    ok("Commit pousse")

    # 5. Inno Setup
    step("Build installeur Inno Setup...")
    if not ISCC.exists():
        print(f"  ERR ISCC introuvable : {ISCC}")
        print("  -> Installe Inno Setup 6 ou verifie le chemin dans ce script")
        return 1
    (ROOT / "installer_output").mkdir(exist_ok=True)
    run([str(ISCC), str(ISS_FILE)], cwd=ROOT)
    if not INSTALLER.exists():
        print(f"  ERR Installeur non genere : {INSTALLER}")
        return 1
    size_mb = INSTALLER.stat().st_size / 1_048_576
    ok(f"Installeur genere ({size_mb:.1f} Mo)")

    # 6. SHA-256 de l'installeur (verifie par l'auto-updater cote client)
    step("Generation du SHA-256...")
    sha_hex = _file_sha256(INSTALLER)
    SHA_FILE.write_text(f"{sha_hex}  {INSTALLER.name}\n", encoding="utf-8")
    ok(f"SHA-256 : {sha_hex}")

    # 7. Release GitHub (installeur + .sha256)
    step(f"Creation de la release GitHub {tag}...")
    run([
        "gh", "release", "create", tag,
        str(INSTALLER), str(SHA_FILE),
        "--title", f"DownAccess {tag}",
        "--notes", notes,
    ], cwd=ROOT)
    ok(f"Release {tag} publiee sur GitHub")

    print(f"\nOK  Release {tag} terminee avec succes !")
    return 0


if __name__ == "__main__":
    sys.exit(main())
