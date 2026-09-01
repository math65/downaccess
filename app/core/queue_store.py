"""File d'attente conservée d'une session à l'autre.

Jusqu'ici la file ne vivait qu'en mémoire : fermer DownAccess perdait tout ce
qui n'était pas terminé. Un utilisateur dont l'analyse d'une playlist restait
bloquée a fermé l'application pour s'en sortir, et a tout perdu d'un coup —
l'historique ne garde que ce qui a abouti (rapport de Brad, 2026-09-01).

On enregistre donc les téléchargements **non terminés** dans `queue.json`, à
côté de `history.json`, et on les remet en file au démarrage suivant.

## Ce qui n'est PAS conservé, et pourquoi

Les éléments issus de l'extraction guidée (`cookies`, `referer`, `skip_info`) :
leur adresse porte un jeton de session qui expire en quelques minutes. Les
restaurer ne produirait qu'un échec incompréhensible le lendemain. Mieux vaut
ne rien promettre que promettre à faux.

Les `Event` d'arrêt et de pause ne se sérialisent pas et n'auraient aucun sens
d'une session à l'autre : ils repartent neufs.
"""

import json
import logging
import os
from pathlib import Path

_log = logging.getLogger("downaccess.queue_store")

# Champs restaurables d'un QueueItem. Volontairement explicite : un champ
# ajoute a QueueItem ne doit pas se retrouver persiste par accident.
_CHAMPS = (
    "url", "format_spec", "format_id", "audio_groups",
    "playlist_title", "playlist_number", "use_cookies",
    "subtitles_override", "section",
)

# Garde-fou : une file monstrueuse (une chaine entiere enfilee par erreur) ne
# doit pas faire un fichier de plusieurs mega-octets ni ressusciter des
# milliers de telechargements au demarrage.
MAX_ITEMS = 500


def _store_file() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    dossier = Path(appdata) / "DownAccess"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier / "queue.json"


def is_restorable(item) -> bool:
    """L'élément a-t-il un sens une fois l'application relancée ?"""
    if not getattr(item, "url", ""):
        return False
    # Extraction guidee : adresse a jeton, perimee des la session suivante.
    if getattr(item, "cookies", None) or getattr(item, "referer", None):
        return False
    if getattr(item, "skip_info", False):
        return False
    return True


def to_dict(item) -> dict:
    """Réduit un QueueItem à ce qui se conserve."""
    donnees = {}
    for champ in _CHAMPS:
        valeur = getattr(item, champ, None)
        if isinstance(valeur, tuple):
            valeur = list(valeur)      # JSON ne connait pas les tuples
        donnees[champ] = valeur
    return donnees


def save(items: list) -> None:
    """Écrit les téléchargements non terminés. Ne lève jamais.

    Appelée à la fermeture : une erreur d'écriture ne doit pas empêcher
    l'application de se fermer.
    """
    restaurables = [to_dict(i) for i in items if is_restorable(i)][:MAX_ITEMS]
    try:
        if not restaurables:
            clear()
            return
        with open(_store_file(), "w", encoding="utf-8") as fh:
            json.dump(restaurables, fh, indent=2, ensure_ascii=False)
        _log.info("File conservee : %d telechargement(s)", len(restaurables))
    except OSError as exc:
        _log.warning("File non conservee : %s", exc)


def load() -> list[dict]:
    """Relit les téléchargements conservés. Liste vide si rien ou illisible."""
    try:
        with open(_store_file(), encoding="utf-8") as fh:
            donnees = json.load(fh)
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError) as exc:
        # Fichier tronque (coupure de courant pendant l'ecriture) : on repart
        # d'une file vide plutot que de refuser de demarrer.
        _log.warning("File conservee illisible, ignoree : %s", exc)
        return []

    if not isinstance(donnees, list):
        return []

    propres = []
    for entree in donnees[:MAX_ITEMS]:
        if not isinstance(entree, dict) or not entree.get("url"):
            continue
        # On ne garde que les champs connus : un fichier venu d'une version
        # plus recente ne doit pas faire exploser `QueueManager.add()`.
        filtre = {k: v for k, v in entree.items() if k in _CHAMPS}
        section = filtre.get("section")
        if isinstance(section, list) and len(section) == 2:
            filtre["section"] = tuple(section)
        else:
            filtre["section"] = None
        propres.append(filtre)
    return propres


def clear() -> None:
    """Oublie la file conservée. Ne lève jamais."""
    try:
        _store_file().unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        _log.warning("File conservee non effacee : %s", exc)
