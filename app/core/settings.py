import copy
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
    "embed_metadata": True,        # titre/artiste/album + pochette + chapitres
                                   # dans les fichiers produits (MP3, M4A, MP4)
    "chapters_mode": "embed",      # que faire des chapitres d'une video :
                                   # embed  = un seul fichier, reperes dedans
                                   # split  = un fichier par chapitre
                                   # ignore = aucun repere
    "subscriptions_check_on_start": True,   # relever les abonnements au lancement
    "subscriptions_announce": False,        # annoncer vocalement les nouveautes
    "subscriptions_on_new": "counter",      # au lancement : counter | window
    "subscriptions_daily_only": False,      # ne pas relever plus d'une fois par jour
    "subscriptions_default_format": "",     # format des nouveaux abonnements ("" = preferences)
                                            # (silencieux par defaut, cf. regle UX)
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
    # Moteur de navigation de l'extraction guidée :
    #   "auto"     -> WebView2 (fourni par Windows) s'il est present, sinon
    #                 le navigateur installe ;
    #   "webview2" -> WebView2, avec repli silencieux s'il manque ;
    #   "browser"  -> toujours le navigateur installe (Chrome/Edge/Brave).
    # Les deux moteurs se pilotent par le meme protocole (CDP) : le reste de
    # l'extraction est rigoureusement identique. Voir app/core/webview_host.py.
    "uge_engine": "auto",
    "browser_choice": "auto",      # navigateur pour l'extraction guidée et la
                                   # connexion : auto | chrome | edge | brave
    "results_paging": "pages",     # parcours des résultats de recherche :
                                   # pages = boutons Page précédente/suivante
                                   # continuous = la suite se charge en bas de liste
    "suppressed_warnings": [],     # clés des avertissements masqués
    # Dialogues d'explication montres UNE SEULE fois. Ils doivent figurer ici :
    # `load()` ne conserve que les cles presentes dans DEFAULTS, donc une cle
    # absente est ecrite sur le disque puis jetee au demarrage suivant — et le
    # dialogue revenait a chaque lancement.
    "_uge_intro_shown": False,
    "_login_intro_shown": False,
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
    # Copie PROFONDE : plusieurs valeurs par defaut sont des listes, et le code
    # appelant y ajoute parfois un element en place (`cookie_sites.append(...)`,
    # `seen_announcements.append(...)`). Avec une copie de surface, ces ajouts
    # modifieraient DEFAULTS lui-meme et se retrouveraient dans une
    # configuration neuve chargee plus tard dans la meme session.
    cfg = copy.deepcopy(DEFAULTS)
    saved: dict = {}
    try:
        with open(_config_file(), encoding="utf-8") as f:
            saved = json.load(f)
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        # Fichier tronque ou illisible (coupure de courant, disque plein au
        # moment de l'ecriture) : on repart des valeurs par defaut plutot que
        # de refuser de demarrer. `history` et `subscriptions` font de meme.
        pass
    # Migration : l'ancien code de format par défaut « none » correspond
    # désormais à « auto » (vocabulaire unifié avec le dialogue d'ajout).
    if cfg.get("post_processing") == "none":
        cfg["post_processing"] = "auto"
    # Migration : la case « un fichier par chapitre » est devenue un choix a
    # trois entrees. Qui l'avait cochee garde son comportement ; les autres
    # basculent sur le defaut (« embed »), qui est ce qui se passait deja.
    if "chapters_mode" not in saved and saved.get("split_chapters"):
        cfg["chapters_mode"] = "split"
    return cfg


def save(settings: dict) -> None:
    with open(_config_file(), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
