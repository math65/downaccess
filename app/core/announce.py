"""
Annonces au lancement DownAccess.
Interroge le backend app-backend (route générique /api/announce/check) et, si une
annonce active existe, la remonte à l'UI pour affichage. Confirme l'affichage via
/api/announce/ack. Vérification silencieuse : toute erreur réseau est ignorée.
"""
import json
import logging
import threading
import urllib.error
import urllib.request
from collections.abc import Callable

from app.core.error_reporter import _APP_ID, _BEARER
from app.core.i18n import _translate as _  # noqa: F401  (cohérence app/core)

log = logging.getLogger("downaccess.announce")

CHECK_URL = "https://mathieumartin.ovh/api/announce/check"
ACK_URL   = "https://mathieumartin.ovh/api/announce/ack"


def _post(url: str, payload: dict, timeout: int) -> dict:
    """POST JSON avec auth Bearer, retourne le corps décodé."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Authorization", f"Bearer {_BEARER}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def check_announcement(install_id: str, on_done: Callable[[dict | None], None]) -> None:
    """
    Récupère l'annonce active pour DownAccess en arrière-plan.
    on_done(announcement | None) est appelé depuis le thread — utiliser
    wx.CallAfter côté UI. None = aucune annonce ou erreur (silencieux).
    """
    def _run() -> None:
        try:
            body = _post(CHECK_URL, {"app": _APP_ID, "install_id": install_id}, timeout=8)
            ann = body.get("announcement")
            on_done(ann if isinstance(ann, dict) else None)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.debug("Verification annonce impossible : %s", exc)
            on_done(None)
        except Exception as exc:
            log.debug("Verification annonce : erreur inattendue : %s", exc)
            on_done(None)

    threading.Thread(target=_run, daemon=True).start()


def ack_announcement(install_id: str, ann_id: str) -> None:
    """Confirme l'affichage d'une annonce (fire-and-forget, erreurs ignorées)."""
    def _run() -> None:
        try:
            _post(ACK_URL, {"app": _APP_ID, "install_id": install_id, "id": ann_id}, timeout=8)
        except Exception as exc:
            log.debug("Accuse annonce impossible : %s", exc)

    threading.Thread(target=_run, daemon=True).start()
