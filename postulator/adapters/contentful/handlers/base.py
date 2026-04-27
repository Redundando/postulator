"""Base class for Contentful node handlers."""

from __future__ import annotations
from typing import TYPE_CHECKING

from ...base import NodeHandler

if TYPE_CHECKING:
    from ..client import ContentfulClient


class ContentfulNodeHandler(NodeHandler):
    """Base for all Contentful node handlers.

    Required methods:
        to_contentful(node) -> dict       — serialize generic node to Contentful JSON
        from_contentful(raw, **ctx)       — deserialize Contentful JSON to generic node

    Optional methods:
        write(node, client) -> str | None — node-specific I/O during write
    """

    def to_contentful(self, node) -> dict:
        raise NotImplementedError

    def from_contentful(self, raw: dict, **context):
        raise NotImplementedError

    async def write(self, node, client: "ContentfulClient") -> str | None:
        return None
