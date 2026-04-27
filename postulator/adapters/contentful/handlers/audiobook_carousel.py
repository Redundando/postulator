"""Contentful AudiobookCarouselNode handler."""

from __future__ import annotations
import logging
import time
from typing import Any, TYPE_CHECKING

from ....models import AudiobookCarouselNode, AudiobookNode
from .._helpers import _embedded_block, _field, _entry_ids_from_links, _link
from .base import ContentfulNodeHandler
from .audiobook import AudiobookHandler

if TYPE_CHECKING:
    from ..client import ContentfulClient

logger = logging.getLogger(__name__)
_audiobook = AudiobookHandler()


class AudiobookCarouselHandler(ContentfulNodeHandler):
    node_type = "audiobook-carousel"

    def to_contentful(self, node: AudiobookCarouselNode) -> dict:
        if not node.source_id:
            raise ValueError("AudiobookCarouselNode.source_id is required for write")
        return _embedded_block(node.source_id)

    def from_contentful(self, raw: dict, **context) -> AudiobookCarouselNode:
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        return self.from_entry(raw, raw_entries, raw_assets, locale)

    def to_fields(self, node: AudiobookCarouselNode, asin_entry_ids: list[str]) -> dict[str, Any]:
        def f(value: Any) -> dict:
            return {"en-US": value}

        fields: dict[str, Any] = {
            "asins": f([_link(eid) for eid in asin_entry_ids]),
            "itemsPerSlide": f(node.items_per_slide or 3),
        }
        if node.title:
            fields["title"] = f(node.title)
        if node.subtitle:
            fields["subtitle"] = f(node.subtitle)
        if node.body_copy:
            fields["copy"] = f(node.body_copy)
        if node.cta_text:
            fields["ctaText"] = f(node.cta_text)
        if node.cta_url:
            fields["ctaUrl"] = f(node.cta_url)
        if node.options:
            fields["options"] = f(node.options)
        return fields

    def from_entry(self, entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> AudiobookCarouselNode:
        sys = entry.get("sys", {})
        fields = entry.get("fields", {})
        asin_links = _field(fields, "asins", locale)
        return AudiobookCarouselNode(
            source_id=sys.get("id"),
            asins=_audiobook.resolve_asins(asin_links, raw_entries, locale),
            asin_entry_ids=_entry_ids_from_links(asin_links),
            children=_audiobook.resolve_children(asin_links, raw_entries, locale),
            items_per_slide=_field(fields, "itemsPerSlide", locale),
            title=_field(fields, "title", locale),
            subtitle=_field(fields, "subtitle", locale),
            body_copy=_field(fields, "copy", locale),
            cta_text=_field(fields, "ctaText", locale),
            cta_url=_field(fields, "ctaUrl", locale),
            options=_field(fields, "options", locale) or [],
        )

    async def write(self, node: AudiobookCarouselNode, client: "ContentfulClient") -> str:
        """Resolve ASINs and create/update an asinsCarousel entry. Returns entry ID."""
        t0 = time.monotonic()
        if node.asin_entry_ids:
            asin_entry_ids = node.asin_entry_ids
            logger.debug("carousel using preserved entry IDs x%d", len(asin_entry_ids))
        else:
            marketplace = node.asins[0].split("-")[-1] if node.asins else "US"
            asin_nodes = [AudiobookNode(asin=a, marketplace=marketplace) for a in node.asins]
            asin_entry_ids = await _audiobook.resolve_batch(asin_nodes, client)
            logger.debug("write_asin x%d — %.2fs", len(asin_nodes), time.monotonic() - t0)

        fields = self.to_fields(node, asin_entry_ids)

        if node.source_id:
            existing = await client.get_entry(node.source_id)
            updated = await client.update_entry(node.source_id, existing["sys"]["version"], fields)
            entry_id = node.source_id
            version = updated["sys"]["version"]
        else:
            raw = await client.create_entry("asinsCarousel", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]

        await client.publish_entry(entry_id, version)
        return entry_id
