import csv
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


def _newest_dist_info(ytdlp_dir: Path) -> Path | None:
    """dist-info de la version la plus recente presente dans `ytdlp_dir`."""
    found = []
    for dist_info in ytdlp_dir.glob("yt_dlp-*.dist-info"):
        try:
            with open(dist_info / "METADATA", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Version:"):
                        found.append((line.split(":", 1)[1].strip(), dist_info))
                        break
        except Exception:
            pass
    if not found:
        return None
    return max(found, key=lambda vd: _version_key(vd[0]))[1]


def is_install_complete(ytdlp_dir: Path | None = None) -> bool:
    """La copie AppData de yt-dlp est-elle entiere ?

    On confronte le dossier au RECORD du dist-info (la liste des fichiers du
    wheel) : chaque fichier de `yt_dlp/` qui y figure doit exister.

    Pourquoi : une mise a jour interrompue (l'app fermee pour lancer
    l'installeur de DownAccess pendant que yt-dlp se mettait a jour en
    arriere-plan) laissait un yt_dlp/ a moitie efface. Il etait quand meme
    charge au demarrage suivant, et l'app plantait avant d'afficher sa
    fenetre : « cannot import name 'compat_ord' from 'yt_dlp.compat'
    (unknown location) » — compat/ avait perdu son __init__.py.
    """
    ytdlp_dir = ytdlp_dir or get_ytdlp_dir()
    if not (ytdlp_dir / "yt_dlp" / "__init__.py").is_file():
        return False
    dist_info = _newest_dist_info(ytdlp_dir)
    if dist_info is None:
        return False  # version inconnue : on ne s'y fie pas
    try:
        with open(dist_info / "RECORD", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
    except Exception:
        return False
    expected = [
        row[0] for row in rows
        if row and row[0].startswith("yt_dlp/") and "__pycache__" not in row[0]
    ]
    if not expected:
        return False
    return all((ytdlp_dir / rel).is_file() for rel in expected)


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
        # Une copie incomplete (mise a jour interrompue) est reinstallee meme
        # si sa version est la bonne : c'est ce qui repare l'app toute seule.
        if (not first_install and current
                and _version_key(current) >= _version_key(latest)
                and is_install_complete(target)):
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

    _install_wheel_payload(target, payload)


def _purge_leftovers(target: Path) -> None:
    """Efface les dossiers de travail d'une installation precedente
    interrompue (`.staging-*`, `.old-*`)."""
    for leftover in list(target.glob(".staging-*")) + list(target.glob(".old-*")):
        shutil.rmtree(leftover, ignore_errors=True)


def _rename(src: Path, dst: Path, attempts: int = 5) -> None:
    """os.rename, retente quelques fois : sous Windows, l'antivirus garde
    brievement ouverts les fichiers qu'on vient d'extraire, et le renommage
    du dossier echoue alors en « acces refuse »."""
    import time

    for i in range(attempts):
        try:
            os.rename(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.2 * (i + 1))


def _install_wheel_payload(target: Path, payload: bytes) -> None:
    """Extrait le wheel `payload` et le met en place dans `target`.

    La mise en place ne fait que des RENOMMAGES (instantanes, sur le meme
    disque) : l'ancien element est d'abord ecarte dans `.old-*`, puis le
    nouveau prend sa place. On ne supprime l'ancien qu'une fois le nouveau en
    place.

    Avant, on effacait l'ancien yt_dlp/ (rmtree) PUIS on deplacait le nouveau.
    Si l'app se fermait pendant l'effacement — typiquement pour lancer
    l'installeur de DownAccess, la mise a jour de yt-dlp tournant encore en
    arriere-plan — il restait un yt_dlp/ a moitie efface, qui faisait planter
    l'app a chaque demarrage. Et si l'effacement echouait en partie (fichier
    verrouille par l'antivirus), `shutil.move` rangeait le nouveau DANS l'ancien
    (yt_dlp/yt_dlp/). Desormais, une coupure laisse au pire yt_dlp/ absent :
    l'app retombe sur sa copie embarquee et reinstalle au demarrage suivant.
    """
    import io
    import tempfile
    import zipfile

    _purge_leftovers(target)
    staging = Path(tempfile.mkdtemp(dir=str(target), prefix=".staging-"))
    trash = Path(tempfile.mkdtemp(dir=str(target), prefix=".old-"))
    try:
        # Partie longue et faillible : rien n'est encore touche dans `target`.
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            zf.extractall(staging)
        # Le paquet d'abord, le dist-info en dernier : c'est lui qui annonce
        # la version installee.
        items = sorted(staging.iterdir(), key=lambda p: p.name.endswith(".dist-info"))
        for item in items:
            dest = target / item.name
            parked = trash / item.name
            had_old = dest.exists()
            if had_old:
                _rename(dest, parked)
            try:
                _rename(item, dest)
            except OSError:
                if had_old:
                    try:
                        _rename(parked, dest)  # remet l'ancien en place
                    except OSError:
                        pass
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(trash, ignore_errors=True)


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
        return None  # rien d'installe
    if not is_install_complete(ytdlp_dir):
        # Mise a jour interrompue : on garde la copie embarquee, et
        # check_and_update() reinstalle proprement en arriere-plan.
        _log.warning("Copie AppData de yt-dlp incomplete (%s) : copie embarquee "
                     "utilisee, reinstallation au prochain controle.", ytdlp_dir)
        return None

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

    finder = _AppDataYtDlpFinder(ytdlp_dir)
    sys.meta_path.insert(0, finder)
    # Import d'essai : si la copie AppData ne se charge pas, pour quelque raison
    # que ce soit, on la retire et l'app demarre sur la copie embarquee au lieu
    # de planter avant meme d'afficher sa fenetre.
    try:
        import yt_dlp  # noqa: F401
    except Exception as exc:
        sys.meta_path.remove(finder)
        for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
            del sys.modules[name]
        _log.warning("yt-dlp %s (AppData) ne se charge pas (%s) : copie "
                     "embarquee utilisee.", installed, exc)
        return None
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
