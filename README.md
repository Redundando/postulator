# Postulator

## Overview

Postulator is a Python library for programmatically creating, reading, and publishing blog posts. It provides Pydantic models for posts, rich-text body nodes, audiobook embeds, SEO settings, and authors. Adapters handle reading from and writing to specific backends (Contentful, DOCX). Enrichers fill in missing data (Audible product metadata).

The primary consumer is other LLMs and automation scripts that need to compose and publish Audible blog content.

### Architecture

```
post = docx_adapter.read("article.docx")          # DOCX → generic model
await contentful_adapter.write(post, publish=True)  # generic model → Contentful
```

- **Generic model** is the interchange format. All adapters read into it and write from it.
- **Adapters** own their orchestration. `ContentfulAdapter` handles ASIN resolution, asset uploads, entry creation. `DocxAdapter` handles placeholder parsing, post-processing, DOCX generation.
- **Enrichers** are pure data in → data out. They don't know about adapters or models.
- **`ContentfulClient`** is a pure HTTP layer — no business logic.
- **Node types are extensible** via a registry. Consumers can add custom node types without modifying core.

## Installation

```bash
pip install postulator
```

Dependencies (installed automatically): `pydantic`, `httpx`, `python-dotenv`, `scraperator`, `markdown-it-py`, `python-docx`.

## Configuration

Set these environment variables (or use a `.env` file with `python-dotenv`):

| Variable | Required | Description |
|---|---|---|
| `CONTENTFUL_TOKEN` | Yes | Contentful CMA personal access token |
| `CONTENTFUL_SPACE_ID` | Yes | Contentful space ID |
| `CONTENTFUL_ENVIRONMENT` | No | Contentful environment (defaults to `"master"`) |

## Quick Start

### Contentful: Create a post

```python
import asyncio
from datetime import datetime, timezone
from postulator import Post, ParagraphNode, TextNode, HeadingNode, AudiobookNode
from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter

post = Post(
    slug="my-first-post",
    locale="fr-FR",
    title="My First Post",
    date=datetime.now(timezone.utc),
    body=[
        HeadingNode(level=2, children=[TextNode(value="Hello")]),
        ParagraphNode(children=[TextNode(value="This is a paragraph.")]),
        AudiobookNode(asin="B0D53WYQ3S", marketplace="FR"),
    ],
)

async def main():
    async with ContentfulClient(
        space_id="<space_id>",
        environment="master",
        token="<token>",
    ) as client:
        adapter = ContentfulAdapter(client)
        created = await adapter.write(post, publish=True)
        print(created.source_id)

asyncio.run(main())
```

### DOCX: Read a Word document and upload to Contentful

```python
from postulator.adapters.docx import DocxAdapter
from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter

# Read DOCX into a Post
post = DocxAdapter().read("article.docx")

# Upload to Contentful
async with ContentfulClient(space_id="<space_id>", environment="master", token="<token>") as client:
    adapter = ContentfulAdapter(client)
    created = await adapter.write(post, publish=False)  # draft
```

### Write pipeline

The `ContentfulAdapter.write()` pipeline automatically:
1. Resolves author and tag names to Contentful entry IDs
2. Uploads any `LocalAsset` images (featured image, SEO OG image, body embeds)
3. Creates/updates the `seoSettings` entry if `post.seo` is set
4. Enriches `AudiobookNode`s by scraping Audible (title, cover, PDP URL, authors, etc.)
5. Creates/reuses `asin` entries in Contentful
6. Creates `asinsList` / `asinsCarousel` entries for list/carousel nodes
7. Creates the `post` entry with rich-text body referencing all embedded entries
8. Optionally publishes everything

## ContentfulAdapter

High-level orchestrator for reading and writing posts, authors, and tags to Contentful. Wraps a `ContentfulClient`.

```python
from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter

async with ContentfulClient(
    space_id="<space_id>",
    environment="master",
    token="<token>",
    on_progress=lambda e: print(type(e).__name__),
) as client:
    adapter = ContentfulAdapter(client)
    ...
```

### Posts

- `write(post, publish=False) -> Post` — full create pipeline: resolve authors/tags, upload assets, enrich ASINs, create all entries, create post. Returns the round-tripped `Post`.
- `update(post, publish=True) -> Post` — same pipeline but updates an existing post (`post.source_id` required).
- `read(entry_id, locale="en-US") -> Post` — reads a post and all its linked entries/assets into a `Post` model.

### Authors

