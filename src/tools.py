"""
LabelWise — src/tools.py
Local helpers for profile management, alias lookup, and scan logging.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
ALIAS_FILE   = ROOT / "data" / "aliases.json"
PROFILE_FILE = ROOT / "data" / "profile.json"
HISTORY_FILE = ROOT / "data" / "history.json"


# ── Helper: safe JSON load ─────────────────────────────────────────────────────
def _load_json(path: Path, default: Any) -> Any:
    """Load JSON from *path*, returning *default* if missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    """Write *data* as pretty-printed JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Tool 1: save_profile ───────────────────────────────────────────────────────
def save_profile(allergies: list[str], conditions: list[str],
                 preferences: list[str] | None = None) -> dict:
    """
    Persist the user's dietary restrictions extracted from their voice note.
    Called by Gemma 4 when it detects restrictions in the audio.

    Args:
        allergies   : e.g. ["peanut", "shellfish"]
        conditions  : e.g. ["diabetes", "hypertension"]
        preferences : e.g. ["vegan", "halal"]

    Returns: the saved profile dict.
    """
    profile = {
        "allergies":    [a.lower().strip() for a in (allergies or [])],
        "conditions":   [c.lower().strip() for c in (conditions or [])],
        "preferences":  [p.lower().strip() for p in (preferences or [])],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    _save_json(PROFILE_FILE, profile)
    print(f"[tools] Profile saved: {profile}")
    return profile


# ── Tool 2: get_profile ────────────────────────────────────────────────────────
def get_profile() -> dict:
    """
    Load the user's saved dietary profile.

    Returns: profile dict with keys allergies, conditions, preferences.
    """
    profile = _load_json(PROFILE_FILE, {
        "allergies": [], "conditions": [], "preferences": [], "last_updated": None
    })
    print(f"[tools] Profile loaded: {profile}")
    return profile


# ── Tool 3: lookup_aliases ─────────────────────────────────────────────────────
def lookup_aliases(ingredient: str) -> dict:
    """
    Check whether *ingredient* is a hidden name for a major allergen or
    high-sugar substance.

    Args:
        ingredient: raw ingredient string from the label.

    Returns:
        {
          "ingredient": <original>,
          "matches": [{"category": ..., "canonical": ...}, ...]
        }
        matches is empty [] if no alias found.
    """
    aliases = _load_json(ALIAS_FILE, {})
    ingredient_lower = ingredient.lower().strip()
    matches = []

    for category, names in aliases.items():
        if category.startswith("_"):
            continue  # skip comment keys
        for alias in names:
            if alias.lower() in ingredient_lower or ingredient_lower in alias.lower():
                matches.append({"category": category, "canonical": alias})
                break  # one match per category is enough

    result = {"ingredient": ingredient, "matches": matches}
    if matches:
        print(f"[tools] Alias match: {ingredient!r} → {matches}")
    return result


# ── Tool 4: log_scan ──────────────────────────────────────────────────────────
def log_scan(product: str, verdict: str, flagged: list[dict],
             summary: str = "") -> dict:
    """
    Append a scan result to the local history log.

    Args:
        product  : product name or description (may be empty).
        verdict  : "SAFE" | "CAUTION" | "AVOID".
        flagged  : list of {"ingredient": ..., "reason": ...} dicts.
        summary  : one-line plain-English summary.

    Returns: the log entry dict.
    """
    history = _load_json(HISTORY_FILE, [])
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product":   product or "Unknown product",
        "verdict":   verdict.upper(),
        "flagged":   flagged or [],
        "summary":   summary,
    }
    history.insert(0, entry)        # newest first
    history = history[:100]          # keep last 100 scans only
    _save_json(HISTORY_FILE, history)
    print(f"[tools] Scan logged: {verdict} — {product}")
    return entry


# ── Tool dispatcher ────────────────────────────────────────────────────────────
# Maps tool name → Python function for any local caller that needs dispatch().
# returns a tool-call block.
TOOL_REGISTRY: dict[str, callable] = {
    "save_profile":   save_profile,
    "get_profile":    get_profile,
    "lookup_aliases": lookup_aliases,
    "log_scan":       log_scan,
}


def dispatch(name: str, arguments: dict) -> Any:
    """Execute a tool by name with the given arguments dict."""
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name!r}")
    return fn(**arguments)


# ── JSON schemas for the system prompt ────────────────────────────────────────
# Tool descriptions retained for integrations that support model tool calling.
TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "save_profile",
        "description": (
            "Save the user's dietary restrictions extracted from their voice note. "
            "Call this if the user mentions allergies or medical conditions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "allergies":   {"type": "array", "items": {"type": "string"},
                                "description": "List of allergens, e.g. ['peanut', 'shellfish']"},
                "conditions":  {"type": "array", "items": {"type": "string"},
                                "description": "Medical conditions, e.g. ['diabetes', 'lactose intolerance']"},
                "preferences": {"type": "array", "items": {"type": "string"},
                                "description": "Dietary preferences, e.g. ['vegan', 'halal']"},
            },
            "required": ["allergies", "conditions"],
        },
    },
    {
        "name": "get_profile",
        "description": "Load the user's previously saved dietary restrictions.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "lookup_aliases",
        "description": (
            "Check if an ingredient from the label is a hidden name for a common "
            "allergen or high-sugar substance. Call this for any unfamiliar ingredient."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ingredient": {"type": "string",
                               "description": "Raw ingredient name from the label"},
            },
            "required": ["ingredient"],
        },
    },
    {
        "name": "log_scan",
        "description": "Save the scan result to local history after giving the verdict.",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string",   "description": "Product name or description"},
                "verdict": {"type": "string",   "description": "SAFE, CAUTION, or AVOID"},
                "flagged": {"type": "array",    "description": "List of flagged ingredient dicts"},
                "summary": {"type": "string",   "description": "One-line plain-English summary"},
            },
            "required": ["verdict", "flagged"],
        },
    },
]
