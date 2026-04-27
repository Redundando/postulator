"""Contentful UnknownNode handler."""

from ....models import UnknownNode
from .base import ContentfulNodeHandler


class UnknownHandler(ContentfulNodeHandler):
    node_type = "unknown"

    def to_contentful(self, node: UnknownNode) -> dict:
        return node.raw

    def from_contentful(self, raw: dict, **context) -> UnknownNode:
        return UnknownNode(raw=raw)
