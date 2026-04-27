"""Contentful Tag handler."""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from ....models import TagRef
from ....marketplace import locale_to_country_code
from .._helpers import _field
from .base import ContentfulNodeHandler
from ....events import TagResolvedEvent, TagNotFoundEvent

if TYPE_CHECKING:
    from ..client import ContentfulClient

logger = logging.getLogger(__name__)


class TagHandler(ContentfulNodeHandler):
    node_type = "tag"

    def to_contentful(self, node: TagRef) -> dict:
        raise NotImplementedError("TagRef is not a body node")

    def from_contentful(self, raw: dict, **context) -> TagRef:
        locale = context.get("locale", "en-US")
        sys = raw.get("sys", {})
        fields = raw.get("fields", {})
        return TagRef(
            slug=_field(fields, "slug", locale) or "",
            locale=locale,
            name=_field(fields, "name", locale) or "",
            source_id=sys.get("id"),
        )

    async def list(self, country_code: str, locale: str, client: "ContentfulClient") -> list[TagRef]:
        """List all tags for a country code."""
        items = await client.find_entries("tag", {"fields.countryCode": country_code}, limit=client._batch_size)
        tags = []
        for item in items:
            sys = item.get("sys", {})
            fields = item.get("fields", {})
            slug = _field(fields, "slug", locale)
            name = _field(fields, "name", locale)
            if slug and name:
                tags.append(TagRef(slug=slug, locale=locale, name=name, source_id=sys.get("id")))
        return tags

    async def resolve(self, refs: list[TagRef], client: "ContentfulClient", locale: str) -> list[TagRef]:
        """Resolve unresolved TagRefs by name → source_id. Modifies refs in-place, returns resolved list."""
        unresolved = [t for t in refs if not t.source_id]
        if not unresolved:
            return refs
        country_code = locale_to_country_code(locale)
        all_tags = await self.list(country_code, locale, client)
        by_name = {t.name.strip().lower(): t for t in all_tags}
        resolved = []
        for ref in refs:
            if ref.source_id:
                resolved.append(ref)
                continue
            match = by_name.get(ref.name.strip().lower())
            if match:
                ref.source_id = match.source_id
                ref.slug = match.slug
                resolved.append(ref)
                client._emit(TagResolvedEvent(name=ref.name, source_id=match.source_id))
            else:
                client._emit(TagNotFoundEvent(name=ref.name))
                logger.warning("Tag not found: %r (country_code=%s)", ref.name, country_code)
        return resolved
