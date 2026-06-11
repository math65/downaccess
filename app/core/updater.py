import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from app.core.i18n import _translate as _


def get_ytdlp_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    return Path(appdata) / "DownAccess" / "yt-dlp"


def get_installed_version() -> str | None:
    """
    Lit la version depuis le dist-info dans AppData (sans cache importlib).
    S'il y a plusieurs dist-info (ancienne + nouvelle après upgrade), retourne la plus récente.
    Fallback sur importlib.metadata si AppData absent.
    """
    ytdlp_dir = get_ytdlp_dir()
    if ytdlp_dir.exists():
        versions = []
        for dist_info in ytdlp_dir.glob("yt_dlp-*.dist-info"):
            metadata_file = dist_info / "METADATA"
            try:
                with open(metadata_file, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("Version:"):
                            versions.append(line.split(":", 1)[1].strip())
                            break
            except Exception:
                pass
        if versions:
            return max(versions)
    # Fallback venv
    try:
        import importlib.metadata
        return importlib.metadata.version("yt-dlp")
    except Exception:
        return None


def get_latest_version() -> str | None:
    try:
        url = "https://pypi.org/pypi/yt-dlp/json"
        req = urllib.request.Request(url, headers={"User-Agent": "DownAccess-Updater"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        return data["info"]["version"]
    except Exception:
        return None


def check_and_update(on_done=None) -> None:
    """
    Vérifie si yt-dlp est à jour, met à jour si nécessaire.
    on_done(status, info) est appelé depuis le thread worker :
      - ("up_to_date", version)  → déjà à jour, pas de téléchargement
      - ("updated",   version)   → mis à jour avec succès
      - ("installed", version)   → installé pour la première fois
      - ("error",     message)   → échec
    """
    def _run():
        target = get_ytdlp_dir()
        first_install = not target.exists()

        current = get_installed_version()
        latest  = get_latest_version()

        if latest is None:
            # Pas de connexion ou erreur PyPI
            if current:
                # yt-dlp est là, on peut continuer sans mise à jour
                if on_done:
                    on_done("up_to_date", current)
            else:
                if on_done:
                    on_done("error", _("Impossible de vérifier la version (connexion indisponible)."))
            return

        if not first_install and current == latest:
            if on_done:
                on_done("up_to_date", current)
            return

        # Installation ou mise à jour nécessaire
        target.mkdir(parents=True, exist_ok=True)
        try:
            if getattr(sys, "frozen", False):
                # En frozen (PyInstaller), sys.executable == DownAccess.exe :
                # lancer "DownAccess.exe -m pip ..." ne lance PAS pip, ça relance
                # l'application (boucle de demarrage + instances multiples). On
                # telecharge et extrait directement le wheel yt-dlp (zip pur Python).
                _install_wheel(target, latest)
            else:
                result = subprocess.run(
                    [
                        sys.executable, "-m", "pip", "install", "-U", "yt-dlp",
                        "--target", str(target),
                        "--quiet", "--no-warn-script-location",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or _("Erreur inconnue."))
            _inject_path(target)
            _cleanup_old_dist_info(target, latest)
            status = "installed" if first_install else "updated"
            if on_done:
                on_done(status, latest)
        except Exception as exc:
            if on_done:
                on_done("error", str(exc))

    threading.Thread(target=_run, daemon=True).start()


def _install_wheel(target: Path, version: str) -> None:
    """Telecharge le wheel yt-dlp depuis PyPI et l'extrait dans `target`.

    Utilise en frozen (PyInstaller) ou pip n'est pas disponible : un wheel est
    un simple zip dont l'extraction reproduit le resultat de
    `pip install --target` (paquet yt_dlp/ + yt_dlp-<version>.dist-info/).
    """
    import io
    import zipfile

    url = f"https://pypi.org/pypi/yt-dlp/{version}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "DownAccess-Updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    wheel_url = None
    for entry in data.get("urls", []):
        fn = entry.get("filename", "")
        if entry.get("packagetype") == "bdist_wheel" and fn.endswith(".whl"):
            wheel_url = entry["url"]
            break
    if not wheel_url:
        raise RuntimeError(_("Wheel yt-dlp introuvable sur PyPI."))

    wreq = urllib.request.Request(wheel_url, headers={"User-Agent": "DownAccess-Updater"})
    with urllib.request.urlopen(wreq, timeout=120) as r:
        payload = r.read()

    # Nettoyer l'ancienne extraction du paquet pour ne pas laisser de fichiers
    # obsoletes (l'extraction de zip ecrase mais ne supprime pas les disparus).
    pkg_dir = target / "yt_dlp"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir, ignore_errors=True)

    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        zf.extractall(target)


def _cleanup_old_dist_info(ytdlp_dir: Path, keep_version: str) -> None:
    """Supprime les dist-info des anciennes versions après une mise à jour."""
    for dist_info in ytdlp_dir.glob("yt_dlp-*.dist-info"):
        if dist_info.name != f"yt_dlp-{keep_version}.dist-info":
            try:
                shutil.rmtree(dist_info)
            except Exception:
                pass


def _inject_path(ytdlp_dir: Path) -> None:
    path_str = str(ytdlp_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def bootstrap(on_update_done=None) -> None:
    """
    Appelé au démarrage :
    - Injecte la version AppData dans sys.path si elle existe.
    - Lance toujours une vérification de mise à jour en arrière-plan.
    """
    ytdlp_dir = get_ytdlp_dir()
    if ytdlp_dir.exists():
        _inject_path(ytdlp_dir)
    check_and_update(on_done=on_update_done)