- `create_author(author, publish=False) -> Author` — creates a new author entry.
- `update_author(author, publish=True) -> Author` — updates an existing author (`author.source_id` required).
- `read_author(entry_id, locale="en-US") -> Author` — reads an author entry.
- `list_authors(country_code, locale="en-US") -> list[Author]` — lists all authors for a country code.

### Tags

- `list_tags(country_code, locale="en-US") -> list[TagRef]` — lists all tags for a country code.

### Lookup

- `find_entry_by_slug(slug, locale) -> dict | None` — checks whether a `post` or `category` entry with the given slug and country code already exists. Returns the raw Contentful entry dict if found, `None` otherwise.

```python
existing = await adapter.find_entry_by_slug(slug="top-books-june-2026", locale="en-GB")
if existing:
    print(f"Already exists: {existing['sys']['id']}")
```

### Assets

- `upload_asset(asset: LocalAsset) -> AssetRef` — uploads, processes, publishes a local file. Returns the resulting `AssetRef`.

## ContentfulClient

Pure async HTTP client wrapping the Contentful CMA. No business logic — all orchestration lives in `ContentfulAdapter`. Must be used as an async context manager.

### Constructor Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `space_id` | `str` | — | Contentful space ID |
| `environment` | `str` | — | Environment name |
| `token` | `str` | — | CMA access token |
| `batch_size` | `int` | `200` | Max entries per batch request |
| `asset_poll_attempts` | `int` | `10` | Polls before asset processing timeout |
| `asset_poll_interval` | `float` | `1.0` | Seconds between asset processing polls |
| `on_progress` | `Callable[[BaseEvent], None] \| None` | `None` | Progress callback (receives typed `BaseEvent` instances) |

### Low-Level Methods

- `get_entry(entry_id) -> dict`
- `get_entries(entry_ids) -> dict[str, dict]` — batch fetch, auto-paginated
- `create_entry(content_type, fields) -> dict`
- `create_entry_with_id(entry_id, content_type, fields) -> dict`
- `update_entry(entry_id, version, fields) -> dict`
- `publish_entry(entry_id, version) -> dict`
- `delete_entry(entry_id, version) -> None`
- `find_entries(content_type, filters, limit=1) -> list[dict]` — auto-paginated
- `get_asset(asset_id) -> dict`
- `get_assets(asset_ids) -> dict[str, dict]` — batch fetch
- `upload_file(data, content_type) -> str` — returns upload ID
- `create_asset(fields) -> dict`
- `process_asset(asset_id, locale) -> None`
- `publish_asset(asset_id, version) -> dict`
- `get_content_type(content_type_id) -> dict`

### Retry Behaviour

All HTTP requests retry up to 3 times on status codes `429`, `500`, `502`, `503`, `504` with exponential backoff (`2^attempt` seconds). Non-retryable errors raise `httpx.HTTPStatusError` immediately.

### Progress Events

The `on_progress` callback receives typed `BaseEvent` subclass instances from `postulator.events`. Use `isinstance` checks or pattern matching to handle specific events.

```python
from postulator.events import BaseEvent, CreatingPostEvent, EnrichingAsinsEvent

def on_progress(event: BaseEvent):
    if isinstance(event, CreatingPostEvent):
        print(f"Creating post: {event.slug}")
    elif isinstance(event, EnrichingAsinsEvent):
        print(f"Enriching {event.count} ASINs")
```

**Contentful ASIN events:**

| Event class | When | Fields |
|---|---|---|
| `ResolvingAsinsEvent` | Before batch-resolving existing ASIN entries | `count` |
| `EnrichingAsinsEvent` | Before scraping Audible for missing ASINs | `count` |
| `WritingAsinEvent` | Before creating/reusing a single ASIN entry | `asin`, `marketplace` |
| `AsinPublishConflictEvent` | When a uniqueKey conflict is detected and resolved | `asin`, `entry_id` |
| `AsinDraftCleanupEvent` | When a stale unpublished ASIN draft is deleted | `asin`, `entry_id` |
| `AsinPublishFailedEvent` | When publishing an ASIN entry fails | `asin`, `message` |

**Contentful asset events:**

| Event class | When | Fields |
|---|---|---|
| `UploadingAssetEvent` | Before uploading a local asset | `title`, `file_name` |
| `AssetUploadFailedEvent` | When asset upload fails | `title`, `message` |
| `AssetProcessingTimeoutEvent` | When asset processing polling times out | `asset_id` |

**Contentful post/author events:**

