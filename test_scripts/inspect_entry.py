"""Fetch the asin content type definition."""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from postulator.adapters.contentful import ContentfulClient


async def main():
    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment=os.environ.get("CONTENTFUL_ENVIRONMENT", "master"),
        token=os.environ["CONTENTFUL_TOKEN"],
    ) as client:
        ct = await client.get_content_type("asin")
        print(json.dumps(ct, indent=2, default=str))


asyncio.run(main())
