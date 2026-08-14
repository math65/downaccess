import importlib.machinery
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from app.core.i18n import _translate as _

_log = logging.getLogger("downaccess.updater")


def get_ytdlp_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    return Path(appdata) / "DownAccess" / "yt-dlp"


def _version_key(v: str) -> tuple:
    """Cle de tri numerique d'une version yt-dlp (ex. '2026.3.17').

    Indispensable : un tri lexicographique de chaines classe '2026.3.17' APRES
    '2026.10.5' (car '3' > '1'), ce qui ferait choisir la mauvaise version et
    re-telecharger yt-dlp a chaque demarrage. On compare composant par composant
    en entiers (les parties non numeriques retombent sur 0)."""
    parts = []
    for chunk in str(v or "").split("."):
        num = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


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
            return max(versions, key=_version_key)
    # Fallback venv
    try:
        import importlib.metadata
        return importlib.metadata.version("yt-dlp")
    except Exception:
        return None


def get_latest_version() -> str | None:
    """Derniere version yt-dlp du canal NIGHTLY.

    yt-dlp publie ses builds nightly sur PyPI comme pre-releases (versions
    suffixees `.devN`, ex. '2026.6.30.234726.dev0'). Le canal stable
    (`info.version`) est volontairement ignore : DownAccess suit le nightly pour
    recuperer au plus vite les correctifs d'extracteurs (sites qui cassent).
    On retient la plus recente version nightly disposant d'un wheel non retire ;
    a defaut (aucun nightly), on retombe sur le stable annonce."""
    try:
        url = "https://pypi.org/pypi/yt-dlp/json"
        req = urllib.request.Request(url, headers={"User-Agent": "DownAccess-Updater"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        nightly = [
            ver for ver, files in data.get("releases", {}).items()
            if ".dev" in ver and any(
                f.get("packagetype") == "bdist_wheel" and not f.get("yanked")
                for f in files
            )
        ]
        if nightly:
            return max(nightly, key=_version_key)
        return data.get("info", {}).get("version")
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

        # Comparaison numerique (pas lexicographique) : les versions nightly
        # '2026.6.30.234726.dev0' doivent se comparer composant par composant,
        # et une eventuelle difference de forme (zero-padding) ne doit pas
        # declencher un re-telechargement en boucle.
        if not first_install and current and _version_key(current) >= _version_key(latest):
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
                # --pre + version exacte : force le nightly (pip sans --pre
                # installerait le stable et bouclerait a chaque demarrage).
                result = subprocess.run(
                    [
                        sys.executable, "-m", "pip", "install", "--pre",
                        f"yt-dlp=={latest}",
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

    # Installation ATOMIQUE : on extrait d'abord dans un dossier temporaire (la
    # partie longue/faillible = reseau + extraction), puis on bascule chaque
    # element vers `target` par un deplacement local rapide. Si l'operation est
    # interrompue pendant le telechargement/extraction, l'installation existante
    # reste intacte (avant : rmtree puis extract laissait yt_dlp/ casse en cas
    # de coupure au mauvais moment).
    import tempfile
    staging = Path(tempfile.mkdtemp(dir=str(target), prefix=".staging-"))
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            zf.extractall(staging)
        for item in staging.iterdir():
            dest = target / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest, ignore_errors=True)
                else:
                    try:
                        dest.unlink()
                    except OSError:
                        pass
            shutil.move(str(item), str(dest))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


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


# --- Priorite d'import de yt-dlp --------------------------------------------
#
# L'app embarque une copie de yt-dlp (PyInstaller) ET en installe une plus
# recente dans %APPDATA%\DownAccess\yt-dlp (canal nightly). Faire gagner la
# seconde ne peut PAS se faire avec sys.path seul : en frozen, l'importeur de
# PyInstaller siege dans sys.meta_path et repond AVANT que sys.path ne soit
# consulte. La copie embarquee gagnait donc systematiquement, et les mises a
# jour nightly n'atteignaient jamais l'utilisateur : l'app annoncait la version
# AppData (lue dans le dist-info) tout en executant celle figee au build.
# On installe donc un finder en TETE de sys.meta_path, avant tout import de
# yt_dlp -> voir l'appel dans main.py.

_MANAGED_ROOTS = ("yt_dlp",)

_activated = False


class _AppDataYtDlpFinder:
    """Finder `sys.meta_path` qui resout yt_dlp depuis le dossier AppData.

    Ne repond que pour le paquet yt_dlp (et ses sous-modules) : tout le reste
    est laisse aux finders suivants, dont celui de PyInstaller.
    """

    def __init__(self, ytdlp_dir: Path):
        self._paths = [str(ytdlp_dir)]

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] not in _MANAGED_ROOTS:
            return None
        # Sous-module : `path` est le __path__ du paquet parent, deja resolu
        # dans AppData. Module racine : on cherche dans le dossier AppData.
        search = list(path) if path is not None else self._paths
        return importlib.machinery.PathFinder.find_spec(fullname, search, target)


def get_reference_version() -> str | None:
    """Version de yt-dlp disponible SANS la copie AppData.

    Sert de plancher : on n'active AppData que si elle est plus recente.
    - En frozen : la version embarquee au build, ecrite par downaccess.spec
      dans `_internal/ytdlp_bundled.txt` (les metadonnees du paquet ne sont pas
      embarquees, on ne peut donc pas interroger importlib.metadata).
    - En dev : la version installee dans le venv.
    """
    if getattr(sys, "frozen", False):
        try:
            stamp = Path(getattr(sys, "_MEIPASS", "")) / "ytdlp_bundled.txt"
            return stamp.read_text(encoding="utf-8").strip() or None
        except Exception:
            return None
    try:
        import importlib.metadata

        return importlib.metadata.version("yt-dlp")
    except Exception:
        return None


def activate_appdata_ytdlp() -> str | None:
    """Fait pointer `import yt_dlp` vers la copie AppData quand elle est plus
    recente que celle embarquee. Retourne la version activee, sinon None.

    DOIT etre appele avant le premier `import yt_dlp` du processus.
    """
    global _activated
    if _activated:
        return None

    ytdlp_dir = get_ytdlp_dir()
    if not (ytdlp_dir / "yt_dlp" / "__init__.py").is_file():
        return None  # rien d'installe (ou installation incomplete)

    installed = get_installed_version()
    reference = get_reference_version()
    if installed and reference and _version_key(installed) <= _version_key(reference):
        # La copie embarquee est aussi recente : rien a faire (cas d'une
        # nouvelle version de l'app installee alors que la machine est hors
        # ligne depuis un moment).
        return None

    if "yt_dlp" in sys.modules:
        # Trop tard : un import a deja eu lieu. Ne devrait pas arriver, mais on
        # le trace plutot que d'echouer silencieusement comme avant.
        _log.warning(
            "yt_dlp deja importe avant activate_appdata_ytdlp() : "
            "la version %s d'AppData ne sera pas utilisee.", installed
        )
        return None

    sys.meta_path.insert(0, _AppDataYtDlpFinder(ytdlp_dir))
    _inject_path(ytdlp_dir)  # coherence pour les outils qui lisent sys.path
    _activated = True
    _log.info("yt-dlp %s (AppData) prioritaire sur %s (embarque).",
              installed, reference or "?")
    return installed


def bootstrap(on_update_done=None) -> None:
    """
    Appelé au démarrage :
    - S'assure que la copie AppData de yt-dlp est prioritaire si elle est plus
      recente (normalement deja fait par main.py, avant tout import de yt_dlp).
    - Lance toujours une vérification de mise à jour en arrière-plan.
    """
    activate_appdata_ytdlp()
    _log_effective_ytdlp()
    check_and_update(on_done=on_update_done)


def _log_effective_ytdlp() -> None:
    """Trace la copie de yt-dlp REELLEMENT chargee (version + emplacement).

    Sans cette trace, l'app annoncait la version d'AppData tout en executant
    celle du bundle : l'ecart est passe inapercu pendant six semaines, et les
    rapports d'erreur eux-memes affichaient les deux valeurs sans qu'on les
    rapproche. On la garde pour que le cas soit immediatement visible.
    """
    try:
        import yt_dlp
        _log.info("yt-dlp effectif : %s (%s)",
                  yt_dlp.version.__version__, yt_dlp.__file__)
    except Exception as exc:
        _log.warning("yt-dlp introuvable : %s", exc)