| Event class | When | Fields |
|---|---|---|
| `CreatingPostEvent` | Before creating a new post entry | `slug`, `locale` |
| `WritingPostEvent` | Before updating a post entry | `entry_id` |
| `PostInvalidEvent` | When post validation fails | `slug`, `reason` |
| `CreatingAuthorEvent` | Before creating a new author entry | `slug` |
| `WritingAuthorEvent` | Before updating an author entry | `entry_id` |

**Contentful resolution events:**

| Event class | When | Fields |
|---|---|---|
| `AuthorResolvedEvent` | When an author name is resolved to an ID | `name`, `source_id` |
| `AuthorNotFoundEvent` | When an author name cannot be resolved | `name` |
| `TagResolvedEvent` | When a tag name is resolved to an ID | `name`, `source_id` |
| `TagNotFoundEvent` | When a tag name cannot be resolved | `name` |

**Contentful read events:**

| Event class | When | Fields |
|---|---|---|
| `FetchingEntriesEvent` | Before batch-fetching linked entries | `count` |
| `FetchingNestedEvent` | Before fetching nested linked entries | `count` |
| `ParsingEvent` | Before parsing raw Contentful data into models | — |

**Contentful embed skip events:**

| Event class | When | Fields |
|---|---|---|
| `ListSkippedEvent` | When an AudiobookListNode is skipped (0 ASINs) | `reason` |
| `CarouselSkippedEvent` | When a carousel is skipped (<4 ASINs) | `reason`, `asins` |

**HTTP events:**

| Event class | When | Fields |
|---|---|---|
| `RequestFailedEvent` | When an HTTP request fails (non-retryable or after retries) | `method`, `url`, `status_code` |

**DOCX events:**

| Event class | When | Fields |
|---|---|---|
| `ReadingMetadataEvent` | Before reading DOCX metadata | — |
| `ReadingBodyEvent` | After parsing body nodes | `paragraph_count` |
| `ParseWarningEvent` | When a parse fallback is used (e.g. title from filename) | `message` |
| `WritingMetadataEvent` | Before writing DOCX metadata | — |
| `WritingBodyEvent` | Before writing body nodes | `node_count` |
| `WritingFeaturedImageEvent` | Before embedding featured image | `url` |

## Locale & Marketplace Mapping

`Post.locale` determines the `countryCode` written to Contentful and the Audible marketplace used for ASIN scraping.

| Locale | Country Code | Audible TLD |
|---|---|---|
| `de-DE` | `DE` | `audible.de` |
| `en-GB` | `UK` | `audible.co.uk` |
| `fr-FR` | `FR` | `audible.fr` |
| `it-IT` | `IT` | `audible.it` |
| `en-CA` | `CA_EN` | `audible.ca` |
| `fr-CA` | `CA_FR` | `audible.ca` |
| `es-ES` | `ES` | `audible.es` |
| `en-US` | `US` | `audible.com` |
| `en-AU` | `AU` | `audible.com.au` |

## DocxAdapter

Reads and writes `Post` models to/from DOCX files. Uses bracket-syntax placeholders for metadata and embeds.

