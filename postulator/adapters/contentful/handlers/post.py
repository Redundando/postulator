"""Contentful Post handler."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from ....models import Post, TagRef
from ....models import AssetRef
from ....marketplace import locale_to_country_code
from .._helpers import _link, _asset_link, _field, _parse_date, _parse_asset, _entry_ids_from_links
from .base import ContentfulNodeHandler
from .seo import SeoHandler
from .author import AuthorHandler

_seo = SeoHandler()
_author = AuthorHandler()


class PostHandler(ContentfulNodeHandler):
    node_type = "post"

    def to_contentful(self, node: Post) -> dict:
        raise NotImplementedError("Post is not a body node — use to_fields()")

    def from_contentful(self, raw: dict, **context) -> Post:
        raise NotImplementedError("Post is not a body node — use from_fields()")

    def to_fields(self, post: Post) -> dict[str, Any]:
        from . import body_to_contentful
        locale = "en-US"
        country_code = locale_to_country_code(post.locale)

        def f(value: Any) -> dict:
            return {locale: value}

        fields: dict[str, Any] = {
            "slug": f(post.slug),
            "title": f(post.title),
            "countryCode": f(country_code),
            "date": f(post.date.strftime("%Y-%m-%d")),
            "content": f(body_to_contentful(post.body)),
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

    def from_fields(self, entry_id: str, fields: dict, raw_entries: dict, raw_assets: dict, locale: str) -> Post:
        from . import parse_body
        richtext_raw = _field(fields, "content", locale)
        body = parse_body(richtext_raw, raw_entries, raw_assets, locale) if richtext_raw else []

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
            authors=_author.parse_author_refs(fields, raw_entries, locale),
            tags=self.parse_tag_refs(fields, raw_entries, locale),
            seo=_seo.from_fields(fields, raw_entries, raw_assets, locale),
            custom_recommended_title=_field(fields, "customRecommendedTitle", locale),
            show_in_feed=not (_field(fields, "hideFromBlogFeed", locale) or False),
            show_publish_date=not (_field(fields, "hidePublishDate", locale) or False),
            show_hero_image=not (_field(fields, "hideHeroImage", locale) or False),
            related_posts=_entry_ids_from_links(_field(fields, "relatedPosts", locale) or []),
        )

    def parse_tag_refs(self, fields: dict, raw_entries: dict[str, dict], locale: str) -> list[TagRef]:
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

    def collect_asset_ids(self, fields: dict, raw_entries: dict[str, dict], locale: str) -> set[str]:
        asset_ids: set[str] = set()
        image_link = _field(fields, "image", locale)
        if isinstance(image_link, dict) and image_link.get("sys", {}).get("linkType") == "Asset":
            asset_ids.add(image_link["sys"]["id"])
        richtext = _field(fields, "content", locale)
        if isinstance(richtext, dict):
            asset_ids.update(_asset_ids_from_richtext(richtext))
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


def _asset_ids_from_richtext(richtext: dict) -> set[str]:
    ids: set[str] = set()
    if richtext.get("nodeType") == "embedded-asset-block":
        aid = richtext.get("data", {}).get("target", {}).get("sys", {}).get("id")
        if aid:
            ids.add(aid)
    for child in richtext.get("content", []):
        ids.update(_asset_ids_from_richtext(child))
    return ids
