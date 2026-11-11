"""
release.py — Bump version, build, génère l'installeur et publie la release GitHub.

Usage :
    python scripts/release.py 0.1.13                 # tout, d'une traite (PC)
    python scripts/release.py 0.1.13 --build-only    # etapes 1-4 (rien n'est publie)
    python scripts/release.py 0.1.13 --publish-only  # etapes 5-6 (installeur deja construit)

Le runner GitHub (.github/workflows/release.yml) enchaine --build-only, la
verification de l'installeur (scripts/ci_check_installer.py), puis
--publish-only : rien n'est publie si l'installeur ne demarre pas.

Les release notes sont prises depuis RELEASE_NOTES.md (FR) et
RELEASE_NOTES.en.md (EN) si presents, concatenes dans le body de la release
GitHub. Sinon, generes depuis git log (commits depuis le dernier tag).

Prérequis :
  - `uv sync` fait (cree .venv avec PyInstaller, utilise par build.py)
  - gh CLI installé et authentifié
  - Inno Setup 6 installé (chemin standard, ou variable ISCC)

Étapes (ordre important — la version DOIT être bumpée AVANT le build,
sinon l'auto-update boucle car l'exe contiendrait l'ancienne version) :
  1. Bumpe la version dans app/version.py et installer/downaccess.iss
  2. Lance scripts/build.py (PyInstaller + smoke test)
  3. Lance Inno Setup → installer_output/DownAccess-Setup.exe
  4. Calcule SHA-256 de l'installeur → DownAccess-Setup.exe.sha256
  5. Commit + push de la version
  6. Crée la release GitHub avec installeur + .sha256 en pièces jointes
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
# Inno Setup : variable ISCC si definie, sinon installation par utilisateur
# (PC de dev), sinon installation systeme (runner GitHub, via choco).
_ISCC_CANDIDATES = [
    Path(r"C:\Users\mathi\AppData\Local\Programs\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def _find_iscc() -> Path:
    import os
    if os.environ.get("ISCC"):
        return Path(os.environ["ISCC"])
    return next((p for p in _ISCC_CANDIDATES if p.exists()), _ISCC_CANDIDATES[0])


ISCC         = _find_iscc()
VENV_PY      = ROOT / ".venv" / "Scripts" / "python.exe"


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


def build(version: str) -> int:
    """Bump, build PyInstaller, installeur et SHA-256. Ne publie rien."""
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

    # 3. Inno Setup
    step("Build installeur Inno Setup...")
    if not ISCC.exists():
        print(f"  ERR ISCC introuvable : {ISCC}")
        print("  -> Installe Inno Setup 6, ou indique son chemin dans la variable ISCC")
        return 1
    (ROOT / "installer_output").mkdir(exist_ok=True)
    run([str(ISCC), str(ISS_FILE)], cwd=ROOT)
    if not INSTALLER.exists():
        print(f"  ERR Installeur non genere : {INSTALLER}")
        return 1
    size_mb = INSTALLER.stat().st_size / 1_048_576
    ok(f"Installeur genere ({size_mb:.1f} Mo)")

    # 4. SHA-256 de l'installeur (verifie par l'auto-updater cote client)
    step("Generation du SHA-256...")
    sha_hex = _file_sha256(INSTALLER)
    SHA_FILE.write_text(f"{sha_hex}  {INSTALLER.name}\n", encoding="utf-8")
    ok(f"SHA-256 : {sha_hex}")
    return 0


def publish(version: str) -> int:
    """Commit + push de la version, puis release GitHub (installeur + .sha256)."""
    tag = f"v{version}"
    if not (INSTALLER.exists() and SHA_FILE.exists()):
        print("  ERR Installeur ou .sha256 absent : lancer d'abord --build-only")
        return 1

    # Notes oubliees = notes de la version precedente publiees telles quelles.
    # Sur le runner (lance depuis un telephone), personne ne relit la sortie :
    # on refuse plutot que de publier des notes perimees.
    for rn in (ROOT / "RELEASE_NOTES.md", ROOT / "RELEASE_NOTES.en.md"):
        if rn.exists():
            first = rn.read_text(encoding="utf-8").strip().splitlines()[:1]
            if not first or f"DownAccess {version}" not in first[0]:
                print(f"  ERR {rn.name} ne commence pas par « ## DownAccess {version} » :"
                      " notes de version pas a jour ?")
                return 1

    # Les notes AVANT le commit de version : en repli sur git log, elles
    # listent les commits depuis le dernier tag.
    step("Generation des release notes...")
    notes = _generate_notes(tag)
    try:
        print(notes)
    except UnicodeEncodeError:
        print(notes.encode("ascii", errors="replace").decode())
    ok("Release notes generees")

    step("Commit et push...")
    run(["git", "add", str(VERSION_PY), str(ISS_FILE)], cwd=ROOT)
    # Version deja bumpee et commitee a la main : rien a commiter, et
    # `git commit` echouerait (code 1).
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        run(["git", "commit", "-m", f"chore: version {version}"], cwd=ROOT)
    else:
        ok("Version deja commitee, rien a ajouter")
    # HEAD explicite : sur le runner, la branche n'a pas forcement d'amont.
    run(["git", "push", "origin", "HEAD"], cwd=ROOT)
    ok("Commit pousse")

    step(f"Creation de la release GitHub {tag}...")
    run([
        "gh", "release", "create", tag,
        str(INSTALLER), str(SHA_FILE),
        "--title", f"DownAccess {tag}",
        "--notes", notes,
        "--target", subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip(),
    ], cwd=ROOT)
    ok(f"Release {tag} publiee sur GitHub")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    unknown = flags - {"--build-only", "--publish-only"}
    if len(args) != 1 or unknown or flags == {"--build-only", "--publish-only"}:
        print("Usage : python scripts/release.py <version> [--build-only | --publish-only]")
        print("  Ex  : python scripts/release.py 0.1.13")
        return 1

    version = args[0].lstrip("v")
    if "--publish-only" not in flags:
        if build(version):
            return 1
    if "--build-only" in flags:
        print(f"\nOK  Installeur {version} pret (non publie) : {INSTALLER}")
        return 0
    if publish(version):
        return 1
    print(f"\nOK  Release v{version} terminee avec succes !")
    return 0


if __name__ == "__main__":
    sys.exit(main())