```python
from postulator.adapters.docx import DocxAdapter

adapter = DocxAdapter(on_progress=None, image_dir=None)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `on_progress` | `Callable[[BaseEvent], None] \| None` | `None` | Progress callback |
| `image_dir` | `str \| None` | `None` | Directory for extracted images (defaults to temp dir) |

### Methods

- `read(path) -> Post` — read a DOCX file into a `Post` model.
- `read_bytes(data, filename=None) -> Post` — read DOCX bytes into a `Post` model. `filename` is used as title fallback.
- `write(post, path)` — write a `Post` to a DOCX file.
- `write_bytes(post) -> bytes` — write a `Post` to DOCX bytes.

### Placeholder Syntax

Metadata and embeds are represented as bracket-delimited placeholders in the DOCX.

**Single-line:** `[TYPE value]` or `[TYPE: value]`

**Multi-line:**
```
[TYPE
key = value
key = "quoted value"
]
```

The `:` after the keyword is always optional. Keys are case-insensitive with dashes/underscores/spaces normalized. Blank lines inside blocks are ignored.

**Escaping:** `\[` → literal `[`, `\]` → literal `]`, `\"` → literal `"`, `\\` → literal `\`

**Placeholder types:**

| Keyword(s) | Type | Description |
|---|---|---|
| `post` | Metadata | Post title, market, slug, date, etc. |
| `author`, `authors` | Metadata | Author name list |
| `tag`, `tags` | Metadata | Tag name list |
| `seo` | Metadata | SEO settings |
| `featured image`, `hero` | Metadata | Featured image marker |
| `intro`, `introduction` | Metadata | Introduction text |
| `asin`, `audiobook` | Body embed | Single audiobook |
| `list`, `asin-list` | Body embed | Audiobook list |
| `carousel`, `asin-carousel` | Body embed | Audiobook carousel |
| `image`, `content-image` | Body embed | Content image |
| `unknown` | Body embed | Round-trip safety (raw JSON) |

### Post-Processing

After parsing, the adapter applies cross-placeholder defaults in order:

1. **Title** ← POST `title` > filename
2. **Slug** ← POST `slug` > derived from title
3. **Date** ← POST `date` > today (UTC)
4. **Intro** ← `[Intro]` block > POST `intro` key > first body paragraph (removed from body)
5. **SEO meta-title** ← post title if not set
6. **SEO meta-description** ← intro if not set
7. **SEO og-title** ← meta-title if not set
8. **SEO og-description** ← meta-description if not set
9. **SEO label** ← `"SEO Settings {meta_title}"` if not set
10. **Featured image title/alt** ← post title if not set
11. **LIST label** ← post title if not set

If no `[Post]` block is present, the adapter still assembles a Post using filename as title, today as date, and `US` as default market.

## Audible Enricher

The `postulator.enrichers.audible` module provides pure data-in/data-out functions for scraping Audible product metadata. No dependency on postulator models.

```python
from postulator.enrichers.audible import enrich, enrich_batch, configure
```

- `enrich(asin, marketplace, on_progress=None) -> dict` — scrape a single Audible product. Returns dict with keys: `title`, `pdp`, `cover_url`, `summary`, `release_date`, `authors` (list of `{name, pdp}`), `narrators` (list of `{name}`).
- `enrich_batch(items, on_progress=None) -> list[dict]` — batch-scrape. Each item must have `asin` and `marketplace` keys. Returns list of metadata dicts in same order.
- `configure(cache, cache_directory, cache_table, scrape_cache, scrape_cache_table, aws_region)` — configure scraperator caching.

```python
configure(
    cache="local",              # "local" or "dynamodb"
    cache_directory="cache",    # local cache dir
    cache_table=None,           # DynamoDB table name
    scrape_cache="none",        # raw scrape cache
)
```

The Contentful adapter calls the enricher automatically during the write pipeline for AudiobookNodes with missing metadata. You only need to call it directly for standalone enrichment.

## CLI

Postulator ships with a `postulator` command-line tool for inspecting Contentful spaces and dumping model schemas.

```bash
postulator <command> [options]
```

All commands that talk to Contentful accept `--space-id`, `--token`, and `--environment` flags. If omitted, they fall back to `CONTENTFUL_SPACE_ID`, `CONTENTFUL_TOKEN`, and `CONTENTFUL_ENVIRONMENT` environment variables.

### Commands

**`postulator entry <entry_id>`** — Dump a single Contentful entry as JSON.

```bash
postulator entry 6nY8mRqIVO42icaoSquMYS
postulator entry 6nY8mRqIVO42icaoSquMYS --space-id abc --token cma-xxx
```

**`postulator content-type <content_type_id>`** — Dump a content type definition as JSON.

```bash
postulator content-type post
```

**`postulator content-types`** — List all content types in the space as JSON.

```bash
postulator content-types
```

**`postulator schema`** — Fetch all content types and write one markdown file per type, plus an index. Useful for documenting the Contentful schema.

```bash
postulator schema                       # writes to docs/schema/
postulator schema --output my-schema/   # custom output directory
```

**`postulator models`** — Dump the JSON Schema for every postulator Pydantic model (Post, Author, all body nodes, assets, SEO, etc.). No Contentful credentials required. Designed for LLM consumers that need to understand the full type system.

```bash
postulator models
postulator models > models.json
```

---

## Appendix: Models & Types

### Post Model

`Post` — the top-level model representing a blog post.

| Field | Type | Default | Description |
|---|---|---|---|
| `source_id` | `str \| None` | `None` | Contentful entry ID. Required for `adapter.update()`, auto-set by `adapter.write()`. |
| `slug` | `str` | — | URL slug |
| `locale` | `str` | — | BCP-47 locale (e.g. `"fr-FR"`, `"en-GB"`). Controls `countryCode` and Audible marketplace — does **not** affect Contentful field locale (always `en-US`). |
| `title` | `str` | — | Post title |
| `date` | `datetime` | — | Publish date |
| `introduction` | `str \| None` | `None` | Short intro text |
| `body` | `DocumentNode` | — | List of `BlockNode` (the rich-text body) |
| `featured_image` | `AssetRef \| LocalAsset \| None` | `None` | Hero image |
| `authors` | `list[AuthorRef]` | `[]` | Author references (must have `source_id` set for write) |
| `tags` | `list[TagRef]` | `[]` | Tag references (must have `source_id` set for write) |
| `update_date` | `datetime \| None` | `None` | Last-updated date |
| `seo` | `SeoMeta \| None` | `None` | SEO settings (created/updated automatically during write) |
| `custom_recommended_title` | `str \| None` | `None` | Override title for recommended content widgets |
| `show_in_feed` | `bool` | `True` | Show in blog feed (maps to `hideFromBlogFeed` inverted) |
| `show_publish_date` | `bool` | `True` | Show publish date on page |
| `show_hero_image` | `bool` | `True` | Show hero image on page |
| `related_posts` | `list[str]` | `[]` | Contentful entry IDs of related posts |

### Author Model

`Author` — represents a blog author entry. Used with `create_author` / `write_author`.

| Field | Type | Default | Description |
|---|---|---|---|
| `source_id` | `str \| None` | `None` | Contentful entry ID. Required for `adapter.update_author()`. |
| `country_code` | `str \| None` | `None` | e.g. `"FR"`, `"UK"` |
| `slug` | `str` | — | URL slug |
| `name` | `str` | — | Display name |
| `short_name` | `str \| None` | `None` | Abbreviated name |
| `title` | `str \| None` | `None` | Job title / role |
| `bio` | `str \| None` | `None` | Biography text |
| `picture` | `AssetRef \| LocalAsset \| None` | `None` | Profile picture |
| `seo` | `SeoMeta \| None` | `None` | SEO settings for the author page |

### Authors & Tags (References)

`AuthorRef` and `TagRef` are lightweight references used on `Post`. For writes via `ContentfulAdapter`, names are automatically resolved to Contentful entry IDs — you don't need to set `source_id` manually.

```python
from postulator import AuthorRef, TagRef

