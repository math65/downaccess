"""
Détection du navigateur Chromium disponible sur le système.
Utilisé par l'extraction guidée et le dialogue de connexion.
"""
import os
import socket

from app.core.i18n import _translate


def _free_port() -> int:
    """Trouve un port TCP local libre (pour le débogage Chrome dédié)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]



# Chemins classiques Windows (Chrome → Edge → Brave)
_CANDIDATES = [
    # Chrome
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    # Edge (présent sur tout Windows 10/11)
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    # Brave
    os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
]


def find_browser() -> str | None:
    """Retourne le chemin du premier navigateur Chromium trouvé, ou None."""
    for path in _CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def browser_name(path: str) -> str:
    """Retourne un nom lisible à partir du chemin de l'exécutable."""
    low = path.lower()
    if "chrome" in low:
        return "Chrome"
    if "edge" in low or "msedge" in low:
        return "Edge"
    if "brave" in low:
        return "Brave"
    return "Navigateur"


def downaccess_profile_dir() -> str:
    """Dossier de profil navigateur dédié à DownAccess (persistant).

    L'utilisateur s'y connecte une seule fois via le dialogue de connexion ;
    les cookies y sont conservés et relus par yt-dlp (cookiesfrombrowser).
    Profil isolé = aucun conflit avec le navigateur habituel de l'utilisateur,
    qu'il soit ouvert ou non.
    """
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "DownAccess", "BrowserProfile")


def open_dedicated_browser(url: str):
    """Lance le navigateur dédié à DownAccess (profil isolé persistant) et
    navigue vers `url`. Retourne l'objet ChromiumPage de DrissionPage.

    Lève RuntimeError (message traduit) si aucun navigateur compatible.
    Le profil dédié n'entre jamais en conflit avec le navigateur habituel de
    l'utilisateur, qu'il soit ouvert ou non.
    """
    bp = find_browser()
    if not bp:
        raise RuntimeError(_translate(
            "Aucun navigateur compatible trouvé.\n"
            "Installez Google Chrome, Microsoft Edge ou Brave."
        ))
    from DrissionPage import ChromiumOptions, ChromiumPage
    co = ChromiumOptions()
    co.set_browser_path(bp)
    # Profil dédié et PERSISTANT (l'utilisateur reste connecté d'une fois sur
    # l'autre). NE PAS utiliser auto_port() : il écrase set_user_data_path() par
    # un dossier temporaire qu'il supprime à la déconnexion (cf. DrissionPage
    # handle_options / _on_disconnect) -> le profil dédié ne persisterait jamais.
    # On choisit donc un port libre nous-mêmes + un user-data-path fixe ; le port
    # distinct permet de coexister avec le navigateur habituel de l'utilisateur.
    co.set_user_data_path(downaccess_profile_dir())
    co.set_local_port(_free_port())
    page = ChromiumPage(co)
    page.get(url)
    return page


def harvest_cookies(page) -> list[dict]:
    """Récolte TOUS les cookies de la session navigateur via CDP.

    `all_domains=True` est indispensable : l'authentification YouTube s'étend
    sur `.youtube.com` ET `.google.com`. `all_info=True` fournit les champs
    complets (domain, path, expires, httpOnly, secure, session).
    """
    raw = page.cookies(all_domains=True, all_info=True)
    return [dict(c) for c in raw]


def harvest_cookies_headless() -> list[dict]:
    """Récolte les cookies du profil dédié SANS fenêtre visible.

    Repli quand la fenêtre de connexion a été fermée avant la récolte : comme
    le profil dédié est persistant, la connexion y est conservée. À n'appeler
    qu'une fois la fenêtre visible fermée (un seul accès au profil à la fois).
    """
    bp = find_browser()
    if not bp:
        raise RuntimeError(_translate(
            "Aucun navigateur compatible trouvé.\n"
            "Installez Google Chrome, Microsoft Edge ou Brave."
        ))
    from DrissionPage import ChromiumOptions, ChromiumPage
    co = ChromiumOptions()
    co.set_browser_path(bp)
    co.set_user_data_path(downaccess_profile_dir())
    co.set_local_port(_free_port())
    co.headless()
    page = ChromiumPage(co)
    try:
        return harvest_cookies(page)
    finally:
        try:
            page.quit()
        except Exception:
            pass
