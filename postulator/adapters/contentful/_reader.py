"""Contentful read logic — mixed into ContentfulClient via _ReaderMixin."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from ...models import Post, Author, AuthorRef, TagRef, AssetRef, SeoMeta
from ...nodes import (
    BlockNode, DocumentNode, InlineNode,
    TextNode, HyperlinkNode,
    ParagraphNode, HeadingNode, ListNode, ListItemNode, BlockquoteNode, HrNode,
    AudiobookAuthor, AudiobookNarrator, AudiobookSeries,
    AudiobookNode, AudiobookListItem, AudiobookListNode, AudiobookCarouselNode, ContentImageNode,
    TableCellNode, TableRowNode, TableNode,
    UnknownNode,
)

if TYPE_CHECKING:
    from .client import ContentfulClient


def _field(fields: dict, key: str, locale: str) -> Any:
    f = fields.get(key, {})
    return f.get(locale) or f.get("en-US")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


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


def _parse_inline(node: dict) -> InlineNode:
    nt = node.get("nodeType", "")
    if nt == "hyperlink":
        url = node.get("data", {}).get("uri", "")
        children = [_parse_inline(c) for c in node.get("content", []) if c.get("nodeType") == "text"]
        return HyperlinkNode(url=url, children=children)
    value = node.get("value", "")
    marks = [m["type"] for m in node.get("marks", []) if m.get("type") in ("bold", "italic", "underline", "code", "superscript", "subscript")]
    return TextNode(value=value, marks=marks)


def _parse_paragraph(node: dict) -> ParagraphNode:
    return ParagraphNode(children=[_parse_inline(c) for c in node.get("content", [])])


def _parse_block(node: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> BlockNode:
    nt = node.get("nodeType", "")

    if nt == "paragraph":
        return _parse_paragraph(node)

    if nt.startswith("heading-"):
        level = int(nt.split("-")[1])
        return HeadingNode(level=level, children=[_parse_inline(c) for c in node.get("content", [])])

    if nt in ("unordered-list", "ordered-list"):
        items = [
            ListItemNode(children=[_parse_paragraph(p) for p in item.get("content", []) if p.get("nodeType") == "paragraph"])
            for item in node.get("content", [])
        ]
        return ListNode(ordered=(nt == "ordered-list"), children=items)

    if nt == "blockquote":
        return BlockquoteNode(children=[_parse_paragraph(c) for c in node.get("content", []) if c.get("nodeType") == "paragraph"])

    if nt == "hr":
        return HrNode()

    if nt == "table":
        rows = [
            TableRowNode(children=[
                TableCellNode(
                    is_header=(cell.get("nodeType") == "table-header-cell"),
                    children=[_parse_block(child, raw_entries, raw_assets, locale) for child in cell.get("content", [])],
                )
                for cell in row.get("content", [])
            ])
            for row in node.get("content", [])
        ]
        return TableNode(children=rows)

    if nt == "embedded-entry-block":
        entry_id = node.get("data", {}).get("target", {}).get("sys", {}).get("id")
        if entry_id and entry_id in raw_entries:
            return _parse_embed(raw_entries[entry_id], raw_entries, raw_assets, locale)
        return UnknownNode(raw=node)

    return UnknownNode(raw=node)


def _parse_embed(entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> BlockNode:
    sys = entry.get("sys", {})
    ct = sys.get("contentType", {}).get("sys", {}).get("id", "")
    fields = entry.get("fields", {})

    if ct == "asin":
        cover_url = _field(fields, "cover", locale)
        raw_authors = _field(fields, "authors", locale) or []
        raw_narrators = _field(fields, "narrators", locale) or []
        raw_series = _field(fields, "series", locale) or []
        return AudiobookNode(
            source_id=sys.get("id"),
            asin=_field(fields, "asin", locale) or "",
            marketplace=_field(fields, "marketplace", locale) or "",
            title=_field(fields, "title", locale),
            cover_url=cover_url,
            summary=_field(fields, "summary", locale),
            label=_field(fields, "label", locale),
            pdp=_field(fields, "pdp", locale),
            release_date=_field(fields, "releaseDate", locale),
            authors=[AudiobookAuthor(**a) for a in raw_authors if isinstance(a, dict)],
            narrators=[AudiobookNarrator(**n) for n in raw_narrators if isinstance(n, dict)],
            series=[AudiobookSeries(**s) for s in raw_series if isinstance(s, dict)],
        )

    if ct == "asinsList":
        asins = _resolve_asins(_field(fields, "asins", locale), raw_entries, locale)
        asin_entry_ids = _entry_ids_from_links(_field(fields, "asins", locale))
        asin_items = _parse_asin_descriptions(_field(fields, "asinDescriptions", locale))
        return AudiobookListNode(
            source_id=sys.get("id"),
            asins=asins,
            asin_entry_ids=asin_entry_ids,
            asin_items=asin_items,
            title=_field(fields, "title", locale),
            label=_field(fields, "label", locale),
            body_copy=_field(fields, "copy", locale),
            player_type=_field(fields, "playerType", locale) or "Cover",
            asins_per_row=_field(fields, "asinsPerRow", locale) or 1,
            descriptions=_field(fields, "descriptions", locale) or "Full",
            filters=_field(fields, "filters", locale),
            options=_field(fields, "options", locale) or [],
        )

    if ct == "asinsCarousel":
        asins = _resolve_asins(_field(fields, "asins", locale), raw_entries, locale)
        asin_entry_ids = _entry_ids_from_links(_field(fields, "asins", locale))
        return AudiobookCarouselNode(
            source_id=sys.get("id"),
            asins=asins,
            asin_entry_ids=asin_entry_ids,
            items_per_slide=_field(fields, "itemsPerSlide", locale),
            title=_field(fields, "title", locale),
            subtitle=_field(fields, "subtitle", locale),
            body_copy=_field(fields, "copy", locale),
            cta_text=_field(fields, "ctaText", locale),
            cta_url=_field(fields, "ctaUrl", locale),
            options=_field(fields, "options", locale) or [],
        )

    if ct == "contentImage":
        image_link = _field(fields, "image", locale)
        asset_id = image_link.get("sys", {}).get("id") if isinstance(image_link, dict) else None
        return ContentImageNode(
            source_id=sys.get("id"),
            image=_parse_asset(raw_assets.get(asset_id), locale) if asset_id else None,
            href=_field(fields, "href", locale),
            alignment=_field(fields, "alignment", locale),
            size=_field(fields, "size", locale),
        )

    return UnknownNode(raw=entry)


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


def _resolve_asins(links: list | None, raw_entries: dict[str, dict], locale: str) -> list[str]:
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


def _parse_body(richtext: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> DocumentNode:
    return [_parse_block(node, raw_entries, raw_assets, locale) for node in richtext.get("content", [])]


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


def _collect_asset_ids(fields: dict, raw_entries: dict[str, dict], locale: str) -> set[str]:
    asset_ids: set[str] = set()
    image_link = _field(fields, "image", locale)
    if isinstance(image_link, dict) and image_link.get("sys", {}).get("linkType") == "Asset":
        asset_ids.add(image_link["sys"]["id"])
    for entry in raw_entries.values():
        ct = entry.get("sys", {}).get("contentType", {}).get("sys", {}).get("id", "")
        if ct == "contentImage":
            link = _field(entry.get("fields", {}), "image", locale)
            if isinstance(link, dict) and link.get("sys", {}).get("linkType") == "Asset":
                asset_ids.add(link["sys"]["id"])
    seo_link = _field(fields, "seoSettings", locale)
    if isinstance(seo_link, dict):
        seo_eid = seo_link.get("sys", {}).get("id")
        if seo_eid and seo_eid in raw_entries:
            og_link = _field(raw_entries[seo_eid].get("fields", {}), "openGraphImage", locale)
            if isinstance(og_link, dict) and og_link.get("sys", {}).get("linkType") == "Asset":
                asset_ids.add(og_link["sys"]["id"])
    return asset_ids


def _collect_author_asset_ids(fields: dict, raw_entries: dict[str, dict], locale: str) -> set[str]:
    asset_ids: set[str] = set()
    picture_link = _field(fields, "picture", locale)
    if isinstance(picture_link, dict) and picture_link.get("sys", {}).get("linkType") == "Asset":
        asset_ids.add(picture_link["sys"]["id"])
    seo_link = _field(fields, "seoSettings", locale)
    seo_eid = seo_link.get("sys", {}).get("id") if isinstance(seo_link, dict) else None
    if seo_eid and seo_eid in raw_entries:
        og_link = _field(raw_entries[seo_eid].get("fields", {}), "openGraphImage", locale)
        if isinstance(og_link, dict) and og_link.get("sys", {}).get("linkType") == "Asset":
            asset_ids.add(og_link["sys"]["id"])
    return asset_ids


def _parse_author(entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> Author:
    sys = entry.get("sys", {})
    fields = entry.get("fields", {})
    picture_link = _field(fields, "picture", locale)
    picture_id = picture_link.get("sys", {}).get("id") if isinstance(picture_link, dict) else None
    return Author(
        source_id=sys.get("id"),
        country_code=_field(fields, "countryCode", locale),
        slug=_field(fields, "slug", locale) or "",
        name=_field(fields, "name", locale) or "",
        short_name=_field(fields, "shortName", locale),
        title=_field(fields, "title", locale),
        bio=_field(fields, "bio", locale),
        picture=_parse_asset(raw_assets.get(picture_id), locale) if picture_id else None,
        seo=_parse_seo(fields, raw_entries, raw_assets, locale),
    )


def _parse_authors(fields: dict, raw_entries: dict[str, dict], locale: str) -> list[AuthorRef]:
    authors = []
    for eid in _entry_ids_from_links(_field(fields, "authors", locale) or []):
        e = raw_entries.get(eid, {})
        ef = e.get("fields", {})
        slug = _field(ef, "slug", locale)
        name = _field(ef, "name", locale)
        if slug and name:
            authors.append(AuthorRef(slug=slug, locale=locale, name=name, source_id=eid))
    return authors


def _parse_tags(fields: dict, raw_entries: dict[str, dict], locale: str) -> list[TagRef]:
    tags = []
    tag_links = (_field(fields, "tags", locale) or []) + (
        [_field(fields, "category", locale)] if _field(fields, "category", locale) else []
    )
    for eid in _entry_ids_from_links(tag_links):
        e = raw_entries.get(eid, {})
        ef = e.get("fields", {})
        slug = _field(ef, "slug", locale)
        name = _field(ef, "name", locale)
        if slug and name:
            tags.append(TagRef(slug=slug, locale=locale, name=name, source_id=eid))
    return tags


def _parse_seo(fields: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> SeoMeta | None:
    seo_link = _field(fields, "seoSettings", locale)
    seo_eid_list = _entry_ids_from_links([seo_link] if seo_link else [])
    if not seo_eid_list:
        return None
    se = raw_entries.get(seo_eid_list[0], {}).get("fields", {})
    og_link = _field(se, "openGraphImage", locale)
    og_asset_id = og_link.get("sys", {}).get("id") if isinstance(og_link, dict) else None
    json_ld_link = _field(se, "jsonLd", locale)
    return SeoMeta(
        source_id=seo_eid_list[0],
        label=_field(se, "label", locale),
        slug_replacement=_field(se, "slugReplacement", locale),
        slug_redirect=_field(se, "slugRedirect", locale),
        no_index=_field(se, "noIndex", locale),
        meta_title=_field(se, "metaTitle", locale),
        meta_description=_field(se, "metaDescription", locale),
        og_title=_field(se, "openGraphTitle", locale),
        og_description=_field(se, "openGraphDescription", locale),
        og_image=_parse_asset(raw_assets.get(og_asset_id), locale) if og_asset_id else None,
        schema_type=_field(se, "schemaType", locale),
        json_ld_id=json_ld_link.get("sys", {}).get("id") if isinstance(json_ld_link, dict) else None,
        similar_content_ids=_entry_ids_from_links(_field(se, "similarContent", locale) or []),
        external_links_source_code=_field(se, "externalLinksSourceCode", locale),
    )


class _ReaderMixin:
    async def read_author(
        self: "ContentfulClient",
        entry_id: str,
        locale: str = "en-US",
    ) -> Author:
        entry = await self.get_entry(entry_id)
        fields = entry.get("fields", {})
        ids_to_fetch: set[str] = set()
        seo_link = _field(fields, "seoSettings", locale)
        if isinstance(seo_link, dict):
            ids_to_fetch.update(_entry_ids_from_links([seo_link]))
        raw_entries: dict[str, dict] = await self.get_entries(list(ids_to_fetch)) if ids_to_fetch else {}
        raw_assets = await self.get_assets(list(_collect_author_asset_ids(fields, raw_entries, locale)))
        return _parse_author(entry, raw_entries, raw_assets, locale)

    async def list_authors(
        self: "ContentfulClient",
        country_code: str,
        locale: str = "en-US",
    ) -> list[Author]:
        items = await self.find_entries(
            "author",
            {"fields.countryCode": country_code},
            limit=self._batch_size,
        )
        if not items:
            return []
        seo_ids: set[str] = set()
        for item in items:
            seo_link = _field(item.get("fields", {}), "seoSettings", locale)
            if isinstance(seo_link, dict):
                seo_ids.update(_entry_ids_from_links([seo_link]))
        raw_entries = await self.get_entries(list(seo_ids)) if seo_ids else {}
        all_asset_ids: set[str] = set()
        for item in items:
            all_asset_ids.update(_collect_author_asset_ids(item.get("fields", {}), raw_entries, locale))
        raw_assets = await self.get_assets(list(all_asset_ids))
        return [_parse_author(item, raw_entries, raw_assets, locale) for item in items]

    async def read_post(
        self: "ContentfulClient",
        entry_id: str,
        locale: str = "en-US",
    ) -> Post:
        main_entry = await self.get_entry(entry_id)
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
            self._emit("fetching_entries", count=len(ids_to_fetch))
            raw_entries = await self.get_entries(list(ids_to_fetch))
            nested_ids = set(_linked_entry_ids(raw_entries)) - ids_to_fetch
            seo_link = _field(fields, "seoSettings", locale)
            seo_eid = seo_link.get("sys", {}).get("id") if isinstance(seo_link, dict) else None
            if seo_eid and seo_eid in raw_entries:
                similar = _field(raw_entries[seo_eid].get("fields", {}), "similarContent", locale) or []
                nested_ids.update(_entry_ids_from_links(similar))
            if nested_ids:
                self._emit("fetching_nested", count=len(nested_ids))
                raw_entries.update(await self.get_entries(list(nested_ids)))

        raw_assets = await self.get_assets(list(_collect_asset_ids(fields, raw_entries, locale)))

        self._emit("parsing")

        body = _parse_body(richtext_raw, raw_entries, raw_assets, locale) if richtext_raw else []

        image_link = _field(fields, "image", locale)
        asset_id = image_link.get("sys", {}).get("id") if isinstance(image_link, dict) else None

        return Post(
            source_id=entry_id,
            slug=_field(fields, "slug", locale) or "",
            locale=locale,
            title=_field(fields, "title", locale) or "",
            date=_parse_date(_field(fields, "date", locale)) or datetime.now(timezone.utc),
            update_date=_parse_date(_field(fields, "updateDate", locale)),
            introduction=_field(fields, "introduction", locale),
            body=body,
            featured_image=_parse_asset(raw_assets.get(asset_id), locale) if asset_id else None,
            authors=_parse_authors(fields, raw_entries, locale),
            tags=_parse_tags(fields, raw_entries, locale),
            seo=_parse_seo(fields, raw_entries, raw_assets, locale),
            custom_recommended_title=_field(fields, "customRecommendedTitle", locale),
            show_in_feed=not (_field(fields, "hideFromBlogFeed", locale) or False),
            show_publish_date=not (_field(fields, "hidePublishDate", locale) or False),
            show_hero_image=not (_field(fields, "hideHeroImage", locale) or False),
            related_posts=_entry_ids_from_links(_field(fields, "relatedPosts", locale) or []),
        )

    async def list_tags(
        self: "ContentfulClient",
        country_code: str,
        locale: str = "en-US",
    ) -> list[TagRef]:
        items = await self.find_entries(
            "tag",
            {"fields.countryCode": country_code},
            limit=self._batch_size,
        )
        tags = []
        for item in items:
            sys = item.get("sys", {})
            fields = item.get("fields", {})
            slug = _field(fields, "slug", locale)
            name = _field(fields, "name", locale)
            if slug and name:
                tags.append(TagRef(slug=slug, locale=locale, name=name, source_id=sys.get("id")))
        return tags

    async def find_entry_by_slug(
        self: "ContentfulClient",
        slug: str,
        locale: str,
    ) -> dict[str, Any] | None:
        country_code = locale.split("-")[-1].upper()
        for content_type in ("post", "category"):
            items = await self.find_entries(
                content_type,
                {"fields.slug": slug, "fields.countryCode": country_code},
            )
            if items:
                return items[0]
        return None