post.authors = [
    AuthorRef(slug="fr-author", locale="fr-FR", name="FR Author"),
]
post.tags = [
    TagRef(slug="fr-tag", locale="fr-FR", name="FR Tag"),
]
```

If a name cannot be resolved, the reference is silently skipped (with an `AuthorNotFoundEvent` / `TagNotFoundEvent` emitted). The post is still created without that reference.

To discover existing authors/tags, use `adapter.list_authors(country_code, locale)` and `adapter.list_tags(country_code, locale)`.

### Body Nodes

`DocumentNode` is `list[BlockNode]`. Each `BlockNode` is resolved via a node registry (on the `type` field).

#### Node Registry

Node types are extensible. Built-in types are registered at import time. Consumers can register custom types:

```python
from postulator import BaseNode, register_node, get_node_class
from typing import Literal

class PodcastEmbedNode(BaseNode):
    type: Literal["podcast-embed"] = "podcast-embed"
    podcast_url: str

register_node("podcast-embed", PodcastEmbedNode)
```

Unrecognized `type` values fall back to `UnknownNode` during deserialization.

#### Standard Block Nodes

**ParagraphNode** (`type="paragraph"`)
- `children: list[InlineNode]` — list of `TextNode` and/or `HyperlinkNode`

**HeadingNode** (`type="heading"`)
- `level: int` — 1–6
- `children: list[InlineNode]`

**ListNode** (`type="list"`)
- `ordered: bool` — `False` for bullet list, `True` for numbered
- `children: list[ListItemNode]` — each `ListItemNode` contains `list[BlockNode]` (supports nested lists)

**BlockquoteNode** (`type="blockquote"`)
- `children: list[ParagraphNode]`

**HrNode** (`type="hr"`)
- No fields. Horizontal rule.

**TableNode** (`type="table"`)
- `children: list[TableRowNode]` — each row contains `list[TableCellNode]`
- `TableCellNode` has `is_header: bool` and `children: list[BlockNode]`

#### Table Helper

Building tables from node constructors is verbose. The `table()` helper parses a markdown table string into a `TableNode`, with full support for **bold**, *italic*, and [links](url):

```python
from postulator import table

node = table("""
| Name | Age |
|------|-----|
| **Alice** | 30 |
| [Bob](https://example.com) | *25* |
""")
```

The separator row (`|---|---|`) is optional — omit it to create a table without header cells.

#### Markdown-to-Nodes Converter

`from_markdown(text: str) -> DocumentNode` parses a markdown string into postulator body nodes, ready to use as `Post.body`.

```python
from postulator import from_markdown

