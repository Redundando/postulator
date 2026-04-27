"""Contentful HrNode handler."""

from ....models import HrNode
from .base import ContentfulNodeHandler


class HrHandler(ContentfulNodeHandler):
    node_type = "hr"

    def to_contentful(self, node: HrNode) -> dict:
        return {"nodeType": "hr", "data": {}, "content": []}

    def from_contentful(self, raw: dict, **context) -> HrNode:
        return HrNode()
