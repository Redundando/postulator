from __future__ import annotations
from typing import Any

from ._base import (
    BasePlaceholder, ml, split_lines, parse_kv_segments,
    resolve_aliases, parse_bool, normalize_key,
)
from ....models import SeoMeta


_ALIASES: dict[str, str] = {
    "meta_title": "meta_title",
    "title": "meta_title",
    "meta_description": "meta_description",
    "desc": "meta_description",
    "og_title": "og_title",
    "open_graph_title": "og_title",
    "og_description": "og_description",
    "open_graph_description": "og_description",
    "no_index": "no_index",
    "source_id": "source_id",
    "id": "source_id",
    "label": "label",
    "schema_type": "schema_type",
    "slug_replacement": "slug_replacement",
    "slug_redirect": "slug_redirect",
    "external_links_source_code": "external_links_source_code",
    "source_code": "external_links_source_code",
}


def parse_seo_fields(kv: dict[str, str]) -> dict[str, Any]:
    """Parse SEO fields from a raw kv dict into a seo result dict."""
    seo = resolve_aliases(kv, _ALIASES)
    if not seo:
        return {}

    no_index = None
    if "no_index" in seo:
        no_index = parse_bool(seo["no_index"])

    return {
        "source_id": seo.get("source_id"),
        "label": seo.get("label"),
        "meta_title": seo.get("meta_title"),
        "meta_description": seo.get("meta_description"),
        "og_title": seo.get("og_title"),
        "og_description": seo.get("og_description"),
        "no_index": no_index,
        "schema_type": seo.get("schema_type"),
        "slug_replacement": seo.get("slug_replacement"),
        "slug_redirect": seo.get("slug_redirect"),
        "external_links_source_code": seo.get("external_links_source_code"),
    }


def has_seo_fields(kv: dict[str, str]) -> bool:
    """Check if a kv dict contains any SEO-related keys."""
    for key in kv:
        if normalize_key(key) in _ALIASES:
            return True
    return False


class SeoPlaceholder(BasePlaceholder):
    keywords = ["seo"]

    @classmethod
    def format(cls, seo: SeoMeta, **ctx) -> str:
        lines = []
        if seo.source_id:
            lines.append(f"source-id = {seo.source_id}")
        if seo.label:
            lines.append(f"label = {seo.label}")
        if seo.meta_title:
            lines.append(f"meta-title = {seo.meta_title}")
        if seo.meta_description:
            lines.append(f"meta-description = {seo.meta_description}")
        if seo.og_title:
            lines.append(f"og-title = {seo.og_title}")
        if seo.og_description:
            lines.append(f"og-description = {seo.og_description}")
        if seo.no_index is not None:
            lines.append(f"no-index = {str(seo.no_index).lower()}")
        if seo.schema_type:
            lines.append(f"schema-type = {seo.schema_type}")
        if seo.slug_replacement:
            lines.append(f"slug-replacement = {seo.slug_replacement}")
        if seo.slug_redirect:
            lines.append(f"slug-redirect = {seo.slug_redirect}")
        if seo.external_links_source_code:
            lines.append(f"external-links-source-code = {seo.external_links_source_code}")
        return ml("SEO", lines)

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        lines = split_lines(content)
        kv = parse_kv_segments(lines)
        result = parse_seo_fields(kv)
        result["type"] = "seo"
        return result