nodes = from_markdown("## Hello\n\nThis is **bold** and *italic*.\n\n- Item one\n- Item two")
# Returns: [HeadingNode, ParagraphNode, ListNode]
```

Supported block mappings:

| Markdown | Node |
|---|---|
| Paragraph | `ParagraphNode` |
| `# Heading` – `###### Heading` | `HeadingNode(level=1..6)` |
| `- item` / `* item` | `ListNode(ordered=False)` |
| `1. item` | `ListNode(ordered=True)` |
| Nested lists | `ListItemNode` with nested `ListNode` children |
| `> blockquote` | `BlockquoteNode` |
| `---` / `***` | `HrNode` |
| Fenced / indented code blocks | `ParagraphNode(children=[TextNode(marks=["code"])])` |
| Tables | `TableNode` (delegates to the `table()` helper) |
| HTML blocks | `ParagraphNode(children=[TextNode(value=raw_html)])` |

Supported inline mappings:

| Markdown | Node |
|---|---|
| Plain text | `TextNode` |
| `**bold**` | `TextNode(marks=["bold"])` |
| `*italic*` | `TextNode(marks=["italic"])` |
| `` `code` `` | `TextNode(marks=["code"])` |
| `[text](url)` | `HyperlinkNode` |
| Nested marks (`**bold *italic***`) | `TextNode(marks=["bold", "italic"])` |
| Inline HTML | `TextNode(value=raw_html)` |

Edge cases:
- Empty / whitespace-only input → `[]`
- Softbreaks and hardbreaks → `TextNode(value="\n")` (newlines preserved)
- `[**bold link**](url)` → `HyperlinkNode` with `TextNode(marks=["bold"])` child
- Images (`![alt](url)`) → skipped with a `logger.warning`

#### Inline Nodes

**TextNode** (`type="text"`)
- `value: str`
- `marks: list[Literal["bold", "italic", "underline", "code", "superscript", "subscript"]]`

**HyperlinkNode** (`type="hyperlink"`)
- `url: str`
- `children: list[TextNode]`

#### Embed Block Nodes

**AudiobookNode** (`type="audiobook"`)

Represents a single Audible product embed. You only need to provide `asin` and `marketplace` — the rest is auto-populated by scraping Audible during write.

| Field | Type | Required for render | Description |
|---|---|---|---|
| `asin` | `str` | Yes | Audible ASIN |
| `marketplace` | `str` | Yes | e.g. `"FR"`, `"US"`, `"DE"` |
| `source_id` | `str \| None` | — | Contentful entry ID (auto-set during write) |
| `title` | `str \| None` | Yes | Book title (auto-scraped) |
| `cover_url` | `str \| None` | Yes | Cover image URL (auto-scraped) |
| `pdp` | `str \| None` | Yes | Product detail page URL (auto-scraped) |
| `authors` | `list[AudiobookAuthor]` | Yes (name + pdp) | Author names and links (auto-scraped) |
| `summary` | `str \| None` | No | Publisher summary HTML |
| `label` | `str \| None` | No | Display label |
| `release_date` | `str \| None` | No | `YYYY-MM-DD` format |
| `narrators` | `list[AudiobookNarrator]` | No | Narrator names |
| `series` | `list[AudiobookSeries]` | No | Series info |

**AudiobookListNode** (`type="audiobook-list"`)

A list of audiobooks rendered as a grid. Maps to the `asinsList` content type.

| Field | Type | Default | Description |
|---|---|---|---|
| `asins` | `list[str]` | `[]` | ASINs to include |
| `asin_entry_ids` | `list[str]` | `[]` | Preserved Contentful entry IDs (used on read round-trip) |
| `asin_items` | `list[AudiobookListItem]` | `[]` | Per-item overrides for `descriptions="Custom"` mode |
| `children` | `list[AudiobookNode]` | `[]` | Fully resolved audiobook nodes for each child ASIN (populated by `adapter.read()`, ignored during write) |
| `title` | `str \| None` | `None` | Section title |
| `label` | `str \| None` | `None` | Display label |
| `body_copy` | `str \| None` | `None` | Intro copy |
| `player_type` | `str` | `"Cover"` | Player display type |
| `asins_per_row` | `int` | `1` | Items per row. Must be 1, 3, 4, or 5. |
| `descriptions` | `str` | `"Full"` | `"Full"`, `"Short"`, or `"Custom"` |
| `filters` | `list[str] \| None` | `None` | Filter options |
| `options` | `list[str]` | `[]` | Display options |

