"""Moteur WebView2 de Windows pour l'extraction guidée.

Jusqu'ici l'extraction guidée lançait un vrai Chrome (ou Edge, ou Brave)
installé sur la machine. Ce module permet d'utiliser à la place **WebView2**,
le moteur de navigateur que Microsoft livre avec Windows — sans dépendre d'un
navigateur installé par l'utilisateur.

## Comment ça marche

WebView2 n'est qu'un moteur : il n'a ni fenêtre, ni barre d'adresse, et ne se
lance pas seul. Il faut une application qui l'accueille. C'est le rôle de la
fonction `run_host()` de ce fichier, qui tourne dans un **processus séparé** :
`webview.start()` s'empare de la boucle de messages WinForms et ne peut donc
pas cohabiter avec `wx.MainLoop()` dans le même processus.

Ce processus hôte ouvre un port de débogage (CDP, le même protocole que celui
par lequel on pilote Chrome), et DownAccess s'y attache avec DrissionPage —
exactement comme il s'attache à Chrome aujourd'hui. Tout le code d'extraction
(écoute réseau, interception, cookies, injection JS) fonctionne sans la moindre
modification : c'est le même protocole, parce que c'est le même moteur.

    DownAccess (wx)  ──CDP──>  processus hôte
                                  └── WebView2 (moteur de Windows)

## Pas de WebView2 sur la machine ?

`is_runtime_available()` le dit, et l'appelant retombe sur le navigateur
installé (`app/core/browser.py`). Rien n'est perdu, aucun message d'erreur à
afficher : c'est le chemin qui a toujours existé.
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request

_log = logging.getLogger("downaccess.webview_host")

# Repere en ligne de commande : DownAccess se relance lui-meme avec ce drapeau
# pour jouer le role d'hote. Evite d'empaqueter un second executable — le
# bundle PyInstaller contient deja tout ce qu'il faut.
HOST_FLAG = "--da-webview-host"

# Identifiant du runtime WebView2 dans le registre (constante Microsoft).
_RUNTIME_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
_RUNTIME_KEYS = (
    (r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients", "HKLM"),
    (r"SOFTWARE\Microsoft\EdgeUpdate\Clients", "HKLM"),
    (r"SOFTWARE\Microsoft\EdgeUpdate\Clients", "HKCU"),
)

# Delai d'ouverture du port. Le premier lancement cree le profil et demarre le
# moteur : c'est la fois la plus lente.
_PORT_TIMEOUT = 30.0


class WebViewUnavailable(RuntimeError):
    """Le moteur WebView2 n'est pas utilisable sur cette machine."""


# ------------------------------------------------------------------
# Disponibilite
# ------------------------------------------------------------------

def runtime_version() -> str:
    """Version du runtime WebView2 installé, ou chaîne vide s'il est absent."""
    if sys.platform != "win32":
        return ""
    try:
        import winreg
    except ImportError:
        return ""
    roots = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    for path, root in _RUNTIME_KEYS:
        try:
            with winreg.OpenKey(roots[root], f"{path}\\{_RUNTIME_GUID}") as key:
                version, _type = winreg.QueryValueEx(key, "pv")
                if version and version != "0.0.0.0":
                    return str(version)
        except OSError:
            continue
    return ""


def is_runtime_available() -> bool:
    """WebView2 est-il installé ? Windows 10/11 le livrent avec Edge."""
    return bool(runtime_version())


def profile_dir() -> str:
    """Dossier de profil WebView2 dédié à DownAccess (persistant).

    Distinct du profil du navigateur installé (`browser.downaccess_profile_dir`)
    : ce sont deux moteurs différents, avec deux formats de stockage. Persistant
    quand même, pour que l'utilisateur reste connecté d'une extraction à l'autre.
    """
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "DownAccess", "WebView2Profile")


# ------------------------------------------------------------------
# Cote DownAccess : lancer l'hote et attendre son port
# ------------------------------------------------------------------

