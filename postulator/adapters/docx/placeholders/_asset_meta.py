from __future__ import annotations

from ._base import parse_kv_segments
from ....models import AssetRef


def format_asset_meta(asset: AssetRef) -> str:
    parts = []
    if asset.source_id:
        parts.append(f"source_id={asset.source_id}")
    if asset.title:
        parts.append(f"title={asset.title}")
    if asset.alt:
        parts.append(f"alt={asset.alt}")
    return f"[{' | '.join(parts)}]"


def parse_asset_meta(text: str) -> dict[str, str] | None:
    text = text.strip()
    if not text.startswith("[") or "=" not in text:
        return None
    inner = text.lstrip("[").rstrip("]").strip()
    segments = [s.strip() for s in inner.split("|")]
    kv = parse_kv_segments(segments)
    if not kv:
        return None
    return kv
