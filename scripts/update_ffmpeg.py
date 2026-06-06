"""
update_ffmpeg.py — Télécharge ffmpeg depuis yt-dlp/FFmpeg-Builds et le place dans assets/.

Usage :
    python scripts/update_ffmpeg.py

Source : https://github.com/yt-dlp/FFmpeg-Builds
Build   : ffmpeg-master-latest-win64-gpl (statique, GPL, Windows x64)
"""
import io
import sys
import zipfile
from datetime import datetime, UTC
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

RELEASE_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
ASSETS_DIR   = Path(__file__).parent.parent / "assets"
VERSION_FILE = ASSETS_DIR / "ffmpeg_version.txt"

# Binaires à extraire : nom dans le zip → chemin de sortie
_BINARIES = {
    "ffmpeg.exe": ASSETS_DIR / "ffmpeg.exe",
}


def _progress(downloaded: int, total: int) -> None:
    if total > 0:
        pct = downloaded * 100 // total
        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  {downloaded // 1_048_576} / {total // 1_048_576} Mo",
              end="", flush=True)


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Téléchargement de ffmpeg (yt-dlp/FFmpeg-Builds)...")
    print(f"  URL : {RELEASE_URL}")

    try:
        req = Request(RELEASE_URL, headers={"User-Agent": "DownAccess-updater/1.0"})
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            buf   = io.BytesIO()
            downloaded = 0
            while chunk := resp.read(65536):
                buf.write(chunk)
                downloaded += len(chunk)
                _progress(downloaded, total)
        print()  # fin de la barre
    except URLError as e:
        print(f"\n❌ Erreur réseau : {e}")
        return 1

    print("Extraction...")
    buf.seek(0)
    try:
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            for binary_name, out_path in _BINARIES.items():
                candidates = [n for n in names
                              if n.endswith(f"/bin/{binary_name}") or n == f"bin/{binary_name}"]
                if not candidates:
                    print(f"  {binary_name} introuvable dans l'archive, ignore.")
                    continue
                src = candidates[0]
                data = zf.read(src)
                out_path.write_bytes(data)
                size_mb = len(data) / 1_048_576
                print(f"  {binary_name} -> {out_path}  ({size_mb:.1f} Mo)")
    except zipfile.BadZipFile as e:
        print(f"Archive corrompue : {e}")
        return 1

    # Fichier de version
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    VERSION_FILE.write_text(
        f"source=yt-dlp/FFmpeg-Builds\n"
        f"build=ffmpeg-master-latest-win64-gpl\n"
        f"updated={now}\n",
        encoding="utf-8",
    )
    print(f"  Version: {VERSION_FILE}")

    print("\nOK  ffmpeg mis a jour avec succes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
