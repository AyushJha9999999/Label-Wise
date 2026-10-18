"""Small per-user JSON store for the local demo deployment."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
USERS_DIR = ROOT / "data" / "users"
_SAFE_UID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _user_dir(uid: str) -> Path:
    if not _SAFE_UID.fullmatch(uid):
        raise ValueError("Invalid user ID")
    path = USERS_DIR / uid
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def get_profile(uid: str) -> dict:
    return _read(_user_dir(uid) / "profile.json", {
        "allergies": [], "conditions": [], "preferences": [], "last_updated": None,
    })


def save_profile(uid: str, allergies: list[str], conditions: list[str],
                 preferences: list[str] | None = None) -> dict:
    profile = {
        "allergies": [x.strip().lower() for x in allergies if x.strip()],
        "conditions": [x.strip().lower() for x in conditions if x.strip()],
        "preferences": [x.strip().lower() for x in (preferences or []) if x.strip()],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    _write(_user_dir(uid) / "profile.json", profile)
    return profile


def get_history(uid: str, limit: int = 25) -> list[dict]:
    return _read(_user_dir(uid) / "history.json", [])[:limit]


def log_scan(uid: str, result: dict) -> None:
    path = _user_dir(uid) / "history.json"
    rows = _read(path, [])
    rows.insert(0, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": result["verdict"],
        "summary": result["summary"],
        "flagged": result.get("flagged", []),
    })
    _write(path, rows[:100])
