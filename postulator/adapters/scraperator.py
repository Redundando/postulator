from __future__ import annotations
import logging
from datetime import datetime
from scraperator import AudibleProduct, ProductInput
from scraperator.audible_product import AudibleProductConfig

from ..nodes import AudiobookNode, AudiobookAuthor, AudiobookNarrator
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


async def enrich_audiobook_nodes(nodes: list[AudiobookNode], on_progress=None) -> None:
    """Batch-scrape Audible and populate missing fields on each node in-place.

    Raises if any product is not found or all scrape attempts failed.
    Only fills fields that are None/empty — never overwrites manually-set data.
    """
    if AudibleProduct.config is None:
        configure()
    inputs = [ProductInput(tld=marketplace_to_tld(n.marketplace), asin=n.asin) for n in nodes]
    products = await AudibleProduct.scrape_many(inputs, on_progress=on_progress)

    for node, product in zip(nodes, products):
        if product.not_found:
            logger.error("Audible product not found: %s (%s)", node.asin, node.marketplace)
            raise ValueError(f"Audible product not found: {node.asin} ({node.marketplace})")
        if product.all_scrapes_unsuccessful:
            logger.error("All scrape attempts failed for: %s (%s)", node.asin, node.marketplace)
            raise RuntimeError(f"All scrape attempts failed for: {node.asin} ({node.marketplace})")

        if not node.title:
            node.title = product.title
        if not node.pdp:
            node.pdp = product.url
        if not node.cover_url:
            node.cover_url = product.image_url
        if not node.summary:
            node.summary = product.publisher_summary
        if not node.release_date and product.release_date:
            for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
                try:
                    node.release_date = datetime.strptime(product.release_date, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        if not node.authors and product.authors:
            node.authors = [AudiobookAuthor(name=a["name"], pdp=a["url"]) for a in product.authors]
        if not node.narrators and product.narrators:
            node.narrators = [AudiobookNarrator(name=n["name"]) for n in product.narrators]
