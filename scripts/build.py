"""
build.py — Build PyInstaller + test de fumée.

Usage :
    python scripts/build.py

Étapes :
  1. Vérifie que assets/ffmpeg.exe existe
  2. Lance PyInstaller (downaccess.spec)
  3. Vérifie que dist/DownAccess/DownAccess.exe existe
  4. Affiche la taille du bundle
  5. Smoke test : lance l'exe 4 secondes et vérifie qu'il ne crash pas
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT      = Path(__file__).parent.parent
FFMPEG    = ROOT / "assets" / "ffmpeg.exe"
SPEC      = ROOT / "downaccess.spec"
EXE       = ROOT / "dist" / "DownAccess" / "DownAccess.exe"
BUNDLE    = ROOT / "dist" / "DownAccess"
VENV_PY   = ROOT / ".venv" / "Scripts" / "python.exe"


def _size(path: Path) -> str:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return f"{total / 1_048_576:.1f} Mo"


def step(msg: str) -> None:
    print(f"\n>> {msg}")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> int:
    print(f"  ERR {msg}")
    return 1


def main() -> int:
    # 1. Vérifier ffmpeg
    step("Vérification de assets/ffmpeg.exe…")
    if not FFMPEG.exists():
        return fail(
            "assets/ffmpeg.exe introuvable.\n"
            "  → Lance d'abord : python scripts/update_ffmpeg.py"
        )
    ok(f"ffmpeg trouvé ({FFMPEG.stat().st_size / 1_048_576:.1f} Mo)")

    py = str(VENV_PY) if VENV_PY.exists() else sys.executable

    # 2. Suite de tests : un build ne doit jamais partir sur du code casse.
    #    Les tests reseau sont exclus (marqueur `network`) pour ne pas dependre
    #    d'un site tiers au moment du build.
    step("Suite de tests…")
    rc = subprocess.run([py, "-m", "pytest", "-q"], cwd=ROOT)
    if rc.returncode != 0:
        return fail("Des tests echouent — build interrompu")
    ok("Tests passes")

    # 3. Generer les guides HTML embarques (depuis docs/*.md)
    step("Generation des guides HTML…")
    rc = subprocess.run([py, "scripts/build_docs.py"], cwd=ROOT)
    if rc.returncode != 0:
        return fail("La generation des guides HTML a echoue")
    ok("Guides HTML generes")

    # 4. PyInstaller
    step("Build PyInstaller…")
    result = subprocess.run(
        [py, "-m", "PyInstaller", str(SPEC), "--noconfirm"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        return fail(f"PyInstaller a échoué (code {result.returncode})")
    ok("PyInstaller terminé")

    # 5. Vérifier l'exe
    step("Vérification du bundle…")
    if not EXE.exists():
        return fail(f"Exe introuvable : {EXE}")
    size = _size(BUNDLE)
    ok(f"Exe trouvé — taille du bundle : {size}")

    # 6. Smoke test
    step("Smoke test (4 secondes)…")
    proc = subprocess.Popen([str(EXE)], cwd=ROOT)
    time.sleep(4)
    code = proc.poll()
    if code is not None:
        return fail(f"L'exe s'est arrêté avec le code {code} — crash probable")
    proc.terminate()
    ok("L'exe a tourné 4 secondes sans crash")

    print("\nBuild OK — prêt pour la release.")
    print(f"   Exe : {EXE}")
    print(f"   Taille bundle : {size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
