"""Contentful asset upload, processing, and publishing."""

from __future__ import annotations
import asyncio
import logging
import mimetypes
import os
from typing import TYPE_CHECKING

from ...models import AssetRef, LocalAsset
from ...events import UploadingAssetEvent, AssetUploadFailedEvent, AssetProcessingTimeoutEvent

if TYPE_CHECKING:
    from .client import ContentfulClient

logger = logging.getLogger(__name__)


async def upload_local_asset(client: "ContentfulClient", asset: LocalAsset) -> AssetRef:
    locale = "en-US"
    file_name = asset.file_name or os.path.basename(asset.local_path)
    content_type = asset.content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    client._emit(UploadingAssetEvent(title=asset.title, file_name=file_name))
    if not os.path.exists(asset.local_path):
        msg = f"Local asset file not found: {asset.local_path!r}"
        logger.error(msg)
        client._emit(AssetUploadFailedEvent(title=asset.title, message=msg))
        raise FileNotFoundError(msg)
    try:
        with open(asset.local_path, "rb") as fh:
            data = fh.read()

        upload_id = await client.upload_file(data, content_type)
        raw = await client.create_asset({
            "title": {locale: asset.title},
            "description": {locale: asset.alt or ""},
            "file": {locale: {
                "fileName": file_name,
                "contentType": content_type,
                "uploadFrom": {"sys": {"type": "Link", "linkType": "Upload", "id": upload_id}},
            }},
        })
        asset_id = raw["sys"]["id"]
        await client.process_asset(asset_id, locale)

        for attempt in range(client._asset_poll_attempts):
            await asyncio.sleep(client._asset_poll_interval)
            raw = await client.get_asset(asset_id)
            if raw.get("fields", {}).get("file", {}).get(locale, {}).get("url"):
                break
        else:
            logger.warning(
                "Asset %s processing did not complete after %d attempts (%.1fs each)",
                asset_id, client._asset_poll_attempts, client._asset_poll_interval,
            )
            client._emit(AssetProcessingTimeoutEvent(asset_id=asset_id))

        await client.publish_asset(asset_id, raw["sys"]["version"])
        raw = await client.get_asset(asset_id)

        file = raw.get("fields", {}).get("file", {}).get(locale, {})
        details = file.get("details", {})
        image = details.get("image", {})
        raw_url = file.get("url", "")
        return AssetRef(
            source_id=asset_id,
            url=f"https:{raw_url}" if raw_url.startswith("//") else raw_url,
            title=asset.title,
            alt=asset.alt,
            file_name=file_name,
            content_type=content_type,
            width=image.get("width"),
            height=image.get("height"),
            size=details.get("size"),
        )
    except Exception as e:
        logger.exception("Failed to upload asset %r", asset.title)
        client._emit(AssetUploadFailedEvent(title=asset.title, message=str(e)))
        raise
