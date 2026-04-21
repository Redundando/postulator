"""Contentful write logic — mixed into ContentfulClient via _WriterMixin."""

from __future__ import annotations
import asyncio
import logging
import mimetypes
import os
import time
from typing import Any, TYPE_CHECKING

import httpx

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .client import ContentfulClient

from ...models import Post, Author, SeoMeta
from ...marketplace import locale_to_country_code
from ..scraperator import enrich_audiobook_nodes
from ...nodes import (
    BlockNode, InlineNode,
    TextNode, HyperlinkNode,
    ParagraphNode, HeadingNode, ListNode, BlockquoteNode, HrNode,
    AudiobookNode, AudiobookListNode, AudiobookCarouselNode,
    AudiobookListItem,
    ContentImageNode, EmbeddedAssetNode, TableCellNode, TableRowNode, TableNode, UnknownNode,
    AssetRef, LocalAsset,
)


def _link(entry_id: str) -> dict:
    return {"sys": {"type": "Link", "linkType": "Entry", "id": entry_id}}


def _asset_link(asset_id: str) -> dict:
    return {"sys": {"type": "Link", "linkType": "Asset", "id": asset_id}}


def _embedded_block(entry_id: str) -> dict:
    return {"nodeType": "embedded-entry-block", "data": {"target": _link(entry_id)}, "content": []}


def _audiobook_node_to_fields(node: AudiobookNode) -> dict[str, Any]:
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


def _inline_to_cf(node: InlineNode) -> dict:
    if isinstance(node, HyperlinkNode):
        return {
            "nodeType": "hyperlink",
            "data": {"uri": node.url},
            "content": [_inline_to_cf(c) for c in node.children],
        }
    return {
        "nodeType": "text",
        "value": node.value,
        "marks": [{"type": m} for m in node.marks],
        "data": {},
    }


def _paragraph_to_cf(node: ParagraphNode) -> dict:
    return {"nodeType": "paragraph", "data": {}, "content": [_inline_to_cf(c) for c in node.children]}


def _embed_to_cf(node: AudiobookNode | AudiobookListNode | AudiobookCarouselNode | ContentImageNode) -> dict:
    if isinstance(node, AudiobookNode):
        return _embedded_block(node.source_id or f"{node.asin}-{node.marketplace}")
    if isinstance(node, AudiobookListNode):
        if not node.source_id:
            raise ValueError("AudiobookListNode.source_id is required for write")
        return _embedded_block(node.source_id)
    if isinstance(node, AudiobookCarouselNode):
        if not node.source_id:
            raise ValueError("AudiobookCarouselNode.source_id is required for write")
        return _embedded_block(node.source_id)
    if not node.source_id:
        raise ValueError("ContentImageNode.source_id is required for write")
    return _embedded_block(node.source_id)


def _block_to_cf(node: BlockNode) -> dict:
    if isinstance(node, ParagraphNode):
        return _paragraph_to_cf(node)

    if isinstance(node, HeadingNode):
        return {"nodeType": f"heading-{node.level}", "data": {}, "content": [_inline_to_cf(c) for c in node.children]}

    if isinstance(node, ListNode):
        nt = "ordered-list" if node.ordered else "unordered-list"
        return {
            "nodeType": nt,
            "data": {},
            "content": [
                {"nodeType": "list-item", "data": {}, "content": [_block_to_cf(child) for child in item.children]}
                for item in node.children
            ],
        }

    if isinstance(node, BlockquoteNode):
        return {"nodeType": "blockquote", "data": {}, "content": [_paragraph_to_cf(p) for p in node.children]}

    if isinstance(node, HrNode):
        return {"nodeType": "hr", "data": {}, "content": []}

    if isinstance(node, TableNode):
        return {
            "nodeType": "table",
            "data": {},
            "content": [
                {
                    "nodeType": "table-row",
                    "data": {},
                    "content": [
                        {
                            "nodeType": "table-header-cell" if cell.is_header else "table-cell",
                            "data": {},
                            "content": [_block_to_cf(child) for child in cell.children],
                        }
                        for cell in row.children
                    ],
                }
                for row in node.children
            ],
        }

    if isinstance(node, (AudiobookNode, AudiobookListNode, AudiobookCarouselNode, ContentImageNode)):
        return _embed_to_cf(node)

    if isinstance(node, EmbeddedAssetNode):
        if not isinstance(node.image, AssetRef) or not node.image.source_id:
            raise ValueError("EmbeddedAssetNode.image must be an AssetRef with source_id for write")
        return {"nodeType": "embedded-asset-block", "data": {"target": _asset_link(node.image.source_id)}, "content": []}

    if isinstance(node, UnknownNode):
        return node.raw

    raise ValueError(f"Unhandled node type: {type(node)}")