**AudiobookCarouselNode** (`type="audiobook-carousel"`)

A carousel of audiobooks. Maps to the `asinsCarousel` content type. Requires at least 4 ASINs.

| Field | Type | Default | Description |
|---|---|---|---|
| `asins` | `list[str]` | — | ASINs to include (minimum 4) |
| `asin_entry_ids` | `list[str]` | `[]` | Preserved Contentful entry IDs |
| `children` | `list[AudiobookNode]` | `[]` | Fully resolved audiobook nodes for each child ASIN (populated by `adapter.read()`, ignored during write) |
| `items_per_slide` | `int \| None` | `None` | Items visible per slide |
| `title` | `str \| None` | `None` | Carousel title |
| `subtitle` | `str \| None` | `None` | Subtitle |
| `body_copy` | `str \| None` | `None` | Intro copy |
| `cta_text` | `str \| None` | `None` | Call-to-action button text |
| `cta_url` | `str \| None` | `None` | CTA link URL |
| `options` | `list[str]` | `[]` | Display options |

**ContentImageNode** (`type="content-image"`)

An inline image embed. Maps to the `contentImage` content type.

| Field | Type | Default | Description |
|---|---|---|---|
| `source_id` | `str \| None` | `None` | Contentful entry ID (required for write) |
| `image` | `AssetRef \| LocalAsset \| None` | `None` | The image asset |
| `href` | `str \| None` | `None` | Link URL when image is clicked |
| `alignment` | `str \| None` | `None` | Image alignment |
| `size` | `str \| None` | `None` | Image size |

**EmbeddedAssetNode** (`type="embedded-asset"`)

A direct asset embed in the rich-text body. Unlike `ContentImageNode`, this does not use a wrapper entry — it maps directly to Contentful's `embedded-asset-block` rich-text node type. Simpler but without extra fields like alignment or link.

| Field | Type | Default | Description |
|---|---|---|---|
| `image` | `AssetRef \| LocalAsset` | — | The image asset. `LocalAsset` is auto-uploaded during write. |

```python
from postulator import EmbeddedAssetNode, LocalAsset, AssetRef

# Embed a local file (uploaded automatically during write)
node = EmbeddedAssetNode(image=LocalAsset(local_path="photo.png", title="My Photo"))

# Embed an existing Contentful asset
node = EmbeddedAssetNode(image=AssetRef(source_id="6qGUwWp4GiJ5Pqkkmk2nI4"))
```

**UnknownNode** (`type="unknown"`)
- `raw: dict` — raw Contentful JSON for unrecognized content types. Written back as-is.

### Assets

Two asset types:

**AssetRef** — references an existing Contentful asset (returned by reads and after upload).

| Field | Type | Description |
|---|---|---|
| `source_id` | `str \| None` | Contentful asset ID |
| `url` | `str \| None` | Public URL (always `https://`) |
| `title` | `str \| None` | Asset title |
| `alt` | `str \| None` | Alt text |
| `file_name` | `str \| None` | Original file name |
| `content_type` | `str \| None` | MIME type |
| `width` | `int \| None` | Image width in px |
| `height` | `int \| None` | Image height in px |
| `size` | `int \| None` | File size in bytes |

**LocalAsset** — a local file to upload during write.

| Field | Type | Description |
|---|---|---|
| `local_path` | `str` | Absolute or relative path to the file on disk |
| `title` | `str` | Asset title in Contentful |
| `alt` | `str \| None` | Alt text |
| `file_name` | `str \| None` | Override file name (defaults to basename of `local_path`) |
| `content_type` | `str \| None` | Override MIME type (auto-detected if omitted) |

During `adapter.write()` / `adapter.update()`, any `LocalAsset` on `featured_image`, `seo.og_image`, `ContentImageNode.image`, or `EmbeddedAssetNode.image` is automatically uploaded via the asset pipeline, which:
1. Reads the file from disk
2. Uploads bytes to Contentful's upload endpoint
3. Creates an asset entry linking to the upload
4. Processes the asset (Contentful server-side)
5. Polls until processing completes
6. Publishes the asset
7. Returns an `AssetRef` that replaces the `LocalAsset` in-place

### SEO Settings

`SeoMeta` — maps to the `seoSettings` content type.

