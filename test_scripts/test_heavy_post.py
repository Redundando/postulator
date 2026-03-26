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
    ParagraphNode, TextNode, HeadingNode, HrNode,
    AudiobookNode, AudiobookCarouselNode, AudiobookListNode,
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


MARKETPLACE = "FR"
LOCALE = "fr-FR"
SLUG = f"test-heavy-{uuid.uuid4().hex[:8]}"

# All 40 ASINs — intentional duplicates scattered throughout
ALL_ASINS = [
    "B0D53WYQ3S", "B0FZCJ7GVF", "B0D926NGSG", "B0G4WKRSNP", "B0FJLSPNJ6",
    "B0DK21WN2K", "B0G5256BL7", "B0DMDZQB89", "B0GD1GDGLD", "B0FZL68H2W",
    "B0DW8Q2ZTY", "B0FSKTMZLC", "B06Y66DT8R", "B06Y64F54M", "B0GD16KF4V",
    "B0FW58J539", "B0C4TG9JZB", "B0CJBWMWRZ", "B0FJFHXFJ7", "B08W2DSPT9",
    "B0GP7LYCQL", "B0F6YL329X", "B06Y66H419", "B00W1RJIWG", "B09C8W6QWV",
    "B0G524JR8R", "B0CT9S2N11", "B0G5249QPP", "B0FSKW9FK4", "B0CV5R3CDY",
    "B0DB5ZM9B5", "B0CRDRQKYH", "B0G6ZG7NZ3", "B0GD1FJ4H9", "B06Y628XNL",
    "B06Y67451Q", "B0GFVZVPR9", "B0G7J2C1WR", "B0D1VYPDPK", "B075K7Q8TZ",
]


