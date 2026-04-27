"""Contentful AudiobookNode handler."""

from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

import httpx

from ....models import AudiobookNode, AudiobookAuthor, AudiobookNarrator, AudiobookSeries
from .._helpers import _embedded_block, _field
from .base import ContentfulNodeHandler
from ....events import (
    WritingAsinEvent, AsinPublishFailedEvent, AsinPublishConflictEvent,
    AsinDraftCleanupEvent, EnrichingAsinsEvent,
)

if TYPE_CHECKING:
    from ..client import ContentfulClient

logger = logging.getLogger(__name__)


class AudiobookHandler(ContentfulNodeHandler):
    node_type = "audiobook"

    def to_contentful(self, node: AudiobookNode) -> dict:
        return _embedded_block(node.source_id or f"{node.asin}-{node.marketplace}")

    def from_contentful(self, raw: dict, **context) -> AudiobookNode:
        locale = context.get("locale", "en-US")
        return self.from_entry(raw, locale)

    def to_fields(self, node: AudiobookNode) -> dict[str, Any]:
        missing = [f for f, v in [("title", node.title), ("pdp", node.pdp), ("cover_url", node.cover_url)] if not v]
        if not node.authors or not all(a.name and a.pdp for a in node.authors):
            missing.append("authors[].name+pdp")
        if missing:
            raise ValueError(f"AudiobookNode missing render-critical fields: {missing}")

        def f(value: Any) -> dict:
            return {"en-US": value}

        unique_key = f"{node.asin}-{node.marketplace}"
        fields: dict[str, Any] = {
            "asin": f(node.asin),
            "marketplace": f(node.marketplace),
            "uniqueKey": f(unique_key),
            "label": f(node.label or unique_key),
            "title": f(node.title),
            "type": f("Product"),
            "deliveryType": f("SinglePartBook"),
            "cover": f(node.cover_url),
            "pdp": f(node.pdp),
            "authors": f([{"name": a.name, "pdp": a.pdp} for a in node.authors]),
        }
        if node.summary:
            summary = node.summary if node.summary.strip().startswith("<") else f"<p>{node.summary}</p>"
            fields["summary"] = f(summary)
        if node.release_date:
            fields["releaseDate"] = f(node.release_date)
        if node.narrators:
            fields["narrators"] = f([{"name": n.name} for n in node.narrators])
        if node.series:
            fields["series"] = f([{"title": s.title, "asin": s.asin, "url": s.url, "sequence": s.sequence} for s in node.series])
        return fields

    def from_entry(self, entry: dict, locale: str) -> AudiobookNode:
        sys = entry.get("sys", {})
        fields = entry.get("fields", {})
        raw_authors = _field(fields, "authors", locale) or []
        raw_narrators = _field(fields, "narrators", locale) or []
        raw_series = _field(fields, "series", locale) or []
        return AudiobookNode(
            source_id=sys.get("id"),
            asin=_field(fields, "asin", locale) or "",
            marketplace=_field(fields, "marketplace", locale) or "",
            title=_field(fields, "title", locale),
            cover_url=_field(fields, "cover", locale),
            summary=_field(fields, "summary", locale),
            label=_field(fields, "label", locale),
            pdp=_field(fields, "pdp", locale),
            release_date=_field(fields, "releaseDate", locale),
            authors=[AudiobookAuthor(**a) for a in raw_authors if isinstance(a, dict)],
            narrators=[AudiobookNarrator(**n) for n in raw_narrators if isinstance(n, dict)],
            series=[AudiobookSeries(**s) for s in raw_series if isinstance(s, dict)],
        )

    def resolve_asins(self, links: list | None, raw_entries: dict[str, dict], locale: str) -> list[str]:
        if not links:
            return []
        asins = []
        for link in links:
            eid = link.get("sys", {}).get("id") if isinstance(link, dict) else None
            if eid and eid in raw_entries:
                asin = _field(raw_entries[eid].get("fields", {}), "asin", locale)
                if asin:
                    asins.append(asin)
        return asins

    def resolve_children(self, links: list | None, raw_entries: dict[str, dict], locale: str) -> list[AudiobookNode]:
        if not links:
            return []
        children = []
        for link in links:
            eid = link.get("sys", {}).get("id") if isinstance(link, dict) else None
            if eid and eid in raw_entries:
                children.append(self.from_entry(raw_entries[eid], locale))
        return children

    # ------------------------------------------------------------------
    # I/O: write single ASIN entry with conflict resolution
    # ------------------------------------------------------------------

    async def write(self, node: AudiobookNode, client: "ContentfulClient") -> str:
        """Create or reuse an ASIN entry in Contentful. Returns entry ID."""
        unique_key = f"{node.asin}-{node.marketplace}"
        client._emit(WritingAsinEvent(asin=node.asin, marketplace=node.marketplace))
        items = await client.find_entries("asin", {"fields.uniqueKey": unique_key})

        if items:
            entry = items[0]
            entry_id = entry["sys"]["id"]
            if entry["sys"].get("publishedVersion"):
                return entry_id
            try:
                await client.publish_entry(entry_id, entry["sys"]["version"])
                return entry_id
            except Exception as e:
                if not hasattr(e, "response"):
                    logger.exception("Failed to publish asin entry %s", entry_id)
                    client._emit(AsinPublishFailedEvent(asin=node.asin, message=str(e)))
                    raise
                conflicts = (
                    e.response.json()
                    .get("details", {})
                    .get("errors", [{}])[0]
                    .get("conflicting", [])
                )
                if not conflicts:
                    logger.exception("Failed to publish asin entry %s", entry_id)
                    client._emit(AsinPublishFailedEvent(asin=node.asin, message=str(e)))
                    raise
                real_id = conflicts[0]["sys"]["id"]
                client._emit(AsinPublishConflictEvent(asin=node.asin, entry_id=entry_id))
                await client.delete_entry(entry_id, entry["sys"]["version"])
                return real_id

        fields = self.to_fields(node)

        # Clean up stale draft left by a previous failed run
        try:
            stale = await client.get_entry(unique_key)
            if not stale["sys"].get("publishedVersion"):
                logger.info("Deleting stale draft entry %s", unique_key)
                client._emit(AsinDraftCleanupEvent(asin=node.asin, entry_id=unique_key))
                await client.delete_entry(unique_key, stale["sys"]["version"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise

        raw = await client.create_entry_with_id(unique_key, "asin", fields)
        entry_id = raw["sys"]["id"]
        version = raw["sys"]["version"]
        try:
            await client.publish_entry(entry_id, version)
            return entry_id
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 422:
                raise
            logger.warning("Publish of %s blocked by index conflict, falling back to random ID", unique_key)
            await client.delete_entry(entry_id, version)
            raw = await client.create_entry("asin", fields)
            entry_id = raw["sys"]["id"]
            await client.publish_entry(entry_id, raw["sys"]["version"])
            return entry_id

    # ------------------------------------------------------------------
    # I/O: batch-resolve existing ASIN entries
    # ------------------------------------------------------------------

    async def resolve_batch(self, asin_nodes: list[AudiobookNode], client: "ContentfulClient") -> list[str]:
        """Batch-resolve ASIN entry IDs. Creates missing entries after enrichment."""
        from ....enrichers.audible import enrich_batch
        from ....models import AudiobookAuthor, AudiobookNarrator

        unique_keys = [f"{n.asin}-{n.marketplace}" for n in asin_nodes]
        items = await client.find_entries(
            "asin",
            {"fields.uniqueKey[in]": ",".join(unique_keys)},
            limit=len(unique_keys),
        )
        by_key = {
            item["fields"].get("uniqueKey", {}).get("en-US"): item
            for item in items
        }
        result: list[str | None] = [None] * len(asin_nodes)
        missing: list[tuple[int, AudiobookNode]] = []

        for i, (node, key) in enumerate(zip(asin_nodes, unique_keys)):
            item = by_key.get(key)
            if item:
                if item["sys"].get("publishedVersion"):
                    result[i] = item["sys"]["id"]
                else:
                    try:
                        await client.publish_entry(item["sys"]["id"], item["sys"]["version"])
                        result[i] = item["sys"]["id"]
                    except Exception:
                        client._emit(AsinDraftCleanupEvent(asin=key, entry_id=item["sys"]["id"]))
                        await client.delete_entry(item["sys"]["id"], item["sys"]["version"])
                        missing.append((i, node))
            else:
                missing.append((i, node))

        if missing:
            client._emit(EnrichingAsinsEvent(count=len(missing)))
            missing_items = [{"asin": n.asin, "marketplace": n.marketplace} for _, n in missing]
            results = await enrich_batch(missing_items, on_progress=client._on_progress)
            for (i, node), data in zip(missing, results):
                if not node.title:
                    node.title = data.get("title")
                if not node.pdp:
                    node.pdp = data.get("pdp")
                if not node.cover_url:
                    node.cover_url = data.get("cover_url")
                if not node.summary:
                    node.summary = data.get("summary")
                if not node.release_date:
                    node.release_date = data.get("release_date")
                if not node.authors and data.get("authors"):
                    node.authors = [AudiobookAuthor(name=a["name"], pdp=a.get("pdp")) for a in data["authors"]]
                if not node.narrators and data.get("narrators"):
                    node.narrators = [AudiobookNarrator(name=n["name"]) for n in data["narrators"]]
                result[i] = await self.write(node, client)

        return result
