"""Top-level 'models' command — dumps all Pydantic model schemas as JSON."""

from __future__ import annotations

import argparse
import json
from typing import Any


def cmd_models(_args: argparse.Namespace) -> None:
    """Print JSON schemas for all public postulator models."""
    print(json.dumps(_collect_models(), indent=2))


def _collect_models() -> dict[str, Any]:
    """Return JSON-serialisable schema dict for all public postulator models."""
    from .. import models as m
    from ..models import nodes as n

    model_classes = [
        m.Post, m.AuthorRef, m.TagRef, m.SeoMeta, m.Author,
        n.AssetRef, n.LocalAsset,
        n.TextNode, n.HyperlinkNode,
        n.ParagraphNode, n.HeadingNode, n.ListNode, n.ListItemNode,
        n.BlockquoteNode, n.HrNode,
        n.AudiobookAuthor, n.AudiobookNarrator, n.AudiobookSeries,
        n.AudiobookNode, n.AudiobookListItem, n.AudiobookListNode,
        n.AudiobookCarouselNode, n.ContentImageNode,
        n.TableNode, n.TableRowNode, n.TableCellNode,
        n.UnknownNode,
    ]
    return {cls.__name__: cls.model_json_schema() for cls in model_classes}
