"""Contentful AudiobookListNode handler."""

from __future__ import annotations
import logging
import time
from typing import Any, TYPE_CHECKING

from ....models import AudiobookListNode, AudiobookListItem, AudiobookNode
from .._helpers import _embedded_block, _field, _entry_ids_from_links, _link
from .base import ContentfulNodeHandler
from .audiobook import AudiobookHandler

if TYPE_CHECKING:
    from ..client import ContentfulClient

logger = logging.getLogger(__name__)
_audiobook = AudiobookHandler()


class AudiobookListHandler(ContentfulNodeHandler):
    node_type = "audiobook-list"

    def to_contentful(self, node: AudiobookListNode) -> dict:
        if not node.source_id:
            raise ValueError("AudiobookListNode.source_id is required for write")
        return _embedded_block(node.source_id)

    def from_contentful(self, raw: dict, **context) -> AudiobookListNode:
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        return self.from_entry(raw, raw_entries, raw_assets, locale)

    def to_fields(self, node: AudiobookListNode, asin_entry_ids: list[str]) -> dict[str, Any]:
        def f(value: Any) -> dict:
            return {"en-US": value}

        fields: dict[str, Any] = {
            "title": f(node.title or ""),
            "playerType": f(node.player_type),
            "asinsPerRow": f(node.asins_per_row),
            "descriptions": f(node.descriptions),
            "asins": f([_link(eid) for eid in asin_entry_ids]),
            "asinDescriptions": f(
                [_asin_description_item(item, eid) for item, eid in zip(node.asin_items, asin_entry_ids)]
                if node.asin_items else []
            ),
            "options": f(node.options or []),
        }
        return fields

    def from_entry(self, entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> AudiobookListNode:
        sys = entry.get("sys", {})
        fields = entry.get("fields", {})
        asin_links = _field(fields, "asins", locale)
        return AudiobookListNode(
            source_id=sys.get("id"),
            asins=_audiobook.resolve_asins(asin_links, raw_entries, locale),
            asin_entry_ids=_entry_ids_from_links(asin_links),
            asin_items=_parse_asin_descriptions(_field(fields, "asinDescriptions", locale)),
            children=_audiobook.resolve_children(asin_links, raw_entries, locale),
            title=_field(fields, "title", locale),
            label=_field(fields, "label", locale),
            body_copy=_field(fields, "copy", locale),
            player_type=_field(fields, "playerType", locale) or "Cover",
            asins_per_row=_field(fields, "asinsPerRow", locale) or 1,
            descriptions=_field(fields, "descriptions", locale) or "Full",
            filters=_field(fields, "filters", locale),
            options=_field(fields, "options", locale) or [],
        )

    async def write(self, node: AudiobookListNode, client: "ContentfulClient") -> str:
        """Resolve ASINs and create/update an asinsList entry. Returns entry ID."""
        if node.asins_per_row not in (1, 3, 4, 5):
            raise ValueError(f"AudiobookListNode.asins_per_row must be one of 1, 3, 4, 5 — got {node.asins_per_row}")
        t0 = time.monotonic()
        asin_nodes = [AudiobookNode(asin=item.asin, marketplace=item.marketplace) for item in node.asin_items] if not node.asins and node.asin_items else []
        preserved = node.asin_entry_ids
        if preserved and len(preserved) == len(asin_nodes or node.asins):
            asin_entry_ids = list(preserved)
            logger.debug("asinsList using preserved entry IDs x%d", len(asin_entry_ids))
        else:
            target_count = len(asin_nodes) if asin_nodes else len(node.asins)
            missing_indices = [i for i, eid in enumerate(preserved) if not eid] if preserved else list(range(target_count))
            if not asin_nodes:
                marketplace = node.asins[0].split("-")[-1] if node.asins else "US"
                asin_nodes = [AudiobookNode(asin=a, marketplace=marketplace) for a in node.asins]
            missing_nodes = [asin_nodes[i] for i in missing_indices if i < len(asin_nodes)]
            resolved = await _audiobook.resolve_batch(missing_nodes, client)
            logger.debug("write_asin x%d — %.2fs", len(missing_nodes), time.monotonic() - t0)
            asin_entry_ids = list(preserved) if preserved else [None] * target_count
            for i, eid in zip(missing_indices, resolved):
                asin_entry_ids[i] = eid

        fields = self.to_fields(node, asin_entry_ids)

        if node.source_id:
            existing = await client.get_entry(node.source_id)
            updated = await client.update_entry(node.source_id, existing["sys"]["version"], fields)
            entry_id = node.source_id
            version = updated["sys"]["version"]
        else:
            raw = await client.create_entry("asinsList", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]

        await client.publish_entry(entry_id, version)
        return entry_id


def _asin_description_item(item: AudiobookListItem, entry_id: str) -> dict:
    out: dict[str, Any] = {
        "key": item.key,
        "sys": {"type": "Link", "linkType": "Entry", "id": entry_id},
        "asin": item.asin,
        "marketplace": item.marketplace,
    }
    if item.title:
        out["title"] = item.title
    if item.cover_url:
        out["cover"] = item.cover_url
    if item.summary:
        out["summary"] = item.summary
    if item.editor_badge:
        out["editorBadge"] = item.editor_badge
    return out


def _parse_asin_descriptions(raw: list | None) -> list[AudiobookListItem]:
    if not raw:
        return []
    items = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        items.append(AudiobookListItem(
            key=item.get("key", ""),
            asin=item.get("asin", ""),
            marketplace=item.get("marketplace", ""),
            title=item.get("title"),
            cover_url=item.get("cover"),
            summary=item.get("summary"),
            editor_badge=item.get("editorBadge"),
        ))
    return items
