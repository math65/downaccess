"""
Module de synthèse vocale pour lecteurs d'écran (NVDA, JAWS).
Utilise accessible_output2 avec uniquement les outputs NVDA et JAWS.
SAPI n'est jamais initialisé — pas de voix Windows sans lecteur d'écran.
"""

_outputs: list = []

try:
    from accessible_output2.outputs.nvda import NVDA
    _outputs.append(NVDA())
except Exception:
    pass

try:
    from accessible_output2.outputs.jaws import Jaws
    _outputs.append(Jaws())
except Exception:
    pass


def speak(text: str, interrupt: bool = True) -> None:
    """
    Parle le texte via le lecteur d'écran actif (NVDA ou JAWS).
    Ne fait rien si aucun lecteur d'écran n'est actif.
    """
    for output in _outputs:
        try:
            if output.is_active():
                output.speak(text, interrupt=interrupt)
                return
        except Exception:
            pass


def active_screen_reader() -> str:
    """Retourne le nom du lecteur d'écran actif ('NVDA', 'Jaws') ou 'aucun'.
    Utile pour les rapports de diagnostic."""
    for output in _outputs:
        try:
            if output.is_active():
                return type(output).__name__
        except Exception:
            pass
    return "aucun"


def braille(text: str) -> None:
    """Envoie le texte sur la plage braille si disponible."""
    for output in _outputs:
        try:
            if output.is_active():
                output.braille(text)
                return
        except Exception:
            pass
