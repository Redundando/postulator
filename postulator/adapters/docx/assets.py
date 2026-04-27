"""DOCX asset helpers — image reading, downloading, extraction."""

from __future__ import annotations
import io
import logging
import os
import tempfile
from pathlib import Path

import httpx
from docx.oxml.ns import qn

from ...models import AssetRef, LocalAsset

logger = logging.getLogger(__name__)


def convert_webp_to_png(data: bytes) -> bytes:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        logger.debug("Pillow not installed, skipping WebP conversion")
    except Exception as e:
        logger.debug("WebP conversion failed: %s", e)
    return data


def get_image_bytes(image: AssetRef | LocalAsset | None) -> bytes | None:
    if image is None:
        return None
    if isinstance(image, LocalAsset):
        try:
            return Path(image.local_path).read_bytes()
        except Exception as e:
            logger.warning("Failed to read local image %s: %s", image.local_path, e)
            return None
    if isinstance(image, AssetRef) and image.url:
        try:
            resp = httpx.get(image.url, follow_redirects=True, timeout=30)
            resp.raise_for_status()
            data = resp.content
            content_type = resp.headers.get("content-type", "")
            if "webp" in content_type or (image.url and image.url.endswith(".webp")):
                data = convert_webp_to_png(data)
            return data
        except Exception as e:
            logger.warning("Failed to download image %s: %s", image.url, e)
            return None
    return None


def extract_image_from_paragraph(p, image_dir: str | None = None, image_index: int = 0) -> tuple[LocalAsset | None, int]:
    """Extract the first inline image from a DOCX paragraph, save to disk.

    Returns (LocalAsset or None, updated image_index).
    """
    for run in p.runs:
        for shape in run._r.findall(qn("w:drawing")):
            blip = shape.find(".//" + qn("a:blip"))
            if blip is not None:
                asset, new_index = _extract_blip(blip, p, image_dir, image_index)
                return asset, new_index
    return None, image_index


def _extract_blip(blip, p, image_dir: str | None, image_index: int) -> tuple[LocalAsset | None, int]:
    r_embed = blip.get(qn("r:embed"))
    if not r_embed:
        return None, image_index
    try:
        rel = p.part.rels[r_embed]
        image_part = rel.target_part
        image_bytes = image_part.blob
        ext = os.path.splitext(image_part.partname)[-1] or ".png"
        img_dir = image_dir or tempfile.mkdtemp(prefix="postulator_")
        os.makedirs(img_dir, exist_ok=True)
        image_index += 1
        filename = f"image_{image_index}{ext}"
        filepath = os.path.join(img_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return LocalAsset(
            local_path=filepath,
            title=filename,
            content_type=image_part.content_type,
        ), image_index
    except Exception as e:
        logger.warning("Failed to extract image: %s", e)
        return None, image_index
