"""Contentful EmbeddedAssetNode handler."""

from ....models import EmbeddedAssetNode, AssetRef
from .._helpers import _asset_link, _parse_asset
from .base import ContentfulNodeHandler


class EmbeddedAssetHandler(ContentfulNodeHandler):
    node_type = "embedded-asset"

    def to_contentful(self, node: EmbeddedAssetNode) -> dict:
        if not isinstance(node.image, AssetRef) or not node.image.source_id:
            raise ValueError("EmbeddedAssetNode.image must be an AssetRef with source_id for write")
        return {"nodeType": "embedded-asset-block", "data": {"target": _asset_link(node.image.source_id)}, "content": []}

    def from_contentful(self, raw: dict, **context) -> EmbeddedAssetNode | None:
        """Returns EmbeddedAssetNode or None if asset not found."""
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        asset_id = context.get("asset_id", "")
        if asset_id and asset_id in raw_assets:
            parsed = _parse_asset(raw_assets[asset_id], locale)
            if parsed:
                return EmbeddedAssetNode(image=parsed)
        return None