def _body_to_richtext(body: list[BlockNode]) -> dict:
    return {"nodeType": "document", "data": {}, "content": [_block_to_cf(n) for n in body]}


def _seo_to_fields(seo: SeoMeta, fallback_label: str) -> dict[str, Any]:
    def f(value: Any) -> dict:
        return {"en-US": value}

    fields: dict[str, Any] = {
        "label": f(seo.label or fallback_label),
    }
    if seo.slug_replacement:
        fields["slugReplacement"] = f(seo.slug_replacement)
    if seo.slug_redirect:
        fields["slugRedirect"] = f(seo.slug_redirect)
    if seo.no_index is not None:
        fields["noIndex"] = f(seo.no_index)
    if seo.meta_title:
        fields["metaTitle"] = f(seo.meta_title)
    if seo.meta_description:
        fields["metaDescription"] = f(seo.meta_description)
    if seo.og_title:
        fields["openGraphTitle"] = f(seo.og_title)
    if seo.og_description:
        fields["openGraphDescription"] = f(seo.og_description)
    if isinstance(seo.og_image, AssetRef) and seo.og_image.source_id:
        fields["openGraphImage"] = f(_asset_link(seo.og_image.source_id))
    if seo.schema_type:
        fields["schemaType"] = f(seo.schema_type)
    if seo.json_ld_id:
        fields["jsonLd"] = f(_link(seo.json_ld_id))
    if seo.similar_content_ids:
        fields["similarContent"] = f([_link(eid) for eid in seo.similar_content_ids])
    if seo.external_links_source_code:
        fields["externalLinksSourceCode"] = f(seo.external_links_source_code)
    return fields


def _author_to_fields(author: Author) -> dict[str, Any]:
    def f(value: Any) -> dict:
        return {"en-US": value}

    fields: dict[str, Any] = {
        "slug": f(author.slug),
        "name": f(author.name),
    }
    if author.country_code:
        fields["countryCode"] = f(author.country_code)
    if author.short_name:
        fields["shortName"] = f(author.short_name)
    if author.title:
        fields["title"] = f(author.title)
    if author.bio:
        fields["bio"] = f(author.bio)
    if isinstance(author.picture, AssetRef) and author.picture.source_id:
        fields["picture"] = f(_asset_link(author.picture.source_id))
    if author.seo and author.seo.source_id:
        fields["seoSettings"] = f(_link(author.seo.source_id))
    return fields


def _post_to_fields(post: Post) -> dict[str, Any]:
    locale = "en-US"
    country_code = locale_to_country_code(post.locale)

    def f(value: Any) -> dict:
        return {locale: value}

    fields: dict[str, Any] = {
        "slug": f(post.slug),
        "title": f(post.title),
        "countryCode": f(country_code),
        "date": f(post.date.strftime("%Y-%m-%d")),
        "content": f(_body_to_richtext(post.body)),
    }
    if post.introduction:
        fields["introduction"] = f(post.introduction)
    if post.update_date:
        fields["updateDate"] = f(post.update_date.strftime("%Y-%m-%d"))
    if post.authors:
        fields["authors"] = f([_link(a.source_id) for a in post.authors if a.source_id])
    if post.tags:
        fields["tags"] = f([_link(t.source_id) for t in post.tags if t.source_id])
    if isinstance(post.featured_image, AssetRef) and post.featured_image.source_id:
        fields["image"] = f(_asset_link(post.featured_image.source_id))
    if post.seo and post.seo.source_id:
        fields["seoSettings"] = f(_link(post.seo.source_id))
    if post.custom_recommended_title:
        fields["customRecommendedTitle"] = f(post.custom_recommended_title)
    if not post.show_in_feed:
        fields["hideFromBlogFeed"] = f(True)
    if not post.show_publish_date:
        fields["hidePublishDate"] = f(True)
    if not post.show_hero_image:
        fields["hideHeroImage"] = f(True)
    if post.related_posts:
        fields["relatedPosts"] = f([_link(eid) for eid in post.related_posts])
    return fields


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


