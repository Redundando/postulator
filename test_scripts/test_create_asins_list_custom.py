import asyncio
import os
import sys
import uuid

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from postulator.adapters.contentful import ContentfulClient
from postulator.nodes import AudiobookListNode, AudiobookListItem

MARKETPLACE = "FR"

ASIN_ITEMS = [
    AudiobookListItem(
        key=str(uuid.uuid4()),
        asin="B0D53WYQ3S",
        marketplace=MARKETPLACE,
        summary=(
            "<p><strong>Un thriller haletant au cœur de la nuit parisienne.</strong></p>"
            "<p>Rarement un roman policier m'a tenu en haleine avec une telle constance. "
            "L'auteur tisse une atmosphère dense, presque étouffante, où chaque silence "
            "cache une menace. La narration audio amplifie cette tension jusqu'à la dernière seconde — "
            "impossible de décrocher avant le dénouement.</p>"
        ),
    ),
    AudiobookListItem(
        key=str(uuid.uuid4()),
        asin="B0FZCJ7GVF",
        marketplace=MARKETPLACE,
        summary=(
            "<p><strong>Une fresque familiale bouleversante sur trois générations.</strong></p>"
            "<p>Ce livre m'a pris complètement par surprise. Ce qui commence comme une simple "
            "histoire de transmission se révèle être une méditation profonde sur la mémoire, "
            "la culpabilité et le pardon. La lectrice prête à chaque personnage une voix si juste "
            "qu'on oublie qu'il s'agit d'une fiction.</p>"
        ),
    ),
    AudiobookListItem(
        key=str(uuid.uuid4()),
        asin="B0D926NGSG",
        marketplace=MARKETPLACE,
        summary=(
            "<p><strong>Science-fiction ambitieuse, humanisme discret.</strong></p>"
            "<p>Dans un genre souvent dominé par les effets spectaculaires, ce titre choisit "
            "la voie de l'intime. On suit des personnages fracturés dans un monde qui l'est tout "
            "autant, et c'est précisément cette fragilité partagée qui rend l'ensemble si "
            "inoubliable. Une belle découverte.</p>"
        ),
    ),
]

NODE = AudiobookListNode(
    title="Sélection de la rédaction — Test",
    asins=[item.asin for item in ASIN_ITEMS],
    asin_items=ASIN_ITEMS,
    player_type="Cover",
    asins_per_row=1,
    descriptions="Custom",
    options=[],
)


async def main() -> None:
    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment=os.getenv("CONTENTFUL_ENVIRONMENT", "master"),
        token=os.environ["CONTENTFUL_TOKEN"],
        on_progress=lambda e: print(f"  [{e['event']}] {e}"),
    ) as client:
        entry_id = await client.write_asin_list(NODE, [])
        from postulator.adapters.contentful._reader import _parse_embed
        raw = await client.get_entry(entry_id)

    from postulator.nodes import AudiobookListNode as ALN
    node = _parse_embed(raw, {}, {}, "en-US")
    assert isinstance(node, ALN)
    print(f"\n✅ asinsList entry ID: {entry_id}")
    print(f"   asin_items read back: {len(node.asin_items)}")
    for item in node.asin_items:
        print(f"   - {item.asin}: {(item.summary or '')[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
