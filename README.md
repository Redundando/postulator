# Postulator

## Overview

Postulator is a Python library for programmatically creating, reading, and publishing blog posts to Contentful CMA (Content Management API). It provides Pydantic models for posts, rich-text body nodes, audiobook embeds, SEO settings, and authors — plus an async Contentful client that handles ASIN resolution, asset uploads, and entry publishing in a single pipeline.

The primary consumer is other LLMs and automation scripts that need to compose and publish Audible blog content to a Contentful space.

## Installation

```bash
pip install postulator
```

Dependencies (installed automatically): `pydantic`, `httpx`, `python-dotenv`, `scraperator`, `markdown-it-py`.

## Configuration

Set these environment variables (or use a `.env` file with `python-dotenv`):

| Variable | Required | Description |
|---|---|---|
| `CONTENTFUL_TOKEN` | Yes | Contentful CMA personal access token |
| `CONTENTFUL_SPACE_ID` | Yes | Contentful space ID |
| `CONTENTFUL_ENVIRONMENT` | No | Contentful environment (defaults to `"master"`) |

## Quick Start

```python
import asyncio
from datetime import datetime, timezone
from postulator import Post, ParagraphNode, TextNode, HeadingNode, AudiobookNode
from postulator.adapters.contentful import ContentfulClient

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
        created = await client.create_post(post, publish=True)
        print(created.source_id)

asyncio.run(main())
```

The pipeline automatically:
1. Enriches `AudiobookNode`s by scraping Audible (title, cover, PDP URL, authors, etc.)
2. Creates/reuses `asin` entries in Contentful
3. Creates `asinsList` / `asinsCarousel` entries for list/carousel nodes
4. Uploads any `LocalAsset` images
5. Creates/updates the `seoSettings` entry if `post.seo` is set
6. Creates the `post` entry with rich-text body referencing all embedded entries
7. Publishes everything

## ContentfulClient

Async HTTP client wrapping the Contentful CMA. Must be used as an async context manager.

```python
from postulator.adapters.contentful import ContentfulClient

async with ContentfulClient(
    space_id="<space_id>",
    environment="master",
    token="<token>",
    on_progress=lambda e: print(e),
) as client:
    ...
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `space_id` | `str` | — | Contentful space ID |
| `environment` | `str` | — | Environment name |
| `token` | `str` | — | CMA access token |
| `batch_size` | `int` | `200` | Max entries per batch request |
| `asset_poll_attempts` | `int` | `10` | Polls before asset processing timeout |
| `asset_poll_interval` | `float` | `1.0` | Seconds between asset processing polls |
| `on_progress` | `Callable \| None` | `None` | Progress callback (receives `dict` with `event`, `ts`, and extra keys) |

### High-Level Methods

**Posts:**
- `create_post(post, publish=False) -> Post` — full pipeline: enrich ASINs, upload assets, create all entries, create post. Returns the round-tripped `Post`.
- `write_post(post, publish=True) -> Post` — same pipeline but updates an existing post (`post.source_id` required).
- `read_post(entry_id, locale="en-US") -> Post` — reads a post and all its linked entries/assets into a `Post` model.

**Authors:**
- `create_author(author, publish=False) -> Author` — creates a new author entry.
- `write_author(author, publish=True) -> Author` — updates an existing author (`author.source_id` required).
- `read_author(entry_id, locale="en-US") -> Author` — reads an author entry.
- `list_authors(country_code, locale="en-US") -> list[Author]` — lists all authors for a country code.

**Tags:**
- `list_tags(country_code, locale="en-US") -> list[TagRef]` — lists all tags for a country code.

**Lookup:**
- `find_entry_by_slug(slug, locale) -> dict | None` — checks whether a `post` or `category` entry with the given slug and country code already exists. Useful for verifying a slug is available before creating a new post. The `locale` parameter uses the same locale → country code mapping as `Post.locale` (see [Locale & Marketplace Mapping](#locale--marketplace-mapping)). Returns the raw Contentful entry dict if found, `None` otherwise.

```python
# Check if a post with this slug already exists in the UK space
existing = await client.find_entry_by_slug(slug="top-books-june-2026", locale="en-GB")
if existing:
    print(f"Already exists: {existing['sys']['id']}")
else:
    print("Slug is available")
