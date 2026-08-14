import json
import os
from pathlib import Path

DEFAULTS: dict = {
    "download_folder": str(Path.home() / "Downloads"),
    "max_concurrent_downloads": 2,
    "concurrent_fragments": 1,      # 1=désactivé, >1=fragments en parallèle (-N)
    "post_processing": "auto",      # format par défaut (codes de add_url_dialog) :
                                    # auto | mp4 | mp3 | m4a | amc_video | amc_audio
    "open_folder_when_done": False,
    "amc_path": "",                  # emplacement de l'exe AMC (vide = détection auto)
    "ffmpeg_path": "ffmpeg",
    "proxy_http": "",
    "proxy_socks": "",
    "user_agent": "",
    "ratelimit_bytes": 0,           # 0 = illimité, sinon octets/seconde
    "auto_subtitles": False,
    "subtitle_langs": ["fr", "en"],
    "subtitle_format": "srt",       # srt | vtt | original
    "subtitle_mode": "separate",    # separate | embed | burn
    "audio_description_mode": "ask",    # sur france.tv/arte, que faire des pistes :
                                        # ask | ad_only | original_and_ad | original_only
    "organize_by_site": False,
    "organize_by_playlist": False,
    "playlist_numbering": 0,       # 0=original, 1=séquentiel, 2=aucun
    "playlist_full_harvest_auto": False,  # récupérer auto les playlists plafonnées
                                          # via le navigateur (sans redemander)
    "download_announcements": "always",  # always | foreground | never
                                          # annonces vocales début/fin de téléchargement
    "clipboard_monitor": False,
    "ytdlp_extra_opts": [],
    "user_email": "",
    "cookie_sites": [],
    "intercept_use_page_title": True,
    "browser_choice": "auto",      # navigateur pour l'extraction guidée et la
                                   # connexion : auto | chrome | edge | brave
    "suppressed_warnings": [],     # clés des avertissements masqués
    "language": "auto",            # auto | fr | en
    "install_id": "",              # identifiant anonyme d'installation (généré au 1er lancement)
    "seen_announcements": [],      # ids des annonces "once" déjà affichées
}


def _config_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    path = Path(appdata) / "DownAccess"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_file() -> Path:
    return _config_dir() / "settings.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(_config_file(), encoding="utf-8") as f:
            saved = json.load(f)
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    # Migration : l'ancien code de format par défaut « none » correspond
    # désormais à « auto » (vocabulaire unifié avec le dialogue d'ajout).
    if cfg.get("post_processing") == "none":
        cfg["post_processing"] = "auto"
    return cfg


def save(settings: dict) -> None:
    with open(_config_file(), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