async def main() -> None:
    image_path = make_featured_image()
    print(f"Generated hero image: {image_path}")

    post = Post(
        slug=SLUG,
        locale=LOCALE,
        title="Heavy Load Test — ASINs, Lists, Carousels & Duplicates",
        date=datetime.now(timezone.utc),
        introduction=(
            "This article is a stress test for the postulator pipeline. "
            "It contains single ASIN embeds, multiple asin lists, multiple carousels, "
            "and intentional duplicate ASINs across all block types."
        ),
        show_in_feed=False,
        featured_image=LocalAsset(
            local_path=image_path,
            title="Heavy Test Hero Image",
            alt="Randomly generated hero image",
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
            meta_title="Heavy Load Test | Audible FR",
            meta_description="Stress test article covering all postulator block types with heavy ASIN load.",
        ),
        body=[
            # --- Single ASINs ---
            HeadingNode(level=2, children=[TextNode(value="Coups de cœur individuels")]),
            ParagraphNode(children=[TextNode(value="Voici quelques titres sélectionnés à la main.")]),
            AudiobookNode(asin="B0D53WYQ3S", marketplace=MARKETPLACE),
            AudiobookNode(asin="B0FZCJ7GVF", marketplace=MARKETPLACE),
            AudiobookNode(asin="B0DK21WN2K", marketplace=MARKETPLACE),
            # duplicate of first — should reuse source_id, not re-create
            AudiobookNode(asin="B0D53WYQ3S", marketplace=MARKETPLACE),

            HrNode(),

            # --- Carousel 1: 8 ASINs ---
            HeadingNode(level=2, children=[TextNode(value="Sélection du mois")]),
            ParagraphNode(children=[TextNode(value="Notre carousel principal avec 8 titres.")]),
            AudiobookCarouselNode(
                asins=[
                    "B0D926NGSG", "B0G4WKRSNP", "B0FJLSPNJ6", "B0G5256BL7",
                    "B0DMDZQB89", "B0GD1GDGLD", "B0FZL68H2W", "B0DW8Q2ZTY",
                ],
                title="Sélection du mois",
                items_per_slide=4,
            ),

            HrNode(),

            # --- ASIN List 1: 6 ASINs, includes duplicates from carousel 1 ---
            HeadingNode(level=2, children=[TextNode(value="Liste annotée — Thrillers")]),
            ParagraphNode(children=[TextNode(value="Une liste détaillée avec descriptions.")]),
            AudiobookListNode(
                asins=[
                    "B0FSKTMZLC", "B06Y66DT8R", "B06Y64F54M", "B0GD16KF4V",
                    # duplicates from carousel 1
                    "B0G4WKRSNP", "B0DMDZQB89",
                ],
                title="Thrillers incontournables",
                player_type="Cover",
                asins_per_row=3,
                descriptions="Full",
            ),

            HrNode(),

            # --- Carousel 2: 7 ASINs, heavy overlap with list 1 and carousel 1 ---
            HeadingNode(level=2, children=[TextNode(value="Nouveautés de la semaine")]),
            AudiobookCarouselNode(
                asins=[
                    "B0FW58J539", "B0C4TG9JZB", "B0CJBWMWRZ", "B0FJFHXFJ7",
                    # duplicates from earlier blocks
                    "B06Y66DT8R", "B0G4WKRSNP", "B0D53WYQ3S",
                ],
                title="Nouveautés de la semaine",
                items_per_slide=3,
                subtitle="Découvrez les sorties récentes",
            ),

            HrNode(),

            # --- ASIN List 2: 8 ASINs ---
            HeadingNode(level=2, children=[TextNode(value="Liste — Romans historiques")]),
            AudiobookListNode(
                asins=[
                    "B08W2DSPT9", "B0GP7LYCQL", "B0F6YL329X", "B06Y66H419",
                    "B00W1RJIWG", "B09C8W6QWV", "B0G524JR8R", "B0CT9S2N11",
                ],
                title="Romans historiques",
                player_type="Cover",
                asins_per_row=1,
                descriptions="Full",
            ),

            HrNode(),

            # --- Carousel 3: 10 ASINs, mix of new and duplicates ---
            HeadingNode(level=2, children=[TextNode(value="Grand carousel — Toute la sélection")]),
            ParagraphNode(children=[TextNode(value="Notre plus grand carousel avec 10 titres.")]),
            AudiobookCarouselNode(
                asins=[
                    "B0G5249QPP", "B0FSKW9FK4", "B0CV5R3CDY", "B0DB5ZM9B5",
                    "B0CRDRQKYH", "B0G6ZG7NZ3", "B0GD1FJ4H9", "B06Y628XNL",
                    # duplicates
                    "B0FZCJ7GVF", "B0DK21WN2K",
                ],
                title="Toute la sélection Audible FR",
                items_per_slide=4,
                cta_text="Voir tout",
                cta_url="https://www.audible.fr",
            ),

            HrNode(),

            # --- ASIN List 3: 5 ASINs, all duplicates from previous blocks ---
            HeadingNode(level=2, children=[TextNode(value="Liste — Nos classiques")]),
            ParagraphNode(children=[TextNode(value="Des titres déjà vus, pour tester la déduplication.")]),
            AudiobookListNode(
                asins=[
                    "B06Y67451Q", "B0GFVZVPR9", "B0G7J2C1WR", "B0D1VYPDPK",
                    "B075K7Q8TZ",
                ],
                title="Classiques revisités",
                player_type="Cover",
                asins_per_row=1,
                descriptions="Full",
            ),

            HrNode(),

            # --- Two more single ASINs, both duplicates ---
            HeadingNode(level=2, children=[TextNode(value="Encore deux titres")]),
            ParagraphNode(children=[TextNode(value="Ces deux titres apparaissent déjà plus haut.")]),
            AudiobookNode(asin="B0GP7LYCQL", marketplace=MARKETPLACE),
            AudiobookNode(asin="B0CV5R3CDY", marketplace=MARKETPLACE),

            HrNode(),

            ParagraphNode(children=[
                TextNode(value="Merci d'avoir lu cet article de test. À bientôt sur Audible FR !"),
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
        print(f"   Body nodes              : {len(created.body)}")


if __name__ == "__main__":
    asyncio.run(main())
