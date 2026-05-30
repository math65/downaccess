"""
Mise à jour automatique de DownAccess.

Flux :
1. Interroger l'API GitHub pour la dernière release
2. Comparer avec la version installée
3. Si nouvelle version : télécharger DownAccess-Setup.exe dans %TEMP%
4. Vérifier que le fichier est complet (taille > 0)
5. Lancer l'installeur et fermer l'app proprement

Sécurités :
- Téléchargement dans un fichier .tmp, renommé seulement si complet
- Vérification taille fichier > 0 avant lancement
- Timeout réseau strict
- L'app ne se ferme que si le processus installeur a bien démarré
- Aucune exception ne peut crasher l'app silencieusement
"""
import hashlib
import os
import subprocess
import tempfile
import threading
from urllib import response
import urllib.request
import urllib.error
import json

from app.version import __version__
from app.core.i18n import _translate as _

GITHUB_API   = "https://api.github.com/repos/math65/downaccess/releases/latest"
ASSET_NAME   = "DownAccess-Setup.exe"
DOWNLOAD_URL = f"https://github.com/math65/downaccess/releases/latest/download/{ASSET_NAME}"
CHECKSUM_URL = DOWNLOAD_URL + ".sha256"
_UA = f"DownAccess/{__version__} (Windows; updater)"


def _fetch_expected_sha256() -> str | None:
    """Récupère le SHA-256 attendu de la release GitHub. Retourne None si absent."""
    try:
        req = urllib.request.Request(CHECKSUM_URL)
        req.add_header("User-Agent", _UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace").strip()
        if not content:
            return None
        # Format sha256sum standard : "<hex>  <filename>" — on prend le premier champ
        return content.split()[0].lower()
    except Exception:
        return None


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower()


# ---------------------------------------------------------------------------
# Comparaison de versions
# ---------------------------------------------------------------------------

def _parse_version(tag: str) -> tuple[int, ...]:
    """'v0.2.1' ou '0.2.1' → (0, 2, 1)"""
    tag = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in tag.split("."))
    except Exception:
        return (0,)


# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------

def check_for_update(on_done) -> None:
    """
    Vérifie en arrière-plan si une nouvelle version est disponible.
    on_done(status, info, release_notes) est appelé dans le thread — utiliser wx.CallAfter côté UI.
      status        : "up_to_date" | "update_available" | "error"
      info          : nouvelle version (str) ou message d'erreur
      release_notes : notes de version (str) ou ""
    """
    def _run():
        try:
            req = urllib.request.Request(GITHUB_API)
            req.add_header("User-Agent", _UA)
            req.add_header("Accept", "application/vnd.github+json")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())

            # Vérifier que la release n'est pas un draft ou pre-release
            if data.get("draft") or data.get("prerelease"):
                on_done("up_to_date", __version__, "")
                return

            tag     = data.get("tag_name", "")
            new_ver = tag.lstrip("v").strip()
            if not new_ver:
                on_done("error", _("Réponse GitHub invalide."), "")
                return

            # Vérifier que l'asset existe bien dans cette release
            assets = [a["name"] for a in data.get("assets", [])]
            if ASSET_NAME not in assets:
                on_done(
                    "error",
                    _("Asset '{asset}' absent de la release {version}.").format(
                        asset=ASSET_NAME, version=new_ver
                    ),
                    "",
                )
                return

            release_notes = data.get("body", "") or ""

            if _parse_version(new_ver) > _parse_version(__version__):
                on_done("update_available", new_ver, release_notes)
            else:
                on_done("up_to_date", __version__, "")

        except urllib.error.URLError:
            on_done("error", _("Impossible de contacter GitHub."), "")
        except Exception as exc:
            on_done("error", str(exc), "")

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Téléchargement et installation
# ---------------------------------------------------------------------------

def download_and_install(new_version: str, on_progress, on_error,
                         on_cancel=None,
                         on_quit=None) -> None:
    """
    Télécharge l'installeur et le lance.

    on_progress(percent: float)  — progression 0-100
    on_error(message: str)       — appelé si échec ; l'app NE se ferme PAS
    on_quit()                    — appelé pour fermer l'app après lancement installeur
    on_cancel()                    — appelé pour fermer la boîte de dialogue si annulation
    """
    cancel_event=threading.Event()
    def _run():
        tmp_path  = os.path.join(tempfile.gettempdir(), ASSET_NAME + ".tmp")
        dest_path = os.path.join(tempfile.gettempdir(), ASSET_NAME)

        # Nettoyer un éventuel résidu de téléchargement précédent
        for path in (tmp_path, dest_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

        try:
            req = urllib.request.Request(DOWNLOAD_URL)
            req.add_header("User-Agent", _UA)
            resp=urllib.request.urlopen(req, timeout=60)
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536  # 64 Ko
            last_pct   = -1
            f=open(tmp_path, "wb")
            while True:
                    if cancel_event.is_set():
                        resp.close()
                        f.close()
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                        if on_cancel:
                            on_cancel()
                            return
                    buf = resp.read(chunk_size)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        if pct != last_pct:
                            on_progress(pct)
                            last_pct = pct
            if not resp.closed:
                resp.close()
            if not f.closed:
                f.close()

        except Exception as exc:
            # Supprimer le fichier partiel
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            on_error(_("Téléchargement échoué : {error}").format(error=exc))
            return

        # Vérifier que le fichier n'est pas vide
        size = os.path.getsize(tmp_path)
        if size < 65536:  # Un installeur fait au minimum 64 Ko
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            on_error(
                _("Fichier téléchargé trop petit ({size} octets) — corrompu ?").format(size=size)
            )
            return

        # Vérification d'intégrité SHA-256 (toujours requise — refus si absent)
        expected_sha = _fetch_expected_sha256()
        if not expected_sha:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            on_error(
                _(
                    "Impossible de récupérer la somme de contrôle (SHA-256) de la nouvelle version.\n"
                    "Mise à jour annulée par sécurité — réessayez plus tard."
                )
            )
            return

        actual_sha = _file_sha256(tmp_path)
        if actual_sha != expected_sha:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            on_error(
                _(
                    "Vérification d'intégrité échouée : le fichier téléchargé ne correspond pas\n"
                    "à la somme de contrôle officielle. Mise à jour annulée par sécurité."
                )
            )
            return

        # Renommer seulement si le téléchargement est complet et vérifié
        try:
            os.rename(tmp_path, dest_path)
        except OSError as exc:
            on_error(_("Impossible de finaliser le fichier : {error}").format(error=exc))
            return

        # Lancer l'installeur
        try:
            proc = subprocess.Popen([dest_path])
        except Exception as exc:
            on_error(_("Impossible de lancer l'installeur : {error}").format(error=exc))
            return

        # Vérifier que le processus a bien démarré
        if proc.poll() is not None:
            on_error(_("L'installeur s'est terminé immédiatement — fichier corrompu ?"))
            return

        # Tout est bon → fermer l'app proprement
        if on_quit:
            on_quit()

    threading.Thread(target=_run, daemon=True).start()
    return cancel_event.set