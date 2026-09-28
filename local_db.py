"""local_db.py — Minimal local JSON-file storage, used as a drop-in
replacement for the Google Sheets backend when no live Sheet/service
account is configured (GOOGLE_SHEET_ID empty).

Not for production concurrent use — single-process, read-modify-write,
no locking. Good enough for a local demo.
"""

import json
import pathlib

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _path(name: str) -> pathlib.Path:
    return DATA_DIR / f"{name}.json"


def load(name: str, default):
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save(name: str, data) -> None:
    _path(name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
