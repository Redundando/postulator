"""Contentful adapter — orchestrates reading and writing posts, authors, tags."""

from __future__ import annotations
import asyncio
import logging
from typing import Any

from ...models import Post, Author, TagRef
from ...marketplace import locale_to_country_code
from ...models import (
    AudiobookNode, AudiobookListNode, AudiobookCarouselNode,
    ContentImageNode, EmbeddedAssetNode, LocalAsset,
)
from ...events import (
    PostInvalidEvent, ResolvingAsinsEvent, AsinDraftCleanupEvent,
    EnrichingAsinsEvent, ListSkippedEvent, CarouselSkippedEvent,
    CreatingPostEvent, WritingPostEvent, FetchingEntriesEvent,
    FetchingNestedEvent, ParsingEvent, CreatingAuthorEvent,
    WritingAuthorEvent,
)
from ._helpers import _field, _linked_entry_ids, _entry_ids_from_links
from .assets import upload_local_asset
from .handlers.audiobook import AudiobookHandler
from .handlers.audiobook_list import AudiobookListHandler
from .handlers.audiobook_carousel import AudiobookCarouselHandler
from .handlers.seo import SeoHandler
from .handlers.author import AuthorHandler
from .handlers.tag import TagHandler
from .handlers.post import PostHandler
from .client import ContentfulClient

logger = logging.getLogger(__name__)

_audiobook = AudiobookHandler()
_audiobook_list = AudiobookListHandler()
_audiobook_carousel = AudiobookCarouselHandler()
_seo = SeoHandler()
_author = AuthorHandler()
_tag = TagHandler()
_post = PostHandler()


def _embedded_ids_from_richtext(richtext: dict) -> list[str]:
    ids = []
    nt = richtext.get("nodeType", "")
    if nt == "embedded-entry-block":
        eid = richtext.get("data", {}).get("target", {}).get("sys", {}).get("id")
        if eid:
            ids.append(eid)
    for child in richtext.get("content", []):
        ids.extend(_embedded_ids_from_richtext(child))
    return ids


