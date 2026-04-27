"""Contentful Author handler."""

from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

from ....models import Author, AuthorRef
from ....models import AssetRef
from ....marketplace import locale_to_country_code
from .._helpers import _link, _asset_link, _field, _parse_asset, _entry_ids_from_links
from .base import ContentfulNodeHandler
from .seo import SeoHandler
from ....events import AuthorResolvedEvent, AuthorNotFoundEvent

if TYPE_CHECKING:
    from ..client import ContentfulClient

logger = logging.getLogger(__name__)
_seo = SeoHandler()


class AuthorHandler(ContentfulNodeHandler):
    node_type = "author"

    def to_contentful(self, node: Author) -> dict:
        raise NotImplementedError("Author is not a body node — use to_fields()")

    def from_contentful(self, raw: dict, **context) -> Author:
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        return self.from_entry(raw, raw_entries, raw_assets, locale)

    def to_fields(self, author: Author) -> dict[str, Any]:
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

    def from_entry(self, entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> Author:
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
            seo=_seo.from_fields(fields, raw_entries, raw_assets, locale),
        )

    def parse_author_refs(self, fields: dict, raw_entries: dict[str, dict], locale: str) -> list[AuthorRef]:
        authors = []
        for eid in _entry_ids_from_links(_field(fields, "authors", locale) or []):
            e = raw_entries.get(eid, {})
            ef = e.get("fields", {})
            slug = _field(ef, "slug", locale)
            name = _field(ef, "name", locale)
            if slug and name:
                authors.append(AuthorRef(slug=slug, locale=locale, name=name, source_id=eid))
        return authors

    def collect_asset_ids(self, fields: dict, raw_entries: dict[str, dict], locale: str) -> set[str]:
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

    # ------------------------------------------------------------------
    # I/O: resolve author refs by name
    # ------------------------------------------------------------------

    async def resolve(self, refs: list[AuthorRef], client: "ContentfulClient", locale: str) -> list[AuthorRef]:
        """Resolve unresolved AuthorRefs by name → source_id. Modifies refs in-place, returns resolved list."""
        unresolved = [a for a in refs if not a.source_id]
        if not unresolved:
            return refs
        country_code = locale_to_country_code(locale)
        items = await client.find_entries("author", {"fields.countryCode": country_code}, limit=client._batch_size)
        by_name: dict[str, dict] = {}
        for item in items:
            name = _field(item.get("fields", {}), "name", "en-US")
            if name:
                by_name[name.strip().lower()] = item
        resolved = []
        for ref in refs:
            if ref.source_id:
                resolved.append(ref)
                continue
            match = by_name.get(ref.name.strip().lower())
            if match:
                ref.source_id = match["sys"]["id"]
                ref.slug = _field(match.get("fields", {}), "slug", "en-US") or ref.slug
                resolved.append(ref)
                client._emit(AuthorResolvedEvent(name=ref.name, source_id=ref.source_id))
            else:
                client._emit(AuthorNotFoundEvent(name=ref.name))
                logger.warning("Author not found: %r (country_code=%s)", ref.name, country_code)
        return resolved
