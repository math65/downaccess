"""
update_jsruntime.py — Telecharge QuickJS-ng (qjs.exe) et le place dans assets/.

Usage :
    python scripts/update_jsruntime.py

yt-dlp exige un moteur JavaScript externe pour resoudre le challenge de
signature YouTube. On embarque QuickJS-ng, minuscule (~2 Mo) et suffisant.
Source : https://github.com/quickjs-ng/quickjs (asset qjs-windows-x86_64.exe)
"""
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ASSETS_DIR   = Path(__file__).parent.parent / "assets"
QJS_EXE      = ASSETS_DIR / "qjs.exe"
VERSION_FILE = ASSETS_DIR / "qjs_version.txt"
LATEST_API   = "https://api.github.com/repos/quickjs-ng/quickjs/releases/latest"
ASSET_NAME   = "qjs-windows-x86_64.exe"


def _get(url: str) -> bytes:
    headers = {"User-Agent": "DownAccess-update-jsruntime"}
    # Sans jeton, l'API GitHub compte les appels par adresse IP : celles des
    # runners sont partagees et le quota y est souvent deja epuise (403).
    # Le jeton ne part que vers l'API, jamais vers l'adresse de telechargement.
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Recuperation de la derniere release QuickJS-ng...")
    try:
        rel = json.loads(_get(LATEST_API))
    except (URLError, ValueError) as exc:
        print(f"  ERREUR API GitHub : {exc}")
        return 1

    tag = rel.get("tag_name", "?")
    url = next((a["browser_download_url"] for a in rel.get("assets", [])
                if a.get("name") == ASSET_NAME), None)
    if not url:
        print(f"  ERREUR : asset {ASSET_NAME} introuvable dans {tag}")
        return 1

    print(f"  Telechargement {ASSET_NAME} ({tag})...")
    try:
        data = _get(url)
    except URLError as exc:
        print(f"  ERREUR telechargement : {exc}")
        return 1

    QJS_EXE.write_bytes(data)
    VERSION_FILE.write_text(
        "source=https://github.com/quickjs-ng/quickjs\n"
        f"version={tag}\n"
        f"updated={datetime.now(UTC).date().isoformat()}\n",
        encoding="utf-8",
    )
    print(f"  OK  qjs.exe ({len(data) // 1024} Ko) + qjs_version.txt -> {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