```

**SEO:**
- `write_seo(seo, fallback_label) -> str` — creates or updates a `seoSettings` entry. Returns entry ID.

**Assets:**
- `upload_local_asset(asset: LocalAsset) -> AssetRef` — uploads, processes, publishes a local file. Returns the resulting `AssetRef`.

**Embeds (usually called automatically by the post pipeline):**
- `write_asin(node: AudiobookNode) -> str` — creates or reuses an `asin` entry. Returns entry ID.
- `write_asin_list(node: AudiobookListNode, asin_nodes) -> str` — creates or updates an `asinsList` entry.
- `write_asin_carousel(node: AudiobookCarouselNode, asin_nodes) -> str` — creates or updates an `asinsCarousel` entry.

### Retry Behaviour

All HTTP requests retry up to 3 times on status codes `429`, `500`, `502`, `503`, `504` with exponential backoff (`2^attempt` seconds). Non-retryable errors raise `httpx.HTTPStatusError` immediately.

### Progress Events

The `on_progress` callback receives dicts with an `event` key. Events emitted:

| Event | When | Extra keys |
|---|---|---|
| `fetching_entries` | Before batch-fetching linked entries during read | `count` |
| `fetching_nested` | Before fetching nested linked entries | `count` |
| `parsing` | Before parsing raw Contentful data into models | — |
| `resolving_asins` | Before batch-resolving existing ASIN entries | `count` |
| `enriching_asins` | Before scraping Audible for missing ASINs | `count` |
| `writing_asin` | Before creating/reusing a single ASIN entry | `asin`, `marketplace` |
| `asin_publish_conflict` | When a uniqueKey conflict is detected and resolved | `asin`, `entry_id` |
| `asin_publish_failed` | When publishing an ASIN entry fails | `asin`, `message` |
| `uploading_asset` | Before uploading a local asset | `title`, `file_name` |
| `asset_upload_failed` | When asset upload fails | `title`, `message` |
| `asset_processing_timeout` | When asset processing polling times out | `asset_id` |
| `writing_post` | Before updating a post entry | `entry_id` |
| `creating_post` | Before creating a new post entry | `slug`, `locale` |
| `writing_author` | Before updating an author entry | `entry_id` |
| `creating_author` | Before creating a new author entry | `slug` |
| `post_invalid` | When post validation fails | `slug`, `reason` |
| `list_skipped` | When an AudiobookListNode is skipped (0 ASINs) | `reason` |
| `carousel_skipped` | When a carousel is skipped (<4 ASINs) | `reason`, `asins` |
| `request_failed` | When an HTTP request fails (non-retryable or after retries) | `method`, `url`, `status_code` |

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

## Scraperator Adapter

The `postulator.adapters.scraperator` module wraps the `scraperator` library to batch-scrape Audible product pages and populate `AudiobookNode` fields.

`enrich_audiobook_nodes(nodes, on_progress=None)` fills in `title`, `pdp`, `cover_url`, `summary`, `release_date`, `authors`, and `narrators` on each node — only for fields that are `None`/empty (never overwrites manually-set data).

To configure caching:

```python
from postulator.adapters.scraperator import configure

configure(
    cache="local",              # "local" or "dynamodb"
    cache_directory="cache",    # local cache dir
    cache_table=None,           # DynamoDB table name
    scrape_cache="none",        # raw scrape cache
)
```

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
| `source_id` | `str \| None` | `None` | Contentful entry ID. Required for `write_post`, auto-set by `create_post`. |
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
| `source_id` | `str \| None` | `None` | Contentful entry ID. Required for `write_author`. |
| `country_code` | `str \| None` | `None` | e.g. `"FR"`, `"UK"` |
| `slug` | `str` | — | URL slug |
| `name` | `str` | — | Display name |
| `short_name` | `str \| None` | `None` | Abbreviated name |
| `title` | `str \| None` | `None` | Job title / role |
| `bio` | `str \| None` | `None` | Biography text |
| `picture` | `AssetRef \| LocalAsset \| None` | `None` | Profile picture |
| `seo` | `SeoMeta \| None` | `None` | SEO settings for the author page |

### Authors & Tags (References)

`AuthorRef` and `TagRef` are lightweight references used on `Post`. Both require `source_id` to be set to an existing Contentful entry ID for writes.

```python
from postulator import AuthorRef, TagRef

post.authors = [
    AuthorRef(slug="fr-author", locale="fr-FR", name="FR Author", source_id="52621970-fr-author"),
]
post.tags = [
    TagRef(slug="fr-tag", locale="fr-FR", name="FR Tag", source_id="2093616522-fr-tag"),
]
```

To discover existing author/tag IDs, use `client.list_authors(country_code, locale)` and `client.list_tags(country_code, locale)` (see [High-Level Methods](#high-level-methods)).

### Body Nodes

`DocumentNode` is `list[BlockNode]`. Each `BlockNode` is a discriminated union (on `type`).

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

During `create_post` / `write_post`, any `LocalAsset` on `featured_image`, `seo.og_image`, or `ContentImageNode.image` is automatically uploaded via `upload_local_asset`, which:
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

`write_seo` creates a new `seoSettings` entry if `seo.source_id` is `None`, or updates the existing one. It publishes the entry and sets `seo.source_id` in-place.

## Appendix: Low-Level Client Methods

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
`AudiobookListItem` instances and set `descriptions="Custom"`. `write_asin_list` will resolve the
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

- `write_post` requires `post.source_id` (use `create_post` for new posts)
- `write_author` requires `author.source_id` (use `create_author` for new authors)
- `ContentImageNode` requires `source_id` for write (must reference an existing `contentImage` entry)
- `AudiobookListNode` and `AudiobookCarouselNode` get `source_id` auto-set during the post pipeline; when calling `write_asin_list` / `write_asin_carousel` directly, set `source_id` to update or leave `None` to create

### ASIN uniqueKey conflict resolution

When publishing an `asin` entry whose `uniqueKey` conflicts with an already-published entry,
the writer detects the conflict from the Contentful error response, deletes the duplicate,
and returns the ID of the existing entry.
