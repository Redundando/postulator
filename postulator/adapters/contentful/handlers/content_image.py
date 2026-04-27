"""Contentful ContentImageNode handler."""

from ....models import ContentImageNode
from .._helpers import _embedded_block, _field, _parse_asset
from .base import ContentfulNodeHandler


class ContentImageHandler(ContentfulNodeHandler):
    node_type = "content-image"

    def to_contentful(self, node: ContentImageNode) -> dict:
        if not node.source_id:
            raise ValueError("ContentImageNode.source_id is required for write")
        return _embedded_block(node.source_id)

    def from_contentful(self, raw: dict, **context) -> ContentImageNode:
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        return self.from_entry(raw, raw_assets, locale)

    def from_entry(self, entry: dict, raw_assets: dict, locale: str) -> ContentImageNode:
        sys = entry.get("sys", {})
        fields = entry.get("fields", {})
        image_link = _field(fields, "image", locale)
        asset_id = image_link.get("sys", {}).get("id") if isinstance(image_link, dict) else None
        return ContentImageNode(
            source_id=sys.get("id"),
            image=_parse_asset(raw_assets.get(asset_id), locale) if asset_id else None,
            href=_field(fields, "href", locale),
            alignment=_field(fields, "alignment", locale),
            size=_field(fields, "size", locale),
        )
