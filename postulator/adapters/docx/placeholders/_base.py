"""Base placeholder class and shared helpers."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from ....marketplace import locale_to_country_code, _LOCALE_TO_COUNTRY_CODE


# ---------------------------------------------------------------------------
# Market <-> locale helpers
# ---------------------------------------------------------------------------

_COUNTRY_CODE_TO_LOCALE: dict[str, str] = {v: k for k, v in _LOCALE_TO_COUNTRY_CODE.items()}


def market_to_locale(market: str) -> str | None:
    market = market.strip().upper()
    if market in _COUNTRY_CODE_TO_LOCALE:
        return _COUNTRY_CODE_TO_LOCALE[market]
    for locale, cc in _LOCALE_TO_COUNTRY_CODE.items():
        if cc.upper() == market:
            return locale
    return None


def locale_to_market(locale: str) -> str:
    return locale_to_country_code(locale)


def resolve_locale(kv: dict[str, str]) -> str | None:
    market = kv.get("market", "")
    if market:
        resolved = market_to_locale(market)
        if resolved:
            return resolved
    return None


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

def escape(text: str) -> str:
    """Escape special characters for placeholder output."""
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace('"', '\\"')


def unescape(text: str) -> str:
    """Unescape backslash-escaped characters in placeholder content."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in "[]\\\"":
            out.append(text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Shared parsing helpers
# ---------------------------------------------------------------------------

def normalize_key(key: str) -> str:
    return re.sub(r"[\s_-]+", "_", key.strip().lower())


def resolve_aliases(kv: dict[str, str], alias_map: dict[str, str]) -> dict[str, str]:
    """Remap keys through an alias map. First-seen value wins per canonical key."""
    result: dict[str, str] = {}
    for key, value in kv.items():
        canonical = alias_map.get(normalize_key(key), normalize_key(key))
        if canonical not in result:
            result[canonical] = value
    return result


def parse_kv_segments(segments: list[str]) -> dict[str, str]:
    result = {}
    for seg in segments:
        seg = seg.strip()
        if "=" in seg:
            key, _, value = seg.partition("=")
            value = value.strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = unescape(value[1:-1])
            elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = unescape(value[1:-1])
            else:
                value = unescape(value)
            result[normalize_key(key)] = value
    return result


def split_content(content: str) -> list[str]:
    """Split placeholder content into segments by newlines and pipes.
    Blank lines are skipped."""
    segments = []
    for line in content.split("\n"):
        for part in line.split("|"):
            part = part.strip()
            if part:
                segments.append(part)
    return segments


def split_lines(content: str) -> list[str]:
    """Split placeholder content into non-blank lines."""
    return [line.strip() for line in content.split("\n") if line.strip()]


def split_asins(text: str) -> list[str]:
    return [a.strip() for a in re.split(r"[,\s]+", text.strip()) if a.strip()]


def parse_bool(value: str, default: bool = True) -> bool:
    return value.strip().lower() not in ("false", "0", "no", "off", "n")


def parse_date_flexible(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)


def parse_item_line(line: str) -> dict[str, str]:
    """Parse a list-item line: bare text before first comma is the primary value,
    comma-separated segments containing '=' are key-value pairs.

    Returns dict with '_value' for the primary value plus any kv pairs.
    E.g. 'Christian Lütjens, id=abc' -> {'_value': 'Christian Lütjens', 'id': 'abc'}
    """
    parts = [p.strip() for p in line.split(",")]
    value_parts: list[str] = []
    kv: dict[str, str] = {}
    for part in parts:
        if "=" in part and not value_parts:
            # kv before any bare text — treat as kv
            k, _, v = part.partition("=")
            kv[normalize_key(k)] = unescape(v.strip().strip('"').strip("'"))
        elif "=" in part:
            k, _, v = part.partition("=")
            kv[normalize_key(k)] = unescape(v.strip().strip('"').strip("'"))
        else:
            value_parts.append(part)
    # Rejoin bare parts with comma (handles quoted names with commas in future)
    result = kv
    result["_value"] = ", ".join(value_parts)
    return result


# ---------------------------------------------------------------------------
# Multi-line bracket block formatting helpers
# ---------------------------------------------------------------------------

def ml(type_name: str, lines: list[str]) -> str:
    body = "\n".join(lines)
    return f"[{type_name}\n{body}\n]"


def ml_flat(type_name: str, content: str) -> str:
    return f"[{type_name}: {content}]"


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BasePlaceholder:
    """Base class for placeholder format/parse handlers."""

    keywords: list[str] = []  # e.g. ["post"], ["author", "authors"]

    @classmethod
    def format(cls, obj: Any, **context) -> str:
        raise NotImplementedError

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        raise NotImplementedError