def _free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _host_command(port: int, url: str, title: str) -> list[str]:
    """Ligne de commande du processus hôte.

    En frozen, on relance l'exécutable de DownAccess avec `HOST_FLAG` : le
    bundle embarque déjà pywebview, inutile d'empaqueter un second programme.
    En développement, on relance l'interpréteur sur `main.py`.
    """
    args = [HOST_FLAG, "--port", str(port), "--url", url,
            "--title", title, "--profile", profile_dir()]
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    main_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "main.py")
    return [sys.executable, main_py, *args]


def _cdp_answers(port: int) -> bool:
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=1) as resp:
            json.loads(resp.read().decode("utf-8", "replace"))
        return True
    except Exception:
        return False


def start_host(url: str, title: str = "DownAccess", *,
               timeout: float = _PORT_TIMEOUT) -> tuple[subprocess.Popen, str]:
    """Lance le processus hôte et attend que son port CDP réponde.

    Retourne `(processus, "127.0.0.1:port")`. L'adresse se donne telle quelle à
    `ChromiumOptions.set_address()`.

    Lève `WebViewUnavailable` si le runtime manque, si l'hôte meurt au
    démarrage, ou si le port n'ouvre pas dans le délai imparti — dans tous les
    cas l'appelant retombe sur le navigateur installé.
    """
    if not is_runtime_available():
        raise WebViewUnavailable("Runtime WebView2 absent de cette machine.")

    port = _free_port()
    cmd = _host_command(port, url, title)
    _log.info("Lancement de l'hote WebView2 sur le port %d", port)

    creationflags = 0
    if sys.platform == "win32":
        # Pas de console noire qui clignote devant l'utilisateur.
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(cmd, creationflags=creationflags,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise WebViewUnavailable(f"Hote WebView2 non lancable : {exc}") from exc

    debut = time.monotonic()
    while time.monotonic() - debut < timeout:
        if proc.poll() is not None:
            raise WebViewUnavailable(
                f"L'hote WebView2 s'est arrete (code {proc.returncode}).")
        if _cdp_answers(port):
            _log.info("Hote WebView2 pret apres %.1f s", time.monotonic() - debut)
            return proc, f"127.0.0.1:{port}"
        time.sleep(0.25)

    stop_host(proc)
    raise WebViewUnavailable(
        f"L'hote WebView2 n'a pas ouvert son port en {timeout:.0f} s.")


def stop_host(proc: subprocess.Popen | None) -> None:
    """Ferme le processus hôte, sans jamais lever."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ------------------------------------------------------------------
# Cote hote : la fenetre qui heberge le moteur
# ------------------------------------------------------------------

def _parse_host_args(argv: list[str]) -> dict:
    """Petit analyseur maison : `argparse` afficherait une aide sur stderr et
    quitterait sur un argument inattendu, dans un processus sans console."""
    valeurs = {"port": 0, "url": "about:blank", "title": "DownAccess",
               "profile": profile_dir()}
    for i, arg in enumerate(argv):
        cle = arg.lstrip("-")
        if cle in valeurs and i + 1 < len(argv):
            valeurs[cle] = argv[i + 1]
    valeurs["port"] = int(valeurs["port"] or 0)
    return valeurs


def run_host(argv: list[str] | None = None) -> int:
    """Point d'entrée du processus hôte. Ne rend la main qu'à la fermeture.

    Appelé depuis `main.py` AVANT tout import de wxPython : ce processus-ci ne
    doit rien savoir de l'interface de DownAccess.
    """
    args = _parse_host_args(argv if argv is not None else sys.argv[1:])
    import webview

    # C'est cette ligne qui ouvre le port CDP : pywebview la traduit en
    # `--remote-debugging-port` dans les arguments du moteur WebView2.
    webview.settings["REMOTE_DEBUGGING_PORT"] = args["port"]

    webview.create_window(args["title"], args["url"], width=1100, height=760)
    # private_mode=False + storage_path : le profil survit a la fermeture, donc
    # l'utilisateur reste connecte aux sites d'une extraction a l'autre.
    webview.start(private_mode=False, storage_path=args["profile"])
    return 0
