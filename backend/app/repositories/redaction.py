"""Persistence for attempt-detail redaction rules (stored in settings)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.engines.redaction import normalize_rules

SETTINGS_KEY = "redaction_rules"

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "fields": ["customer_id", "name", "phone", "email", "id_card", "bank_card"],
        "action": "mask",
        "enabled": True,
    }
]


def get_rules(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    row = conn.execute(
        "SELECT value FROM settings WHERE key=?", (SETTINGS_KEY,)
    ).fetchone()
    if not row or not row["value"]:
        return [dict(r) for r in DEFAULT_RULES]
    try:
        raw = json.loads(row["value"])
    except json.JSONDecodeError:
        return [dict(r) for r in DEFAULT_RULES]
    try:
        return normalize_rules(raw)
    except ValueError:
        # A broken stored value must not take down the write path.
        return [dict(r) for r in DEFAULT_RULES]


def put_rules(conn: sqlite3.Connection, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = normalize_rules(rules)
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SETTINGS_KEY, json.dumps(clean, ensure_ascii=False)),
    )
    return clean
