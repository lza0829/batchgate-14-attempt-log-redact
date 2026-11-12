"""Attempt-detail redaction: match JSON fields by name, mask or drop them.

Rules are matched against a field's name (the JSON key) at any nesting depth,
and against dotted paths (e.g. ``sample.customer_id``). A rule may carry
several field names, comma-separated. Actions:

- ``mask``: replace the value with a fixed placeholder (default ``***``).
- ``drop``: remove the field entirely from the payload.
"""

from __future__ import annotations

import copy
from typing import Any

MASK_PLACEHOLDER = "***"
VALID_ACTIONS = ("mask", "drop")


def normalize_rules(raw: Any) -> list[dict[str, Any]]:
    """Validate and normalize a rules payload into a clean list.

    Raises ValueError on malformed input so callers can surface a 400.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("rules must be a list")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"rule #{i} must be an object")
        names_raw = item.get("fields")
        if isinstance(names_raw, str):
            names = [n.strip() for n in names_raw.split(",")]
        elif isinstance(names_raw, list):
            names = [str(n).strip() for n in names_raw]
        else:
            names = []
        names = [n for n in names if n]
        if not names:
            raise ValueError(f"rule #{i} needs at least one field name")
        action = str(item.get("action", "mask")).strip().lower()
        if action not in VALID_ACTIONS:
            raise ValueError(f"rule #{i} action must be one of {VALID_ACTIONS}")
        out.append(
            {
                "fields": names,
                "action": action,
                "enabled": bool(item.get("enabled", True)),
            }
        )
    return out


def _matching_action(rules: list[dict[str, Any]], key: str, path: str) -> str | None:
    action: str | None = None
    for rule in rules:
        if not rule["enabled"]:
            continue
        for name in rule["fields"]:
            if name == key or name == path:
                # Last matching rule wins.
                action = rule["action"]
    return action


def redact_value(value: Any, rules: list[dict[str, Any]], _path: str = "") -> Any:
    """Return a redacted deep copy of ``value`` according to ``rules``."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            path = f"{_path}.{key}" if _path else key
            action = _matching_action(rules, key, path)
            if action == "drop":
                continue
            if action == "mask":
                out[key] = MASK_PLACEHOLDER
                continue
            out[key] = redact_value(v, rules, path)
        return out
    if isinstance(value, list):
        return [redact_value(item, rules, _path) for item in value]
    return copy.deepcopy(value)