class _WriterMixin:
    async def upload_local_asset(self: "ContentfulClient", asset: LocalAsset) -> AssetRef:
        locale = "en-US"
        file_name = asset.file_name or os.path.basename(asset.local_path)
        content_type = asset.content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        self._emit("uploading_asset", title=asset.title, file_name=file_name)
        if not os.path.exists(asset.local_path):
            msg = f"Local asset file not found: {asset.local_path!r}"
            logger.error(msg)
            self._emit("asset_upload_failed", title=asset.title, message=msg)
            raise FileNotFoundError(msg)
        try:
            with open(asset.local_path, "rb") as fh:
                data = fh.read()

            upload_id = await self.upload_file(data, content_type)
            raw = await self.create_asset({
                "title": {locale: asset.title},
                "description": {locale: asset.alt or ""},
                "file": {locale: {
                    "fileName": file_name,
                    "contentType": content_type,
                    "uploadFrom": {"sys": {"type": "Link", "linkType": "Upload", "id": upload_id}},
                }},
            })
            asset_id = raw["sys"]["id"]
            await self.process_asset(asset_id, locale)

            for attempt in range(self._asset_poll_attempts):
                await asyncio.sleep(self._asset_poll_interval)
                raw = await self.get_asset(asset_id)
                if raw.get("fields", {}).get("file", {}).get(locale, {}).get("url"):
                    break
            else:
                logger.warning(
                    "Asset %s processing did not complete after %d attempts (%.1fs each)",
                    asset_id, self._asset_poll_attempts, self._asset_poll_interval,
                )
                self._emit("asset_processing_timeout", asset_id=asset_id)

            await self.publish_asset(asset_id, raw["sys"]["version"])
            raw = await self.get_asset(asset_id)

            file = raw.get("fields", {}).get("file", {}).get(locale, {})
            details = file.get("details", {})
            image = details.get("image", {})
            raw_url = file.get("url", "")
            return AssetRef(
                source_id=asset_id,
                url=f"https:{raw_url}" if raw_url.startswith("//") else raw_url,
                title=asset.title,
                alt=asset.alt,
                file_name=file_name,
                content_type=content_type,
                width=image.get("width"),
                height=image.get("height"),
                size=details.get("size"),
            )
        except Exception as e:
            logger.exception("Failed to upload asset %r", asset.title)
            self._emit("asset_upload_failed", title=asset.title, message=str(e))
            raise

    async def write_asin(self: "ContentfulClient", node: AudiobookNode) -> str:
        unique_key = f"{node.asin}-{node.marketplace}"
        self._emit("writing_asin", asin=node.asin, marketplace=node.marketplace)
        items = await self.find_entries("asin", {"fields.uniqueKey": unique_key})

        if items:
            entry = items[0]
            entry_id = entry["sys"]["id"]
            if entry["sys"].get("publishedVersion"):
                return entry_id
            try:
                await self.publish_entry(entry_id, entry["sys"]["version"])
                return entry_id
            except Exception as e:
                if not hasattr(e, "response"):
                    logger.exception("Failed to publish asin entry %s", entry_id)
                    self._emit("asin_publish_failed", asin=node.asin, message=str(e))
                    raise
                conflicts = (
                    e.response.json()
                    .get("details", {})
                    .get("errors", [{}])[0]
                    .get("conflicting", [])
                )
                if not conflicts:
                    logger.exception("Failed to publish asin entry %s", entry_id)
                    self._emit("asin_publish_failed", asin=node.asin, message=str(e))
                    raise
                real_id = conflicts[0]["sys"]["id"]
                self._emit("asin_publish_conflict", asin=node.asin, entry_id=entry_id)
                await self.delete_entry(entry_id, entry["sys"]["version"])
                return real_id

        fields = _audiobook_node_to_fields(node)

        # Clean up stale draft left by a previous failed run
        try:
            stale = await self.get_entry(unique_key)
            if not stale["sys"].get("publishedVersion"):
                logger.info("Deleting stale draft entry %s", unique_key)
                self._emit("asin_draft_cleanup", asin=node.asin, entry_id=unique_key)
                await self.delete_entry(unique_key, stale["sys"]["version"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise

        raw = await self.create_entry_with_id(unique_key, "asin", fields)
        entry_id = raw["sys"]["id"]
        version = raw["sys"]["version"]
        try:
            await self.publish_entry(entry_id, version)
            return entry_id
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 422:
                raise
            # Publish blocked by corrupted uniqueness index — delete the
            # deterministic-ID entry and fall back to a random-ID entry.
            logger.warning("Publish of %s blocked by index conflict, falling back to random ID", unique_key)
            await self.delete_entry(entry_id, version)
            raw = await self.create_entry("asin", fields)
            entry_id = raw["sys"]["id"]
            await self.publish_entry(entry_id, raw["sys"]["version"])
            return entry_id

    async def _resolve_asin_entry_ids(self: "ContentfulClient", asin_nodes: list[AudiobookNode]) -> list[str]:
        unique_keys = [f"{n.asin}-{n.marketplace}" for n in asin_nodes]
        items = await self.find_entries(
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
                        await self.publish_entry(item["sys"]["id"], item["sys"]["version"])
                        result[i] = item["sys"]["id"]
                    except Exception:
                        self._emit("asin_draft_cleanup", asin=key, entry_id=item["sys"]["id"])
                        await self.delete_entry(item["sys"]["id"], item["sys"]["version"])
                        missing.append((i, node))
            else:
                missing.append((i, node))

        if missing:
            self._emit("enriching_asins", count=len(missing))
            await enrich_audiobook_nodes([n for _, n in missing], on_progress=self._on_progress)
            for i, node in missing:
                result[i] = await self.write_asin(node)

        return result  # type: ignore[return-value]

    async def write_asin_list(self: "ContentfulClient", node: AudiobookListNode, asin_nodes: list[AudiobookNode]) -> str:
        if node.asins_per_row not in (1, 3, 4, 5):
            raise ValueError(f"AudiobookListNode.asins_per_row must be one of 1, 3, 4, 5 — got {node.asins_per_row}")
        t0 = time.monotonic()
        # derive asin_nodes from asin_items if not explicitly provided
        if not asin_nodes and node.asin_items:
            asin_nodes = [AudiobookNode(asin=item.asin, marketplace=item.marketplace) for item in node.asin_items]
        preserved = node.asin_entry_ids
        if preserved and len(preserved) == len(asin_nodes):
            asin_entry_ids = list(preserved)
            logger.debug("asinsList using preserved entry IDs x%d", len(asin_entry_ids))
        else:
            missing_indices = [i for i, eid in enumerate(preserved) if not eid] if preserved else list(range(len(asin_nodes)))
            missing_nodes = [asin_nodes[i] for i in missing_indices]
            resolved = await self._resolve_asin_entry_ids(missing_nodes)
            logger.debug("write_asin x%d — %.2fs", len(missing_nodes), time.monotonic() - t0)
            asin_entry_ids = list(preserved) if preserved else [None] * len(asin_nodes)
            for i, eid in zip(missing_indices, resolved):
                asin_entry_ids[i] = eid

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

        if node.source_id:
            existing = await self.get_entry(node.source_id)
            updated = await self.update_entry(node.source_id, existing["sys"]["version"], fields)
            entry_id = node.source_id
            version = updated["sys"]["version"]
        else:
            raw = await self.create_entry("asinsList", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]

        await self.publish_entry(entry_id, version)
        return entry_id

    async def write_asin_carousel(self: "ContentfulClient", node: AudiobookCarouselNode, asin_nodes: list[AudiobookNode]) -> str:
        t0 = time.monotonic()
        if node.asin_entry_ids:
            asin_entry_ids = node.asin_entry_ids
            logger.debug("carousel using preserved entry IDs x%d", len(asin_entry_ids))
        else:
            asin_entry_ids = await self._resolve_asin_entry_ids(asin_nodes)
            logger.debug("write_asin x%d — %.2fs", len(asin_nodes), time.monotonic() - t0)

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

        if node.source_id:
            existing = await self.get_entry(node.source_id)
            updated = await self.update_entry(node.source_id, existing["sys"]["version"], fields)
            entry_id = node.source_id
            version = updated["sys"]["version"]
        else:
            raw = await self.create_entry("asinsCarousel", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]

        await self.publish_entry(entry_id, version)
        return entry_id

    async def write_seo(self: "ContentfulClient", seo: SeoMeta, fallback_label: str) -> str:
        fields = _seo_to_fields(seo, fallback_label)
        if seo.source_id:
            existing = await self.get_entry(seo.source_id)
            updated = await self.update_entry(seo.source_id, existing["sys"]["version"], fields)
            entry_id = seo.source_id
            version = updated["sys"]["version"]
        else:
            raw = await self.create_entry("seoSettings", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]
        await self.publish_entry(entry_id, version)
        seo.source_id = entry_id
        return entry_id

    async def _prepare_post(self: "ContentfulClient", post: Post) -> None:
        if not post.body:
            msg = f"Post {post.slug!r} has an empty body — aborting"
            logger.error(msg)
            self._emit("post_invalid", slug=post.slug, reason=msg)
            raise ValueError(msg)

        marketplace = post.locale.split("-")[-1].upper()
        try:
            locale_to_country_code(post.locale)
        except ValueError:
            msg = f"Post {post.slug!r} has unknown locale {post.locale!r} — aborting"
            logger.error(msg)
            self._emit("post_invalid", slug=post.slug, reason=msg)
            raise ValueError(msg)
        t0 = time.monotonic()

        if isinstance(post.featured_image, LocalAsset):
            post.featured_image = await self.upload_local_asset(post.featured_image)
        if post.seo and isinstance(post.seo.og_image, LocalAsset):
            post.seo.og_image = await self.upload_local_asset(post.seo.og_image)
        for node in post.body:
            if isinstance(node, ContentImageNode) and isinstance(node.image, LocalAsset):
                node.image = await self.upload_local_asset(node.image)
            elif isinstance(node, EmbeddedAssetNode) and isinstance(node.image, LocalAsset):
                node.image = await self.upload_local_asset(node.image)

        if post.seo:
            await self.write_seo(post.seo, f"SEO Settings: {post.title}")

        # --- Phase 1: collect all unique ASINs across the entire post ---
        # keyed by "ASIN-MARKETPLACE" → representative AudiobookNode
        all_asins: dict[str, AudiobookNode] = {}
        for node in post.body:
            if isinstance(node, AudiobookNode):
                key = f"{node.asin}-{node.marketplace}"
                all_asins.setdefault(key, node)
            elif isinstance(node, AudiobookListNode):
                for asin in node.asins:
                    key = f"{asin}-{marketplace}"
                    all_asins.setdefault(key, AudiobookNode(asin=asin, marketplace=marketplace))
            elif isinstance(node, AudiobookCarouselNode) and len(node.asins) >= 4:
                for asin in node.asins:
                    key = f"{asin}-{marketplace}"
                    all_asins.setdefault(key, AudiobookNode(asin=asin, marketplace=marketplace))

        # --- Phase 2: batch-resolve what already exists in Contentful ---
        resolved: dict[str, str] = {}  # key → entry_id
        if all_asins:
            self._emit("resolving_asins", count=len(all_asins))
            existing = await self.find_entries(
                "asin",
                {"fields.uniqueKey[in]": ",".join(all_asins.keys())},
                limit=len(all_asins),
            )
            for item in existing:
                key = item["fields"].get("uniqueKey", {}).get("en-US")
                if not key:
                    continue
                entry_id = item["sys"]["id"]
                if not item["sys"].get("publishedVersion"):
                    try:
                        await self.publish_entry(entry_id, item["sys"]["version"])
                    except Exception as e:
                        if not hasattr(e, "response"):
                            raise
                        self._emit("asin_draft_cleanup", asin=key, entry_id=entry_id)
                        await self.delete_entry(entry_id, item["sys"]["version"])
                        continue
                resolved[key] = entry_id

            # --- Phase 3: enrich + write missing ASINs concurrently ---
            missing_nodes = [node for key, node in all_asins.items() if key not in resolved]
            if missing_nodes:
                self._emit("enriching_asins", count=len(missing_nodes))
                await enrich_audiobook_nodes(missing_nodes, on_progress=self._on_progress)

                async def _write_one(node: AudiobookNode) -> None:
                    entry_id = await self.write_asin(node)
                    resolved[f"{node.asin}-{node.marketplace}"] = entry_id

                await asyncio.gather(*[_write_one(n) for n in missing_nodes])

            # brief pause to let Contentful's search index catch up
            await asyncio.sleep(1.5)
            logger.debug("asin phase — %d total, %d created — %.2fs", len(all_asins), len(missing_nodes), time.monotonic() - t0)

        # --- Phase 4: backfill source_id / asin_entry_ids on all nodes ---
        for node in post.body:
            if isinstance(node, AudiobookNode):
                node.source_id = resolved.get(f"{node.asin}-{node.marketplace}")
            elif isinstance(node, AudiobookListNode):
                node.asin_entry_ids = [resolved[f"{a}-{marketplace}"] for a in node.asins if f"{a}-{marketplace}" in resolved]
            elif isinstance(node, AudiobookCarouselNode):
                node.asin_entry_ids = [resolved[f"{a}-{marketplace}"] for a in node.asins if f"{a}-{marketplace}" in resolved]

        # --- Phase 5: create list + carousel entries concurrently ---
        async def _write_list(node: AudiobookListNode) -> None:
            if not node.asins:
                msg = f"AudiobookListNode skipped: requires at least 1 ASIN, got 0"
                logger.error(msg)
                self._emit("list_skipped", reason=msg)
                return
            node.source_id = await self.write_asin_list(node, [])
            logger.debug("asinsList %s — %d asins — %.2fs", node.source_id, len(node.asins), time.monotonic() - t0)

        async def _write_carousel(node: AudiobookCarouselNode) -> None:
            if len(node.asins) < 4:
                msg = f"AudiobookCarouselNode skipped: requires at least 4 ASINs, got {len(node.asins)}"
                logger.error(msg)
                self._emit("carousel_skipped", reason=msg, asins=node.asins)
                return
            node.source_id = await self.write_asin_carousel(node, [])
            logger.debug("asinsCarousel %s — %d asins — %.2fs", node.source_id, len(node.asins), time.monotonic() - t0)

        embed_tasks = [
            _write_list(node) for node in post.body if isinstance(node, AudiobookListNode)
        ] + [
            _write_carousel(node) for node in post.body if isinstance(node, AudiobookCarouselNode)
        ]
        if embed_tasks:
            try:
                await asyncio.gather(*embed_tasks)
            except Exception:
                logger.exception("Failed to write list/carousel blocks")
                raise

    async def _prepare_author(self: "ContentfulClient", author: Author) -> None:
        if isinstance(author.picture, LocalAsset):
            author.picture = await self.upload_local_asset(author.picture)
        if author.seo and isinstance(author.seo.og_image, LocalAsset):
            author.seo.og_image = await self.upload_local_asset(author.seo.og_image)
        if author.seo:
            await self.write_seo(author.seo, f"SEO Settings: {author.name}")

    async def write_author(self: "ContentfulClient", author: Author, publish: bool = True) -> Author:
        if not author.source_id:
            raise ValueError("author.source_id is required for write_author")
        await self._prepare_author(author)
        self._emit("writing_author", entry_id=author.source_id)
        entry = await self.get_entry(author.source_id)
        updated = await self.update_entry(author.source_id, entry["sys"]["version"], _author_to_fields(author))
        if publish:
            await self.publish_entry(author.source_id, updated["sys"]["version"])
        return await self.read_author(author.source_id)

    async def create_author(self: "ContentfulClient", author: Author, publish: bool = False) -> Author:
        await self._prepare_author(author)
        self._emit("creating_author", slug=author.slug)
        raw = await self.create_entry("author", _author_to_fields(author))
        author.source_id = raw["sys"]["id"]
        if publish:
            await self.publish_entry(author.source_id, raw["sys"]["version"])
        return await self.read_author(author.source_id)

    async def write_post(self: "ContentfulClient", post: Post, publish: bool = True) -> Post:
        if not post.source_id:
            raise ValueError("post.source_id is required for write_post")
        await self._prepare_post(post)
        t1 = time.monotonic()
        self._emit("writing_post", entry_id=post.source_id)
        entry = await self.get_entry(post.source_id)
        updated = await self.update_entry(post.source_id, entry["sys"]["version"], _post_to_fields(post))
        if publish:
            await self.publish_entry(post.source_id, updated["sys"]["version"])
        logger.debug("post update+publish — %.2fs", time.monotonic() - t1)
        return await self.read_post(post.source_id, post.locale)

    async def create_post(self: "ContentfulClient", post: Post, publish: bool = False) -> Post:
        await self._prepare_post(post)
        t1 = time.monotonic()
        self._emit("creating_post", slug=post.slug, locale=post.locale)
        raw = await self.create_entry("post", _post_to_fields(post))
        post.source_id = raw["sys"]["id"]
        if publish:
            await self.publish_entry(post.source_id, raw["sys"]["version"])
        logger.debug("post create+publish — %.2fs", time.monotonic() - t1)
        return await self.read_post(post.source_id, post.locale)