class ContentfulAdapter:
    """High-level Contentful adapter. Wraps a ContentfulClient with orchestration logic."""

    def __init__(self, client: ContentfulClient):
        self.client = client

    # ------------------------------------------------------------------
    # Post write pipeline
    # ------------------------------------------------------------------

    async def _validate_post(self, post: Post) -> str:
        """Validate post and return marketplace string. Raises on invalid."""
        if not post.body:
            msg = f"Post {post.slug!r} has an empty body — aborting"
            self.client._emit(PostInvalidEvent(slug=post.slug, reason=msg))
            raise ValueError(msg)
        try:
            locale_to_country_code(post.locale)
        except ValueError:
            msg = f"Post {post.slug!r} has unknown locale {post.locale!r} — aborting"
            self.client._emit(PostInvalidEvent(slug=post.slug, reason=msg))
            raise ValueError(msg)
        return post.locale.split("-")[-1].upper()

    async def _upload_post_assets(self, post: Post) -> None:
        """Upload any LocalAsset on the post (featured image, SEO, body embeds)."""
        if isinstance(post.featured_image, LocalAsset):
            post.featured_image = await upload_local_asset(self.client, post.featured_image)
        if post.seo and isinstance(post.seo.og_image, LocalAsset):
            post.seo.og_image = await upload_local_asset(self.client, post.seo.og_image)
        for node in post.body:
            if isinstance(node, ContentImageNode) and isinstance(node.image, LocalAsset):
                node.image = await upload_local_asset(self.client, node.image)
            elif isinstance(node, EmbeddedAssetNode) and isinstance(node.image, LocalAsset):
                node.image = await upload_local_asset(self.client, node.image)

    async def _resolve_post_asins(self, post: Post, marketplace: str) -> dict[str, str]:
        """Collect, deduplicate, resolve, enrich, and create all ASIN entries. Returns {unique_key: entry_id}."""
        from ...enrichers.audible import enrich_batch
        from ...models import AudiobookAuthor, AudiobookNarrator

        all_asins: dict[str, AudiobookNode] = {}
        for node in post.body:
            if isinstance(node, AudiobookNode):
                if not node.marketplace:
                    node.marketplace = marketplace
                all_asins.setdefault(f"{node.asin}-{node.marketplace}", node)
            elif isinstance(node, AudiobookListNode):
                for asin in node.asins:
                    all_asins.setdefault(f"{asin}-{marketplace}", AudiobookNode(asin=asin, marketplace=marketplace))
            elif isinstance(node, AudiobookCarouselNode) and len(node.asins) >= 4:
                for asin in node.asins:
                    all_asins.setdefault(f"{asin}-{marketplace}", AudiobookNode(asin=asin, marketplace=marketplace))

        if not all_asins:
            return {}

        self.client._emit(ResolvingAsinsEvent(count=len(all_asins)))
        resolved: dict[str, str] = {}

        existing = await self.client.find_entries(
            "asin", {"fields.uniqueKey[in]": ",".join(all_asins.keys())}, limit=len(all_asins),
        )
        for item in existing:
            key = item["fields"].get("uniqueKey", {}).get("en-US")
            if not key:
                continue
            entry_id = item["sys"]["id"]
            if not item["sys"].get("publishedVersion"):
                try:
                    await self.client.publish_entry(entry_id, item["sys"]["version"])
                except Exception as e:
                    if not hasattr(e, "response"):
                        raise
                    self.client._emit(AsinDraftCleanupEvent(asin=key, entry_id=entry_id))
                    await self.client.delete_entry(entry_id, item["sys"]["version"])
                    continue
            resolved[key] = entry_id

        missing_nodes = [node for key, node in all_asins.items() if key not in resolved]
        if missing_nodes:
            self.client._emit(EnrichingAsinsEvent(count=len(missing_nodes)))
            items = [{"asin": n.asin, "marketplace": n.marketplace} for n in missing_nodes]
            results = await enrich_batch(items, on_progress=self.client._on_progress)
            for node, data in zip(missing_nodes, results):
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

            async def _write_one(n: AudiobookNode) -> None:
                resolved[f"{n.asin}-{n.marketplace}"] = await _audiobook.write(n, self.client)

            await asyncio.gather(*[_write_one(n) for n in missing_nodes])

        await asyncio.sleep(1.5)
        return resolved

    async def _backfill_asin_ids(self, post: Post, resolved: dict[str, str], marketplace: str) -> None:
        """Set source_id / asin_entry_ids on body nodes from resolved ASIN map."""
        for node in post.body:
            if isinstance(node, AudiobookNode):
                node.source_id = resolved.get(f"{node.asin}-{node.marketplace}")
            elif isinstance(node, AudiobookListNode):
                node.asin_entry_ids = [resolved[f"{a}-{marketplace}"] for a in node.asins if f"{a}-{marketplace}" in resolved]
            elif isinstance(node, AudiobookCarouselNode):
                node.asin_entry_ids = [resolved[f"{a}-{marketplace}"] for a in node.asins if f"{a}-{marketplace}" in resolved]

    async def _write_embed_entries(self, post: Post) -> None:
        """Write list/carousel entries for body nodes that need them."""
        async def _write_list(n: AudiobookListNode) -> None:
            if not n.asins:
                self.client._emit(ListSkippedEvent(reason="AudiobookListNode requires at least 1 ASIN, got 0"))
                return
            n.source_id = await _audiobook_list.write(n, self.client)

        async def _write_carousel(n: AudiobookCarouselNode) -> None:
            if len(n.asins) < 4:
                self.client._emit(CarouselSkippedEvent(reason=f"requires at least 4 ASINs, got {len(n.asins)}", asins=n.asins))
                return
            n.source_id = await _audiobook_carousel.write(n, self.client)

        tasks = [_write_list(n) for n in post.body if isinstance(n, AudiobookListNode)]
        tasks += [_write_carousel(n) for n in post.body if isinstance(n, AudiobookCarouselNode)]
        if tasks:
            await asyncio.gather(*tasks)

    async def _prepare_post(self, post: Post) -> None:
        """Full write preparation: validate, resolve, upload, enrich, create dependencies."""
        marketplace = await self._validate_post(post)
        post.authors = await _author.resolve(post.authors, self.client, post.locale)
        post.tags = await _tag.resolve(post.tags, self.client, post.locale)
        await self._upload_post_assets(post)
        if post.seo:
            await _seo.write(post.seo, self.client, fallback_label=f"SEO Settings: {post.title}")
        resolved = await self._resolve_post_asins(post, marketplace)
        await self._backfill_asin_ids(post, resolved, marketplace)
        await self._write_embed_entries(post)

    async def _prepare_author(self, author: Author) -> None:
        if isinstance(author.picture, LocalAsset):
            author.picture = await upload_local_asset(self.client, author.picture)
        if author.seo and isinstance(author.seo.og_image, LocalAsset):
            author.seo.og_image = await upload_local_asset(self.client, author.seo.og_image)
        if author.seo:
            await _seo.write(author.seo, self.client, fallback_label=f"SEO Settings: {author.name}")

    # ------------------------------------------------------------------
    # Post CRUD
    # ------------------------------------------------------------------

    async def write(self, post: Post, publish: bool = False) -> Post:
        """Create a new post entry. Full pipeline: enrich, upload, create."""
        await self._prepare_post(post)
        self.client._emit(CreatingPostEvent(slug=post.slug, locale=post.locale))
        raw = await self.client.create_entry("post", _post.to_fields(post))
        post.source_id = raw["sys"]["id"]
        if publish:
            await self.client.publish_entry(post.source_id, raw["sys"]["version"])
        return await self.read(post.source_id, post.locale)

    async def update(self, post: Post, publish: bool = True) -> Post:
        """Update an existing post entry. Requires post.source_id."""
        if not post.source_id:
            raise ValueError("post.source_id is required for update")
        await self._prepare_post(post)
        self.client._emit(WritingPostEvent(entry_id=post.source_id))
        entry = await self.client.get_entry(post.source_id)
        updated = await self.client.update_entry(post.source_id, entry["sys"]["version"], _post.to_fields(post))
        if publish:
            await self.client.publish_entry(post.source_id, updated["sys"]["version"])
        return await self.read(post.source_id, post.locale)

    async def read(self, entry_id: str, locale: str = "en-US") -> Post:
        """Read a post and all linked entries/assets into a Post model."""
        main_entry = await self.client.get_entry(entry_id)
        fields = main_entry.get("fields", {})
        richtext_raw = _field(fields, "content", locale)

        ids_to_fetch: set[str] = set()
        if richtext_raw:
            ids_to_fetch.update(_embedded_ids_from_richtext(richtext_raw))
        for ref_field in ("authors", "tags", "category", "seoSettings", "relatedPosts"):
            val = _field(fields, ref_field, locale)
            if isinstance(val, list):
                ids_to_fetch.update(_entry_ids_from_links(val))
            elif isinstance(val, dict):
                ids_to_fetch.update(_entry_ids_from_links([val]))

        raw_entries: dict[str, dict] = {}
        if ids_to_fetch:
            self.client._emit(FetchingEntriesEvent(count=len(ids_to_fetch)))
            raw_entries = await self.client.get_entries(list(ids_to_fetch))
            nested_ids = set(_linked_entry_ids(raw_entries)) - ids_to_fetch
            seo_link = _field(fields, "seoSettings", locale)
            seo_eid = seo_link.get("sys", {}).get("id") if isinstance(seo_link, dict) else None
            if seo_eid and seo_eid in raw_entries:
                similar = _field(raw_entries[seo_eid].get("fields", {}), "similarContent", locale) or []
                nested_ids.update(_entry_ids_from_links(similar))
            if nested_ids:
                self.client._emit(FetchingNestedEvent(count=len(nested_ids)))
                raw_entries.update(await self.client.get_entries(list(nested_ids)))

        raw_assets = await self.client.get_assets(list(_post.collect_asset_ids(fields, raw_entries, locale)))
        self.client._emit(ParsingEvent())
        return _post.from_fields(entry_id, fields, raw_entries, raw_assets, locale)

    # ------------------------------------------------------------------
    # Author CRUD
    # ------------------------------------------------------------------

    async def create_author(self, author: Author, publish: bool = False) -> Author:
        await self._prepare_author(author)
        self.client._emit(CreatingAuthorEvent(slug=author.slug))
        raw = await self.client.create_entry("author", _author.to_fields(author))
        author.source_id = raw["sys"]["id"]
        if publish:
            await self.client.publish_entry(author.source_id, raw["sys"]["version"])
        return await self.read_author(author.source_id)

    async def update_author(self, author: Author, publish: bool = True) -> Author:
        if not author.source_id:
            raise ValueError("author.source_id is required for update_author")
        await self._prepare_author(author)
        self.client._emit(WritingAuthorEvent(entry_id=author.source_id))
        entry = await self.client.get_entry(author.source_id)
        updated = await self.client.update_entry(author.source_id, entry["sys"]["version"], _author.to_fields(author))
        if publish:
            await self.client.publish_entry(author.source_id, updated["sys"]["version"])
        return await self.read_author(author.source_id)

    async def read_author(self, entry_id: str, locale: str = "en-US") -> Author:
        entry = await self.client.get_entry(entry_id)
        fields = entry.get("fields", {})
        ids_to_fetch: set[str] = set()
        seo_link = _field(fields, "seoSettings", locale)
        if isinstance(seo_link, dict):
            ids_to_fetch.update(_entry_ids_from_links([seo_link]))
        raw_entries = await self.client.get_entries(list(ids_to_fetch)) if ids_to_fetch else {}
        raw_assets = await self.client.get_assets(list(_author.collect_asset_ids(fields, raw_entries, locale)))
        return _author.from_entry(entry, raw_entries, raw_assets, locale)

    async def list_authors(self, country_code: str, locale: str = "en-US") -> list[Author]:
        items = await self.client.find_entries("author", {"fields.countryCode": country_code}, limit=self.client._batch_size)
        if not items:
            return []
        seo_ids: set[str] = set()
        for item in items:
            seo_link = _field(item.get("fields", {}), "seoSettings", locale)
            if isinstance(seo_link, dict):
                seo_ids.update(_entry_ids_from_links([seo_link]))
        raw_entries = await self.client.get_entries(list(seo_ids)) if seo_ids else {}
        all_asset_ids: set[str] = set()
        for item in items:
            all_asset_ids.update(_author.collect_asset_ids(item.get("fields", {}), raw_entries, locale))
        raw_assets = await self.client.get_assets(list(all_asset_ids))
        return [_author.from_entry(item, raw_entries, raw_assets, locale) for item in items]

    # ------------------------------------------------------------------
    # Tags + slug lookup
    # ------------------------------------------------------------------

    async def list_tags(self, country_code: str, locale: str = "en-US") -> list[TagRef]:
        return await _tag.list(country_code, locale, self.client)

    async def find_entry_by_slug(self, slug: str, locale: str) -> dict[str, Any] | None:
        country_code = locale_to_country_code(locale)
        for content_type in ("post", "category"):
            items = await self.client.find_entries(content_type, {"fields.slug": slug, "fields.countryCode": country_code})
            if items:
                return items[0]
        return None

    # ------------------------------------------------------------------
    # Direct handler access (for callers that need lower-level control)
    # ------------------------------------------------------------------

    async def upload_asset(self, asset: LocalAsset):
        return await upload_local_asset(self.client, asset)
