"""Convert the mock DE article to DOCX using postulator's markdown parser + DOCX adapter."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from postulator import (
    Post, ParagraphNode, TextNode, HeadingNode, HrNode,
    BlockquoteNode, AudiobookNode, AudiobookCarouselNode,
    AuthorRef, TagRef, SeoMeta, LocalAsset,
)
from postulator.table import table
from postulator.adapters.docx import DocxAdapter

OUTPUT = os.path.join("test_output", "mock_article_de.docx")

post = Post(
    slug="hoerbuecher-zum-traeumen",
    locale="de-DE",
    title="Hörbücher zum Träumen: Die schönsten Geschichten für gemütliche Abende",
    date=datetime(2025, 7, 1, tzinfo=timezone.utc),
    introduction=(
        "Ob Märchen, Liebesgeschichten oder phantastische Abenteuer – "
        "diese Hörbücher laden zum Träumen ein. Wir haben die schönsten "
        "Geschichten für gemütliche Abende zusammengestellt."
    ),
    authors=[AuthorRef(slug="redaktion-audible", locale="de-DE", name="Redaktion Audible")],
    tags=[
        TagRef(slug="unterhaltung", locale="de-DE", name="Unterhaltung"),
        TagRef(slug="empfehlungen", locale="de-DE", name="Empfehlungen"),
    ],
    seo=SeoMeta(
        meta_title="Die schönsten Hörbücher für gemütliche Abende",
        meta_description=(
            "Entdecke unsere Auswahl der schönsten Hörbücher zum Träumen – "
            "von Märchen über Liebesgeschichten bis hin zu phantastischen Abenteuern."
        ),
    ),
    featured_image=LocalAsset(
        local_path=os.path.join("test_output", "images", "image_1.jpg"),
        title="Hörbücher zum Träumen",
        alt="Eine gemütliche Leseecke mit Kopfhörern",
    ),
    body=[
        HeadingNode(level=2, children=[TextNode(value="Phantastische Abenteuer für die ganze Familie")]),
        ParagraphNode(children=[TextNode(value=(
            "Manchmal braucht man einfach eine Geschichte, die einen in eine andere Welt entführt. "
            "Rufus T. Feuerflieg nimmt uns mit auf eine Reise in das tiefe Tiefgeschoss – "
            "ein Abenteuer, das Kinder und Erwachsene gleichermaßen begeistert."
        ))]),
        AudiobookNode(asin="B0BYJR6W77", marketplace="DE"),
        ParagraphNode(children=[TextNode(value=(
            "Die Geschichte verbindet Humor mit Spannung und ist perfekt für einen gemeinsamen "
            "Hörabend mit der ganzen Familie. Die phantastischen Fälle sind mittlerweile eine "
            "beliebte Reihe, die immer wieder überrascht."
        ))]),

        HeadingNode(level=2, children=[TextNode(value="Einschlafen leicht gemacht")]),
        ParagraphNode(children=[TextNode(value=(
            "Wer kennt es nicht: Man liegt im Bett und die Gedanken kreisen. "
            "Diese beiden Hörbücher schaffen Abhilfe und entführen dich sanft in den Schlaf."
        ))]),
        AudiobookNode(asin="B092MNY82S", marketplace="DE"),
        AudiobookNode(asin="B092MNP9XR", marketplace="DE"),
        ParagraphNode(children=[TextNode(value=(
            "Beide Titel kombinieren beruhigende Erzählungen mit atmosphärischen Klängen. "
            "Ob du lieber durch die fränkische Landschaft oder durch die Berliner Nacht reist "
            "– Entspannung ist garantiert."
        ))]),

        HeadingNode(level=2, children=[TextNode(value="Klassiker neu entdeckt")]),
        ParagraphNode(children=[TextNode(value=(
            "Manche Geschichten verlieren nie ihren Zauber. Dornröschen gehört zu den "
            "bekanntesten Märchen der Brüder Grimm und begeistert seit Generationen."
        ))]),
        AudiobookNode(asin="B00B4FPR76", marketplace="DE"),
        BlockquoteNode(children=[ParagraphNode(children=[TextNode(value=(
            "Die alten Märchen sind nicht nur für Kinder. Sie erzählen von universellen "
            "Wahrheiten, die uns ein Leben lang begleiten."
        ))])]),

        HeadingNode(level=2, children=[TextNode(value="Unsere Empfehlungen im Überblick")]),
        table("""
| Kategorie | Titel | Für wen? |
|---|---|---|
| **Abenteuer** | Das tiefe Tiefgeschoss | Familien |
| **Einschlafen** | Schlaf gut, Franken | Erwachsene |
| **Einschlafen** | Schlaf gut, Berlin | Erwachsene |
| **Märchen** | Dornröschen | Alle |
| **Liebe** | Auf diese Art zusammen | Erwachsene |
| **Komödie** | Hallojulia | Junge Erwachsene |
"""),

        HeadingNode(level=2, children=[TextNode(value="Liebe und Zusammenhalt")]),
        ParagraphNode(children=[TextNode(value=(
            "Manchmal sind es die leisen Töne, die am meisten berühren. "
            "Diese Geschichte erzählt von zwei Menschen, die auf unerwartete Weise zueinander finden."
        ))]),
        AudiobookNode(asin="3732404471", marketplace="DE"),

        HrNode(),

        HeadingNode(level=2, children=[TextNode(value="Alle Empfehlungen auf einen Blick")]),
        ParagraphNode(children=[TextNode(value=(
            "Entdecke alle unsere Hörbuch-Empfehlungen für gemütliche Abende in diesem Carousel:"
        ))]),
        AudiobookCarouselNode(
            asins=["B0BYJR6W77", "B092MNY82S", "B092MNP9XR", "B00B4FPR76", "3732404471", "B07KT13WND", "B086M6PVSY"],
            title="Hörbücher zum Träumen",
            subtitle="Unsere Empfehlungen für gemütliche Abende",
        ),
    ],
)

adapter = DocxAdapter()
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
adapter.write(post, OUTPUT)
print(f"Wrote: {OUTPUT}")

# Read back and verify
post2 = adapter.read(OUTPUT)
print(f"Read back: {post2.title!r}")
print(f"  locale: {post2.locale}")
print(f"  slug: {post2.slug}")
print(f"  intro: {post2.introduction[:80]!r}...")
print(f"  authors: {[a.name for a in post2.authors]}")
print(f"  tags: {[t.name for t in post2.tags]}")
print(f"  seo: {post2.seo.meta_title!r}" if post2.seo else "  seo: None")
print(f"  featured_image: {type(post2.featured_image).__name__}")
print(f"  body: {len(post2.body)} nodes")
types = [n.type for n in post2.body]
print(f"  types: {types}")

assert post2.title == post.title
assert post2.locale == "de-DE"
assert post2.introduction
assert len(post2.authors) == 1
assert len(post2.tags) == 2
assert post2.seo
assert post2.featured_image
assert "heading" in types
assert "paragraph" in types
assert "audiobook" in types
assert "audiobook-carousel" in types
assert "table" in types
assert "blockquote" in types
assert "hr" in types

print("\nAll assertions passed!")
