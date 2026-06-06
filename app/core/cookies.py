"""
Cookies pour yt-dlp.

Deux mécanismes :

1. **Jar persistant par site** (recommandé, fonctionne sur Chrome récent) :
   les cookies sont récoltés depuis la session du navigateur dédié (DrissionPage
   via CDP, déjà déchiffrés) puis écrits dans un fichier cookie jar Netscape
   sous `%APPDATA%\\DownAccess\\cookies\\<domaine>.txt`. yt-dlp le lit via
   `cookiefile`. C'est la parade au chiffrement « App-Bound » de Chrome 127+
   qui casse `cookiesfrombrowser` (yt-dlp issue #10927).

2. **Repli `cookiesfrombrowser`** : lecture directe du profil par yt-dlp.
   Conservé pour Edge / Chrome ancien ; inopérant (mais inoffensif) sur Chrome
   127+ — l'échec re-déclenche simplement le parcours de connexion guidée.
"""
import logging
import os
import re
from urllib.parse import urlparse

from app.core.browser import browser_name, downaccess_profile_dir, find_browser

_log = logging.getLogger("downaccess.cookies")

# Mapping nom lisible -> identifiant yt-dlp
_YTDLP_BROWSER = {
    "Chrome": "chrome",
    "Edge": "edge",
    "Brave": "brave",
}

# Domaines qui partagent le même jar (liens courts -> site principal).
_DOMAIN_ALIASES = {
    "youtu.be": "youtube.com",
}


# ----------------------------------------------------------------------
# Stockage du jar persistant
# ----------------------------------------------------------------------

def cookies_dir() -> str:
    """Dossier des cookie jars persistants (`%APPDATA%\\DownAccess\\cookies`)."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(appdata, "DownAccess", "cookies")
    os.makedirs(path, exist_ok=True)
    return path


def _normalize_domain(url: str) -> str:
    """Domaine normalisé d'une URL (sans `www.`, en minuscules, alias résolus)."""
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return _DOMAIN_ALIASES.get(host, host)


def jar_path_for(url: str) -> str:
    """Chemin du cookie jar persistant pour le domaine de l'URL."""
    domain = _normalize_domain(url)
    safe = re.sub(r"[^a-z0-9.-]", "_", domain) or "site"
    return os.path.join(cookies_dir(), f"{safe}.txt")


# ----------------------------------------------------------------------
# Écriture d'un jar Netscape depuis des cookies CDP / DrissionPage
# ----------------------------------------------------------------------

def write_cookie_jar_from_dicts(cookies: list[dict], path: str) -> int:
    """Écrit un fichier cookie jar au format Netscape à partir des dicts de
    cookies renvoyés par DrissionPage/CDP (`name`, `value`, `domain`, `path`,
    `expires`, `httpOnly`, `secure`, `session`).

    Retourne le nombre de cookies écrits. Format strict attendu par le
    `MozillaCookieJar` de yt-dlp :
      domain<TAB>flag<TAB>path<TAB>secure<TAB>expiration<TAB>name<TAB>value
    Les cookies httpOnly utilisent le préfixe `#HttpOnly_` collé au domaine.
    """
    lines = ["# Netscape HTTP Cookie File", ""]
    written = 0
    for c in cookies:
        name = str(c.get("name", "") or "")
        value = str(c.get("value", "") or "")
        domain = str(c.get("domain", "") or "")
        if not name or not domain:
            continue
        # Robustesse : ignorer ce qui casserait le format tabulé.
        if any(ch in (name + value + domain) for ch in ("\t", "\n", "\r")):
            continue

        path_field = str(c.get("path", "/") or "/")
        # Drapeau « inclure les sous-domaines » = domaine à point initial.
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if c.get("secure") else "FALSE"

        # Expiration : session -> 0, sinon epoch entier.
        expires = c.get("expires", c.get("expiry"))
        is_session = c.get("session") or expires in (None, -1) or (
            isinstance(expires, (int, float)) and expires <= 0
        )
        expiration = "0" if is_session else str(round(float(expires)))

        # httpOnly -> préfixe spécial reconnu par yt-dlp.
        http_only = c.get("httpOnly", c.get("http_only", False))
        domain_field = ("#HttpOnly_" + domain) if http_only else domain

        lines.append("\t".join(
            [domain_field, include_sub, path_field, secure, expiration, name, value]
        ))
        written += 1

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")
    _log.debug("Cookie jar écrit (%d cookies) : %s", written, path)
    return written


# ----------------------------------------------------------------------
# Application aux options yt-dlp
# ----------------------------------------------------------------------

def apply_cookies(opts: dict, url: str | None = None) -> None:
    """Ajoute les cookies aux options yt-dlp.

    Priorité au jar persistant du site (récolté lors de la connexion guidée) ;
    à défaut, repli best-effort sur `cookiesfrombrowser`.
    """
    # 1. Jar persistant du site (parade au chiffrement App-Bound de Chrome).
    if url:
        jar = jar_path_for(url)
        if os.path.isfile(jar):
            opts["cookiefile"] = jar
            _log.debug("Cookies depuis le jar persistant : %s", jar)
            return

    # 2. Repli : lecture directe du profil par yt-dlp. Fonctionne sur Edge et
    #    Chrome ancien ; échoue (sans dommage) sur Chrome 127+ à cause du
    #    chiffrement App-Bound -> l'erreur relance la connexion guidée.
    path = find_browser()
    if not path:
        _log.warning("Aucun navigateur Chromium trouvé pour les cookies")
        return

    name = browser_name(path)
    browser_id = _YTDLP_BROWSER.get(name, "chrome")

    profile = os.path.join(downaccess_profile_dir(), "Default")
    if os.path.isdir(profile):
        opts["cookiesfrombrowser"] = (browser_id, profile)
        _log.debug("Repli : cookies depuis le profil dédié DownAccess (%s)", name)
    else:
        opts["cookiesfrombrowser"] = (browser_id,)
        _log.debug("Repli : cookies depuis le profil système %s", name)
