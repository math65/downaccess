"""Historique des téléchargements — stockage JSON dans %APPDATA%\\DownAccess.

Conserve les téléchargements réussis et échoués pour permettre :
- de retrouver un fichier déjà téléchargé,
- d'ouvrir le dossier de destination,
- de copier l'URL d'origine,
- de re-télécharger avec le même format.

Limite : MAX_ENTRIES (les plus anciennes sont supprimées au-delà).
"""
import json
import os
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 500


@dataclass
class HistoryEntry:
    timestamp: str = ""        # ISO 8601
    url: str = ""
    title: str = ""
    site: str = ""
    format_spec: str = ""
    format_id: str | None = None
    filepath: str = ""
    file_size: int = 0
    status: str = "success"    # success | failed
    error: str = ""


def _history_file() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    path = Path(appdata) / "DownAccess"
    path.mkdir(parents=True, exist_ok=True)
    return path / "history.json"


def load() -> list[HistoryEntry]:
    try:
        with open(_history_file(), encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    valid_keys = {f.name for f in fields(HistoryEntry)}
    out: list[HistoryEntry] = []
    for item in raw.get("entries", []):
        if not isinstance(item, dict):
            continue
        clean = {k: v for k, v in item.items() if k in valid_keys}
        out.append(HistoryEntry(**clean))
    return out


def save(entries: list[HistoryEntry]) -> None:
    payload = {"version": 1, "entries": [asdict(e) for e in entries]}
    with open(_history_file(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def add(entry: HistoryEntry) -> None:
    if not entry.timestamp:
        entry.timestamp = datetime.now().isoformat(timespec="seconds")
    entries = load()
    entries.insert(0, entry)
    if len(entries) > MAX_ENTRIES:
        entries = entries[:MAX_ENTRIES]
    save(entries)


def clear() -> None:
    save([])
