"""Contentful SeoMeta handler."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

from ....models import SeoMeta
from ....models import AssetRef
from .._helpers import _link, _asset_link, _field, _parse_asset, _entry_ids_from_links
from .base import ContentfulNodeHandler

if TYPE_CHECKING:
    from ..client import ContentfulClient


class SeoHandler(ContentfulNodeHandler):
    node_type = "seo"

    def to_contentful(self, node: SeoMeta) -> dict:
        raise NotImplementedError("SeoMeta is not a body node — use to_fields()")

    def from_contentful(self, raw: dict, **context) -> SeoMeta | None:
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        return self.from_fields(raw, raw_entries, raw_assets, locale)

    def to_fields(self, seo: SeoMeta, fallback_label: str) -> dict[str, Any]:
        def f(value: Any) -> dict:
            return {"en-US": value}

        fields: dict[str, Any] = {
            "label": f(seo.label or fallback_label),
        }
        if seo.slug_replacement:
            fields["slugReplacement"] = f(seo.slug_replacement)
        if seo.slug_redirect:
            fields["slugRedirect"] = f(seo.slug_redirect)
        if seo.no_index is not None:
            fields["noIndex"] = f(seo.no_index)
        if seo.meta_title:
            fields["metaTitle"] = f(seo.meta_title)
        if seo.meta_description:
            fields["metaDescription"] = f(seo.meta_description)
        if seo.og_title:
            fields["openGraphTitle"] = f(seo.og_title)
        if seo.og_description:
            fields["openGraphDescription"] = f(seo.og_description)
        if isinstance(seo.og_image, AssetRef) and seo.og_image.source_id:
            fields["openGraphImage"] = f(_asset_link(seo.og_image.source_id))
        if seo.schema_type:
            fields["schemaType"] = f(seo.schema_type)
        if seo.json_ld_id:
            fields["jsonLd"] = f(_link(seo.json_ld_id))
        if seo.similar_content_ids:
            fields["similarContent"] = f([_link(eid) for eid in seo.similar_content_ids])
        if seo.external_links_source_code:
            fields["externalLinksSourceCode"] = f(seo.external_links_source_code)
        return fields

    def from_fields(self, fields: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> SeoMeta | None:
        seo_link = _field(fields, "seoSettings", locale)
        seo_eid_list = _entry_ids_from_links([seo_link] if seo_link else [])
        if not seo_eid_list:
            return None
        se = raw_entries.get(seo_eid_list[0], {}).get("fields", {})
        og_link = _field(se, "openGraphImage", locale)
        og_asset_id = og_link.get("sys", {}).get("id") if isinstance(og_link, dict) else None
        json_ld_link = _field(se, "jsonLd", locale)
        return SeoMeta(
            source_id=seo_eid_list[0],
            label=_field(se, "label", locale),
            slug_replacement=_field(se, "slugReplacement", locale),
            slug_redirect=_field(se, "slugRedirect", locale),
            no_index=_field(se, "noIndex", locale),
            meta_title=_field(se, "metaTitle", locale),
            meta_description=_field(se, "metaDescription", locale),
            og_title=_field(se, "openGraphTitle", locale),
            og_description=_field(se, "openGraphDescription", locale),
            og_image=_parse_asset(raw_assets.get(og_asset_id), locale) if og_asset_id else None,
            schema_type=_field(se, "schemaType", locale),
            json_ld_id=json_ld_link.get("sys", {}).get("id") if isinstance(json_ld_link, dict) else None,
            similar_content_ids=_entry_ids_from_links(_field(se, "similarContent", locale) or []),
            external_links_source_code=_field(se, "externalLinksSourceCode", locale),
        )

    async def write(self, seo: SeoMeta, client: "ContentfulClient", fallback_label: str = "") -> str:
        """Create or update a seoSettings entry. Returns entry ID."""
        fields = self.to_fields(seo, fallback_label)
        if seo.source_id:
            existing = await client.get_entry(seo.source_id)
            updated = await client.update_entry(seo.source_id, existing["sys"]["version"], fields)
            entry_id = seo.source_id
            version = updated["sys"]["version"]
        else:
            raw = await client.create_entry("seoSettings", fields)
            entry_id = raw["sys"]["id"]
            version = raw["sys"]["version"]
        await client.publish_entry(entry_id, version)
        seo.source_id = entry_id
        return entry_id
