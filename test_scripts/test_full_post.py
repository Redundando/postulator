import asyncio
import os
import sys
import uuid
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from postulator import (
    Post, AuthorRef, TagRef, SeoMeta,
    ParagraphNode, TextNode, HeadingNode,
    AudiobookNode, AudiobookCarouselNode,
    LocalAsset,
)
from postulator.adapters.contentful import ContentfulClient


def make_featured_image() -> str:
    from PIL import Image
    import random
    img = Image.new("RGB", (1200, 630), color=(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    ))
    path = os.path.join(tempfile.gettempdir(), f"test_hero_{uuid.uuid4().hex}.jpg")
    img.save(path, "JPEG")
    return path


ASINS = [
    "B0D53WYQ3S",
    "B0FZCJ7GVF",
    "B0D926NGSG",
    "B06Y66DT8R",
    "B0FJLSPNJ6",
    "B0G4WKRSNP",
    "B0G5256BL7",
]
MARKETPLACE = "FR"
LOCALE = "fr-FR"
SLUG = f"test-article-{uuid.uuid4().hex[:8]}"


async def main() -> None:
    image_path = make_featured_image()
    print(f"Generated hero image: {image_path}")

    post = Post(
        slug=SLUG,
        locale=LOCALE,
        title="Test Article — Everything Included",
        date=datetime.now(timezone.utc),
        introduction=(
            "This is a test article generated automatically to validate the full "
            "postulator pipeline: content, ASINs, carousel, author, tags, SEO, and featured image."
        ),
        show_in_feed=False,
        featured_image=LocalAsset(
            local_path=image_path,
            title="Test Hero Image",
            alt="A randomly generated hero image for testing",
            content_type="image/jpeg",
        ),
        authors=[
            AuthorRef(slug="fr-author", locale=LOCALE, name="FR Author", source_id="52621970-fr-author"),
        ],
        tags=[
            TagRef(slug="fr-tag", locale=LOCALE, name="FR Tag", source_id="2093616522-fr-tag"),
            TagRef(slug="fr-tag-2", locale=LOCALE, name="FR Tag 2", source_id="4w2qhuccGUWd6Jl46FAzCN"),
        ],
        seo=SeoMeta(
            label=f"SEO — {SLUG}",
            meta_title="Test Article | Audible FR",
            meta_description=(
                "A comprehensive test article covering all postulator features: "
                "rich text, ASIN embeds, carousels, SEO, and more."
            ),
        ),
        body=[
            HeadingNode(level=2, children=[TextNode(value="Introduction")]),
            ParagraphNode(children=[
                TextNode(value="Welcome to this test article. Below you will find a mix of content types."),
            ]),
            ParagraphNode(children=[
                TextNode(value="This paragraph contains "),
                TextNode(value="bold text", marks=["bold"]),
                TextNode(value=" and "),
                TextNode(value="italic text", marks=["italic"]),
                TextNode(value="."),
            ]),
            HeadingNode(level=2, children=[TextNode(value="Featured Audiobook")]),
            ParagraphNode(children=[
                TextNode(value="Here is a single audiobook embed:"),
            ]),
            AudiobookNode(asin=ASINS[0], marketplace=MARKETPLACE),
            HeadingNode(level=2, children=[TextNode(value="More Picks")]),
            ParagraphNode(children=[
                TextNode(value="And here is a second individual audiobook:"),
            ]),
            AudiobookNode(asin=ASINS[1], marketplace=MARKETPLACE),
            HeadingNode(level=2, children=[TextNode(value="Our Full Selection")]),
            ParagraphNode(children=[
                TextNode(value="Browse the full carousel of recommended listens below."),
            ]),
            AudiobookCarouselNode(
                asins=ASINS,
                title="Top Picks on Audible FR",
                items_per_slide=3,
            ),
            ParagraphNode(children=[
                TextNode(value="Thanks for reading. Check back soon for more recommendations."),
            ]),
        ],
    )

    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment=os.getenv("CONTENTFUL_ENVIRONMENT", "master"),
        token=os.environ["CONTENTFUL_TOKEN"],
        on_progress=lambda e: print(f"  [{e['event']}] {e}"),
    ) as client:
        print(f"\nCreating post: {SLUG}")
        created = await client.create_post(post, publish=True)
        print(f"\n✅ Published post entry ID : {created.source_id}")
        print(f"   Slug                    : {created.slug}")
        print(f"   SEO entry ID            : {created.seo.source_id if created.seo else 'n/a'}")
        print(f"   Authors                 : {[a.name for a in created.authors]}")
        print(f"   Tags                    : {[t.name for t in created.tags]}")
        print(f"   Body nodes              : {len(created.body)}")


if __name__ == "__main__":
    asyncio.run(main())