| Field | Type | Default | Description |
|---|---|---|---|
| `source_id` | `str \| None` | `None` | Contentful entry ID (auto-set after write) |
| `label` | `str \| None` | `None` | Internal label (falls back to `"SEO Settings: {post.title}"`) |
| `slug_replacement` | `str \| None` | `None` | Override slug |
| `slug_redirect` | `str \| None` | `None` | Redirect slug |
| `no_index` | `bool \| None` | `None` | Set `noindex` meta tag |
| `meta_title` | `str \| None` | `None` | `<title>` tag |
| `meta_description` | `str \| None` | `None` | Meta description |
| `og_title` | `str \| None` | `None` | Open Graph title |
| `og_description` | `str \| None` | `None` | Open Graph description |
| `og_image` | `AssetRef \| LocalAsset \| None` | `None` | Open Graph image (LocalAsset auto-uploaded) |
| `schema_type` | `str \| None` | `None` | Schema.org type |
| `json_ld_id` | `str \| None` | `None` | Linked `jsonLd` entry ID |
| `similar_content_ids` | `list[str]` | `[]` | Entry IDs for similar content links |
| `external_links_source_code` | `str \| None` | `None` | Tracking source code for external links |

The SEO entry is created or updated automatically during `adapter.write()` / `adapter.update()` when `post.seo` is set. It publishes the entry and sets `seo.source_id` in-place.

## Known Quirks

### All fields are written under `en-US`

Contentful fields are always stored under the `"en-US"` locale key regardless of `post.locale`.
The `locale` field on `Post` controls `countryCode` (e.g. `FR`, `UK`) and determines which
Audible marketplace is used for ASIN scraping — it does not affect the Contentful field locale.
This is intentional given the current space setup but worth keeping in mind if multi-locale
field storage is ever needed.

### `asinDescriptions` — hybrid inline overrides

The `asinDescriptions` field on an `asinsList` entry stores a hybrid structure: each item contains
both a `sys` link pointing to the underlying `asin` entry **and** inline field overrides (`summary`,
`cover`, `title`, `editorBadge`, etc.) that take precedence over what is stored on the linked entry.

The `descriptions` field controls which data the frontend uses:
- `"Full"` / `"Short"` — reads summary from the linked `asin` entry directly
- `"Custom"` — reads the inline overrides from `asinDescriptions` instead

When writing an `AudiobookListNode` with custom per-item summaries, populate `asin_items` with
`AudiobookListItem` instances and set `descriptions="Custom"`. The write pipeline will resolve the
underlying `asin` entry IDs automatically and embed them alongside the inline overrides.

### ASIN deduplication

The write pipeline collects all ASINs across the entire post body (single embeds, lists, carousels),
deduplicates by `{ASIN}-{MARKETPLACE}` key, batch-resolves existing entries, and only scrapes/creates
missing ones. Duplicate `AudiobookNode`s referencing the same ASIN reuse the same `source_id`.

### Carousel minimum

`AudiobookCarouselNode` requires at least 4 ASINs. Carousels with fewer are skipped during write
(emits `carousel_skipped` event).

### `asins_per_row` validation

`AudiobookListNode.asins_per_row` must be one of `1`, `3`, `4`, `5`. Other values raise `ValueError`.

### `source_id` requirements for write

- `adapter.update()` requires `post.source_id` (use `adapter.write()` for new posts)
- `adapter.update_author()` requires `author.source_id` (use `adapter.create_author()` for new authors)
- `ContentImageNode` requires `source_id` for write (must reference an existing `contentImage` entry)
- `AudiobookListNode` and `AudiobookCarouselNode` get `source_id` auto-set during the post pipeline

### ASIN uniqueKey conflict resolution

When publishing an `asin` entry whose `uniqueKey` conflicts with an already-published entry,
the writer detects the conflict from the Contentful error response, deletes the duplicate,
and returns the ID of the existing entry.

### Stale ASIN draft cleanup

If a previous write failed mid-pipeline, it may leave behind unpublished `asin` draft entries
that block future writes. The writer handles this automatically:

1. During batch resolution, if a found entry is unpublished and fails to publish, it is deleted
   and treated as missing so it gets re-created fresh.
2. Before creating an entry with a deterministic ID, the writer checks whether a stale draft
   with that ID already exists and deletes it first.
3. If publishing a newly created entry still fails with a 422 uniqueKey conflict (e.g. due to
   a corrupted Contentful uniqueness index), the writer deletes the deterministic-ID entry and
   falls back to creating one with a random ID.

All draft cleanups emit the `asin_draft_cleanup` progress event.
