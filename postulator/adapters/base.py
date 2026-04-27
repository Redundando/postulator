"""Base classes for postulator adapters and node handlers."""

from __future__ import annotations


class NodeHandler:
    """Base for all adapter node handlers."""

    node_type: str = ""

    def __str__(self):
        return f"{self.__class__.__name__}({self.node_type})"
