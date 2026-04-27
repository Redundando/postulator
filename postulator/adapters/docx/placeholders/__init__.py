"""Placeholder formatting and parsing for DOCX <-> Post conversion.

Public API (unchanged from the old monolithic _placeholders.py):
- parse_placeholder(text) -> dict | None
- parse_asset_meta(text) -> dict | None
- format_post_block, format_authors_block, format_tags_block, format_seo_block
- format_audiobook, format_carousel, format_list_node
- format_content_image, format_unknown, format_asset_meta
- Helper re-exports: market_to_locale, locale_to_market, slugify, parse_date_flexible, etc.
"""

from __future__ import annotations

import re
from typing import Any

from ._base import (
    BasePlaceholder,
    normalize_key,
    market_to_locale,
    locale_to_market,
    resolve_locale,
    slugify,
    parse_date_flexible,
    parse_bool,
    split_asins,
    split_content,
    split_lines,
    parse_kv_segments,
    parse_item_line,
    resolve_aliases,
    escape,
    unescape,
)
from ._post import PostPlaceholder
from ._authors import AuthorsPlaceholder
from ._tags import TagsPlaceholder
from ._seo import SeoPlaceholder, parse_seo_fields, has_seo_fields
from ._audiobook import AudiobookPlaceholder
from ._carousel import CarouselPlaceholder
from ._list import ListPlaceholder
from ._content_image import ContentImagePlaceholder
from ._featured_image import FeaturedImagePlaceholder
from ._intro import IntroPlaceholder
from ._unknown import UnknownPlaceholder
from ._asset_meta import format_asset_meta, parse_asset_meta


# ---------------------------------------------------------------------------
# Dispatch table: keyword -> placeholder class
# ---------------------------------------------------------------------------

_ALL_PLACEHOLDERS: list[type[BasePlaceholder]] = [
    PostPlaceholder,
    AuthorsPlaceholder,
    TagsPlaceholder,
    SeoPlaceholder,
    IntroPlaceholder,
    FeaturedImagePlaceholder,
    AudiobookPlaceholder,
    CarouselPlaceholder,
    ListPlaceholder,
    ContentImagePlaceholder,
    UnknownPlaceholder,
]

_DISPATCH: dict[str, type[BasePlaceholder]] = {}
for _cls in _ALL_PLACEHOLDERS:
    for _kw in _cls.keywords:
        _DISPATCH[normalize_key(_kw)] = _cls


# ---------------------------------------------------------------------------
# Block extraction (shared logic)
# ---------------------------------------------------------------------------

def _extract_block(text: str) -> tuple[str, str] | None:
    text = text.strip()
    if not text.startswith("["):
        return None
    inner = text.lstrip("[").rstrip("]").strip()
    if not inner:
        return None
    first_line = inner.split("\n")[0].strip()
    # Strip optional colon from keyword
    if ":" in first_line:
        type_part, _, content = inner.partition(":")
        type_part = type_part.strip()
    elif "\n" in inner:
        type_part, _, content = inner.partition("\n")
        type_part = type_part.strip()
    else:
        # Single keyword or "keyword value" on one line
        # Try to match a known keyword at the start
        parts = first_line.split(None, 1)
        keyword = normalize_key(parts[0]) if parts else ""
        if keyword in _DISPATCH:
            return (keyword, parts[1].strip() if len(parts) > 1 else "")
        # Try multi-word keyword (e.g. "featured image")
        keyword = normalize_key(first_line)
        if keyword in _DISPATCH:
            return (keyword, "")
        return None
    keyword = normalize_key(type_part)
    if keyword in _DISPATCH:
        return (keyword, content.strip())
    # Try the full first line as keyword (no content)
    keyword = normalize_key(first_line.rstrip(":"))
    if keyword in _DISPATCH:
        rest = inner[len(first_line):].strip()
        return (keyword, rest)
    return None


# ---------------------------------------------------------------------------
# Public parse function
# ---------------------------------------------------------------------------

def parse_placeholder(text: str) -> dict[str, Any] | None:
    """Parse a bracket-syntax placeholder string (single or multi-line).
    Returns a dict with 'type' key and parsed fields, or None if not a placeholder.
    """
    extracted = _extract_block(text)
    if not extracted:
        return None

    ptype, content = extracted

    cls = _DISPATCH.get(ptype)
    if cls:
        return cls.parse(content)
    return None


# ---------------------------------------------------------------------------
# Public format functions (thin wrappers for backward compat)
# ---------------------------------------------------------------------------

def format_post_block(post):
    return PostPlaceholder.format(post)

def format_authors_block(authors):
    return AuthorsPlaceholder.format(authors)

def format_tags_block(tags):
    return TagsPlaceholder.format(tags)

def format_seo_block(seo):
    return SeoPlaceholder.format(seo)

def format_audiobook(node, post_market=None):
    return AudiobookPlaceholder.format(node, post_market=post_market)

def format_carousel(node, post_market=None):
    return CarouselPlaceholder.format(node, post_market=post_market)

def format_list_node(node, post_market=None):
    return ListPlaceholder.format(node, post_market=post_market)

def format_featured_image(asset):
    return FeaturedImagePlaceholder.format(asset)


def format_content_image(node):
    return ContentImagePlaceholder.format(node)

def format_unknown(node):
    return UnknownPlaceholder.format(node)


# Re-export for backward compat
def collect_placeholder_text(lines, start):
    combined = lines[start]
    if "]" in combined:
        return combined, start
    for i in range(start + 1, len(lines)):
        combined += "\n" + lines[i]
        if "]" in lines[i]:
            return combined, i
    return combined, len(lines) - 1


# Keep _slugify and _parse_date_flexible accessible under old names
_slugify = slugify
_parse_date_flexible = parse_date_flexible
