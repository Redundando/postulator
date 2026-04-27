"""Audible product enricher — pure data in, data out.

No dependency on postulator models. Accepts ASINs and marketplaces,
returns plain dicts of metadata.
"""

from __future__ import annotations
import logging
from datetime import datetime

from scraperator import AudibleProduct, ProductInput
from scraperator.audible_product import AudibleProductConfig

from ..marketplace import marketplace_to_tld

logger = logging.getLogger(__name__)


def configure(
    cache: str = "local",
    cache_directory: str = "cache",
    cache_table: str | None = None,
    scrape_cache: str = "none",
    scrape_cache_table: str | None = None,
    aws_region: str | None = None,
) -> None:
    AudibleProduct.config = AudibleProductConfig(
        cache=cache,
        cache_directory=cache_directory,
        cache_table=cache_table,
        scrape_cache=scrape_cache,
        scrape_cache_table=scrape_cache_table,
        aws_region=aws_region,
    )


def _parse_release_date(raw: str | None) -> str | None:
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _product_to_dict(product) -> dict:
    """Convert a scraperator product to a plain metadata dict."""
    return {
        "title": product.title,
        "pdp": product.url,
        "cover_url": product.image_url,
        "summary": product.publisher_summary,
        "release_date": _parse_release_date(product.release_date),
        "authors": [{"name": a["name"], "pdp": a.get("url")} for a in (product.authors or [])],
        "narrators": [{"name": n["name"]} for n in (product.narrators or [])],
    }


async def enrich(asin: str, marketplace: str, on_progress=None) -> dict:
    """Scrape a single Audible product and return a metadata dict.

    Returns dict with keys: title, pdp, cover_url, summary, release_date,
    authors (list of {name, pdp}), narrators (list of {name}).

    Raises ValueError if product not found, RuntimeError if all scrapes failed.
    """
    if AudibleProduct.config is None:
        configure()
    tld = marketplace_to_tld(marketplace)
    products = await AudibleProduct.scrape_many(
        [ProductInput(tld=tld, asin=asin)], on_progress=on_progress,
    )
    product = products[0]
    if product.not_found:
        raise ValueError(f"Audible product not found: {asin} ({marketplace})")
    if product.all_scrapes_unsuccessful:
        raise RuntimeError(f"All scrape attempts failed for: {asin} ({marketplace})")
    return _product_to_dict(product)


async def enrich_batch(items: list[dict], on_progress=None) -> list[dict]:
    """Batch-scrape Audible products and return metadata dicts.

    Each item must have 'asin' and 'marketplace' keys.
    Returns list of metadata dicts in same order.

    Raises ValueError if any product not found, RuntimeError if all scrapes failed.
    """
    if not items:
        return []
    if AudibleProduct.config is None:
        configure()
    inputs = [ProductInput(tld=marketplace_to_tld(i["marketplace"]), asin=i["asin"]) for i in items]
    products = await AudibleProduct.scrape_many(inputs, on_progress=on_progress)
    results = []
    for item, product in zip(items, products):
        if product.not_found:
            raise ValueError(f"Audible product not found: {item['asin']} ({item['marketplace']})")
        if product.all_scrapes_unsuccessful:
            raise RuntimeError(f"All scrape attempts failed for: {item['asin']} ({item['marketplace']})")
        results.append(_product_to_dict(product))
    return results
