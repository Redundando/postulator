"""Shared Contentful utilities — link builders, field accessors, asset/date parsing, entry ID extraction."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from ...models import AssetRef


# ---------------------------------------------------------------------------
# Link builders
# ---------------------------------------------------------------------------

def _link(entry_id: str) -> dict:
    return {"sys": {"type": "Link", "linkType": "Entry", "id": entry_id}}


def _asset_link(asset_id: str) -> dict:
    return {"sys": {"type": "Link", "linkType": "Asset", "id": asset_id}}


def _embedded_block(entry_id: str) -> dict:
    return {"nodeType": "embedded-entry-block", "data": {"target": _link(entry_id)}, "content": []}


# ---------------------------------------------------------------------------
# Field accessors
# ---------------------------------------------------------------------------

def _field(fields: dict, key: str, locale: str) -> Any:
    f = fields.get(key, {})
    return f.get(locale) or f.get("en-US")


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Asset parsing
# ---------------------------------------------------------------------------

def _parse_asset(asset: dict | None, locale: str) -> AssetRef | None:
    if not asset:
        return None
    sys = asset.get("sys", {})
    fields = asset.get("fields", {})
    file = _field(fields, "file", locale) or {}
    details = file.get("details", {})
    image = details.get("image", {})
    raw_url = file.get("url")
    url = (f"https:{raw_url}" if raw_url and raw_url.startswith("//") else raw_url) if raw_url else None
    return AssetRef(
        source_id=sys.get("id"),
        url=url,
        title=_field(fields, "title", locale),
        alt=_field(fields, "description", locale),
        file_name=file.get("fileName"),
        content_type=file.get("contentType"),
        width=image.get("width"),
        height=image.get("height"),
        size=details.get("size"),
    )


# ---------------------------------------------------------------------------
# Entry ID extraction
# ---------------------------------------------------------------------------

def _linked_entry_ids(obj: Any) -> list[str]:
    ids = []
    if isinstance(obj, dict):
        sys = obj.get("sys", {})
        if sys.get("type") == "Link" and sys.get("linkType") == "Entry":
            ids.append(sys["id"])
        for v in obj.values():
            ids.extend(_linked_entry_ids(v))
    elif isinstance(obj, list):
        for item in obj:
            ids.extend(_linked_entry_ids(item))
    return ids


def _entry_ids_from_links(links: list | None) -> list[str]:
    if not links:
        return []
    return [
        l["sys"]["id"] for l in links
        if isinstance(l, dict) and l.get("sys", {}).get("linkType") == "Entry"
    ]
