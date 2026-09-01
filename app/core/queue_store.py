"""File d'attente conservée d'une session à l'autre.

Jusqu'ici la file ne vivait qu'en mémoire : fermer DownAccess perdait tout ce
qui n'était pas terminé. Un utilisateur dont l'analyse d'une playlist restait
bloquée a fermé l'application pour s'en sortir, et a tout perdu d'un coup —
l'historique ne garde que ce qui a abouti (rapport de Brad, 2026-09-01).

On enregistre donc les téléchargements **non terminés** dans `queue.json`, à
côté de `history.json`, et on les remet en file au démarrage suivant.

## Écrit à chaque changement, pas seulement à la fermeture

La première version n'écrivait qu'en quittant proprement. Or c'est exactement
ce qui manque quand on en a besoin : Brad a fermé une fenêtre qui ne répondait
plus (Alt+F4), le gestionnaire de fermeture n'a jamais tourné, et la file
était vide au relancement — la conservation était inutile précisément dans le
cas qu'elle devait couvrir. `save()` est désormais appelée à chaque
modification de la file, et l'écriture est atomique (fichier temporaire puis
remplacement) : une coupure en pleine écriture laisse l'ancien fichier intact
au lieu d'un JSON tronqué.

## Ce qui n'est PAS conservé, et pourquoi

Les éléments issus de l'extraction guidée (`cookies`, `referer`, `skip_info`) :
leur adresse porte un jeton de session qui expire en quelques minutes. Les
restaurer ne produirait qu'un échec incompréhensible le lendemain. Mieux vaut
ne rien promettre que promettre à faux.

Les `Event` d'arrêt et de pause ne se sérialisent pas et n'auraient aucun sens
d'une session à l'autre : ils repartent neufs.

## Le garde-fou contre la boucle

Un téléchargement — ou la reprise elle-même — qui fait planter l'application
repartirait à chaque démarrage, indéfiniment. Chaque entrée compte donc ses
reprises (`restore_attempts`), incrémentées **sur le disque** dès la lecture :
au-delà de MAX_RESTORE_ATTEMPTS, l'entrée est abandonnée. Compter sur le
disque et non en mémoire est le point clé — un plantage survenant juste après
la reprise ne doit pas remettre le compteur à zéro.

Une fermeture propre remet tous les compteurs à zéro (`save(...,
reset_attempts=True)`) : elle prouve que rien n'a fait tomber l'application.
Sans cela, une file de plusieurs centaines de vidéos — trois soirées à fermer
et rouvrir DownAccess — se serait vidée toute seule des entrées qui
attendaient encore leur tour. Le compteur ne doit mesurer que les fins
brutales.
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
    "subtitles_override", "section", "restore_attempts",
)

# Garde-fou : une file monstrueuse (une chaine entiere enfilee par erreur) ne
# doit pas faire un fichier de plusieurs mega-octets ni ressusciter des
# milliers de telechargements au demarrage.
MAX_ITEMS = 500

# Nombre de reprises avant d'abandonner une entree. Trois laisse sa chance a
# une panne passagere (coupure reseau, machine eteinte) sans transformer un
# telechargement qui fait planter l'application en boucle sans fin.
MAX_RESTORE_ATTEMPTS = 3


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


def _ecrire(entrees: list[dict]) -> None:
    """Écrit le fichier de file, ou l'efface si rien à conserver. Ne lève jamais.

    Écriture atomique : le contenu part dans un fichier temporaire voisin, puis
    `os.replace()` le met en place d'un seul coup. La file étant réécrite à
    chaque modification, une coupure pendant l'écriture est un cas réel, pas
    théorique — sans cela elle laisserait un JSON tronqué, donc une file perdue.
    """
    if not entrees:
        clear()
        return
    cible = _store_file()
    temporaire = cible.with_suffix(".json.tmp")
    try:
        with open(temporaire, "w", encoding="utf-8") as fh:
            json.dump(entrees, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporaire, cible)
        _log.debug("File conservee : %d telechargement(s)", len(entrees))
    except OSError as exc:
        _log.warning("File non conservee : %s", exc)
        try:
            temporaire.unlink()
        except OSError:
            pass


def save(items: list, reset_attempts: bool = False) -> None:
    """Écrit les téléchargements non terminés. Ne lève jamais.

    Appelée à chaque modification de la file : une erreur d'écriture ne doit
    ni interrompre un téléchargement ni empêcher l'application de se fermer.

    `reset_attempts` : réservé à la fermeture propre, dernière écriture de la
    session. L'application s'est arrêtée normalement, donc aucune entrée n'est
    suspecte — leurs compteurs de reprise repartent de zéro.
    """
    entrees = [to_dict(i) for i in items if is_restorable(i)][:MAX_ITEMS]
    if reset_attempts:
        for entree in entrees:
            entree["restore_attempts"] = 0
    _ecrire(entrees)


def load() -> list[dict]:
    """Relit les téléchargements conservés. Liste vide si rien ou illisible.

    **Consomme une reprise** : le fichier est réécrit avec les compteurs
    incrémentés avant même que l'application n'ait relancé quoi que ce soit.
    C'est ce qui rend le garde-fou fiable — un plantage juste après la reprise
    ne doit pas rendre ses essais à l'entrée fautive.
    """
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
    abandonnees = 0
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
        essais = filtre.get("restore_attempts")
        essais = essais if isinstance(essais, int) and essais > 0 else 0
        if essais >= MAX_RESTORE_ATTEMPTS:
            # Trois reprises sans jamais aboutir : cette adresse fait tres
            # probablement planter l'application. On l'abandonne plutot que de
            # la relancer a chaque demarrage.
            abandonnees += 1
            _log.warning("Entree abandonnee apres %d reprises : %s",
                         essais, filtre.get("url"))
            continue
        filtre["restore_attempts"] = essais + 1
        propres.append(filtre)

    if abandonnees or propres:
        _ecrire(propres)
    return propres


def clear() -> None:
    """Oublie la file conservée. Ne lève jamais."""
    try:
        _store_file().unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        _log.warning("File conservee non effacee : %s", exc)
