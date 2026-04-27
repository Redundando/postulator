# Placeholder Improvements Plan

## Goal

Make DOCX placeholders editor-friendly: minimal required input, sensible defaults, robust parsing, consistent syntax across all placeholder types.

Two phases:
1. **Per-placeholder improvements** — aliases, defaults, syntax consistency
2. **Post-processing** — inference logic after initial parse (e.g. derive intro from first paragraph)

This document covers Phase 1. Phase 2 will be added after Phase 1 is agreed.

---

## Syntax Rules (Agreed)

### Bracket Delimiters

All placeholders use `[` and `]` as delimiters. Two forms:

**Single-line:**
```
[TYPE value]
[TYPE: value]
```

**Multi-line:**
```
[TYPE
key = value
key = "quoted value"
]
```

Or:
```
[TYPE:
key = value
]
```

The `:` after the TYPE keyword is always optional.
```

### Multi-line Closing Rule

- The closing `]` must appear on its own line (optionally with surrounding whitespace).
- A `]` that appears inside a value line does NOT close the block.

### Key-Value Pairs

- `key = value` — spaces around `=` are optional and ignored.
- `key = "quoted value"` — quotes are optional. Use them when the value contains special characters.
- Keys are case-insensitive, and spaces/hyphens/underscores are normalized (e.g. `Meta Title`, `meta-title`, `meta_title` all resolve to the same key).
- Blank lines and extra whitespace inside a block are ignored.

### Escaping

- `\[` → literal `[`
- `\]` → literal `]`
- `\"` → literal `"` (inside quoted values)
- `\\` → literal `\`

Backslash escaping applies to the content/values only, not to the structural `[` and `]` that open/close the block.

### TYPE Keyword

- Case-insensitive.
- Spaces, hyphens, and underscores are normalized (e.g. `FEATURED IMAGE`, `featured-image`, `featured_image` all match).
- Multiple aliases per placeholder type are supported (e.g. `ASIN` and `AUDIOBOOK` both resolve to the audiobook placeholder).

---

## Placeholders

### POST

**Keyword:** `post` (case-insensitive)

**Keys:**

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| `title` | — | Yes | None | Post title |
| `market` | — | Yes | None | Country code: `DE`, `UK`, `FR`, `IT`, `ES`, `US`, `AU`, `CA_EN`, `CA_FR` |
| `slug` | — | No | Derived from title via slugify | URL slug |
| `date` | — | No | Today (UTC) | Publish date. Accepts `2025-06-01`, `01.06.2025`, `06/01/2025` |
| `intro` | `introduction` | No | None | Short introduction text |
| `source-id` | — | No | None | Contentful entry ID (round-trip) |
| `update-date` | — | No | None | Last-updated date (same formats as `date`) |
| `show-in-feed` | `feed` | No | `true` | Show in blog feed |
| `show-publish-date` | — | No | `true` | Show publish date on page |
| `show-hero-image` | — | No | `true` | Show hero image on page |
| `custom-recommended-title` | — | No | None | Override title for recommended widgets |
| `related-posts` | — | No | None | Comma-separated Contentful entry IDs |

All keys accept both dashes and underscores interchangeably (`show-in-feed` = `show_in_feed` = `show in feed`).

**Minimal example (editor-facing):**
```
[Post
title = My First Post
market = DE
]
```

**Full example (round-trip):**
```
[Post
title = My First Post
market = DE
slug = my-first-post
date = 2025-06-01
intro = A short introduction to the post.
source-id = 7o06g0WBcE5BRv9pg5m3YQ
show-in-feed = true
]
```

**Changes from current:**
- Removed `title_override` and `post_title` aliases — only `title` is accepted.
- Removed `locale` key — use `market` instead. `CA_EN` / `CA_FR` distinguish Canadian English/French.
- `introduction` is now an alias for `intro` (was the other way around).

### AUTHORS

**Keyword:** `author`, `authors` (case-insensitive)

**Format:** List of items. Each item is an author name with optional key-value metadata.

| Per-item field | Required | Default | Description |
|---|---|---|---|
| (bare text) | Yes | — | Author name |
| `id` | No | Resolved by name during write | Contentful entry ID (round-trip) |

**Single author (single-line):**
```
[Authors: Christian Lütjens]
```

**Multiple authors (multi-line):**
```
[Authors
Christian Lütjens
Jane Doe
]
```

**Round-trip (with IDs):**
```
[Authors
Christian Lütjens, id=5kk5gP7mXl2CjiFyz9ZBDM
Jane Doe, id=abc123
]
```

**Parsing rules:**
- Single-line: content after `:` is one item.
- Multi-line: each non-blank line that is not a top-level `key=value` is one item.
- Within each item line: bare text before the first comma is the name. Comma-separated segments containing `=` are key-value pairs for that item.

**Changes from current:**
- Removed `|` as per-item field separator — use commas instead.
- Multi-line form is now supported.

### TAGS

**Keyword:** `tag`, `tags` (case-insensitive)

**Format:** Identical to AUTHORS — list of items, each a tag name with optional metadata.

| Per-item field | Required | Default | Description |
|---|---|---|---|
| (bare text) | Yes | — | Tag name |
| `id` | No | Resolved by name during write | Contentful entry ID (round-trip) |

**Single tag (single-line):**
```
[Tags: Thriller]
```

**Multiple tags (multi-line):**
```
[Tags
Thriller
Psychothriller
Aktuelles
]
```

**Round-trip (with IDs):**
```
[Tags
Thriller, id=912801934-de-tag
Psychothriller, id=3740724469-de-tag
Aktuelles, id=3897901234-de-tag
]
```

**Note on commas in tag names:** If a tag name contains a comma (e.g. `Crime, Thriller & Mystery`), use quoting: `"Crime, Thriller & Mystery"`. The quoted text is treated as the bare name value.

**Parsing rules:** Same as AUTHORS.

**Changes from current:**
- Removed `|` as per-item field separator — use commas instead.
- Multi-line form is now supported.

### SEO

**Keyword:** `seo` (case-insensitive)

**Keys:**

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| `meta-title` | `title` | No | Post title (post-processing) | `<title>` tag |
| `meta-description` | `desc` | No | Post intro (post-processing) | Meta description |
| `og-title` | `open-graph-title` | No | None | Open Graph title |
| `og-description` | `open-graph-description` | No | None | Open Graph description |
| `no-index` | — | No | None | `true` / `false` — sets `noindex` meta tag |
| `label` | — | No | `"SEO Settings {meta_title}"` | Internal label in Contentful |
| `source-id` | `id` | No | None | Contentful entry ID (round-trip) |
| `schema-type` | — | No | None | Schema.org type |
| `slug-replacement` | — | No | None | Override slug |
| `slug-redirect` | — | No | None | Redirect slug |
| `external-links-source-code` | `source-code` | No | None | Tracking source code for external links |

All keys accept both dashes and underscores interchangeably.

**Minimal example (editor-facing):**
```
[SEO
title = My SEO Title
desc = A short description for search engines.
]
```

**Full example (round-trip):**
```
[SEO
source-id = 2ToK8irbDON83NuobLrjUj
label = SEO Settings: My SEO Title
meta-title = My SEO Title
meta-description = A short description for search engines.
og-title = My OG Title
og-description = My OG Description
no-index = false
schema-type = Article
slug-replacement = custom-slug
external-links-source-code = campaign-123
]
```

**Changes from current:**
- Removed `index` key — use `no-index` only (no more inversion logic).
- Removed `seo_title`, `seo-title`, `seo_description`, `seo-description`, `seo_id`, `seo_source_id`, `seo_label` aliases — redundant inside an `[SEO]` block.
- Added `title` as alias for `meta-title`.
- Default `label` is `"SEO Settings {meta_title}"` when not explicitly set.

### FEATURED IMAGE

**Keyword:** `featured image`, `featured-image`, `featured_image`, `hero image`, `hero` (case-insensitive)

**Keys:**

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| `title` | — | No | Post title | Asset title in Contentful |
| `alt` | — | No | Post title | Alt text |
| `source-id` | `id` | No | None | Contentful asset ID (round-trip) |

All keys accept both dashes and underscores interchangeably.

**Image detection:** The adapter looks for an inline image (a paragraph containing only an image, no text) in two places:
1. Inside the block — any image-only paragraph between `[` and `]`.
2. After the block — the next paragraph immediately following `]`.

Both locations are supported. If found, the image is extracted as a `LocalAsset`.

**Minimal example (editor-facing):**
```
[Hero]
<pasted image>
```

Or:
```
[Hero
<pasted image>
]
```

**With metadata (round-trip):**
```
[Featured Image
source-id = 4Nhg2qlB3DDtOns7pMYaph
title = My Hero Image
alt = A description of the image
]
<embedded image>
```

**Changes from current:**
- Image inside the block is now accepted (not just after).
- Default `title` and `alt` fall back to the post title when not set.

**Phase 2 note:** Consider detecting a leading image (before any body content) as the featured image even without a `[Featured Image]` block.

### INTRO

**Keyword:** `intro`, `introduction` (case-insensitive)

**Format:** Plain text content. No key-value pairs — the entire content inside the block is the introduction text.

**Single-line:**
```
[Intro: This is the introduction text.]
```

**Multi-line:**
```
[Intro
This is the introduction text.
It can span multiple lines.
]
```

The `:` after the keyword is optional (as with all placeholders).

Multiple lines are joined with `\n`. The result is stored as a plain string — no rich text formatting is preserved (Contentful's `introduction` field is plain `Text`).

**Conflict with POST `intro` key:** If both a `[Post intro=...]` key and a separate `[Intro]` block are present, the conflict is resolved in post-processing (Phase 2).

**Changes from current:**
- `:` after keyword is now optional.

### AUDIOBOOK (inline embed)

**Keyword:** `asin`, `audiobook` (case-insensitive)

**Format:** Single-line. Positional ASIN with optional marketplace override.

| Field | Required | Default | Description |
|---|---|---|---|
| (positional) | Yes | — | Audible ASIN |
| `market` | No | Post's market | Marketplace override (e.g. `FR`, `US`) |

**Minimal example:**
```
[ASIN B0G4943RH8]
```

**With marketplace override:**
```
[ASIN B0G4943RH8, market=FR]
```

**Also accepted:**
```
[Audiobook B0G4943RH8]
[Audiobook: B0G4943RH8]
[asin: B0G4943RH8, market=FR]
```

The `:` after the keyword is optional (as with all placeholders).

**Changes from current:**
- Added `asin` as keyword alias.
- Replaced `|` separator with `,` for consistency with other placeholders.

### LIST (audiobook list embed)

**Keyword:** `list`, `audiobook-list`, `asin-list` (case-insensitive)

**Format:** Multi-line. Bare ASIN list plus optional key-value pairs.

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| (positional) | — | Yes | — | Comma-separated ASINs |
| `title` | — | No | None | Section title |
| `label` | — | No | Post title (post-processing) | Display label |
| `per-row` | `columns` | No | `1` | Items per row (1, 3, 4, or 5) |
| `body-copy` | `copy`, `description` | No | None | Intro copy |
| `market` | — | No | Post's market | Marketplace override |
| `descriptions` | — | No | `Full` | `Full`, `Short`, or `Custom` |
| `player-type` | — | No | `Cover` | Player display type |
| `source-id` | `id` | No | None | Contentful entry ID (round-trip) |

All keys accept both dashes and underscores interchangeably.

**Minimal example (editor-facing):**
```
[List
B012Y9Y6ZE, B07CM9S3WV, 3844533168
title = My Favourite Books
]
```

**Full example (round-trip):**
```
[List
B012Y9Y6ZE, B07CM9S3WV, 3844533168
title = My Favourite Books
label = Top Picks
per-row = 3
body-copy = Check out these great listens.
descriptions = Full
player-type = Cover
id = abc123
]
```

**Changes from current:**
- Added `audiobook-list` and `asin-list` as keyword aliases.
- Added `columns` as alias for `per-row`.
- Added `copy` and `description` as aliases for `body-copy`.
- `:` after keyword is now optional.
- Default `label` falls back to post title (post-processing).

### CAROUSEL (audiobook carousel embed)

**Keyword:** `carousel`, `audiobook-carousel`, `asin-carousel` (case-insensitive)

**Format:** Multi-line. Bare ASIN list plus optional key-value pairs.

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| (positional) | — | Yes | — | Comma-separated ASINs |
| `title` | — | No | None | Carousel title |
| `subtitle` | — | No | None | Subtitle |
| `body-copy` | `copy`, `description` | No | None | Intro copy |
| `cta-text` | `cta` | No | None | Call-to-action button text |
| `cta-url` | — | No | None | CTA link URL |
| `items-per-slide` | `per-slide` | No | None | Items visible per slide |
| `market` | — | No | Post's market | Marketplace override |
| `source-id` | `id` | No | None | Contentful entry ID (round-trip) |

All keys accept both dashes and underscores interchangeably.

**Minimal example (editor-facing):**
```
[Carousel
B012Y9Y6ZE, B07CM9S3WV, 3844533168, B0G4943RH8
title = All Books by Author X
]
```

**Full example (round-trip):**
```
[Carousel
B012Y9Y6ZE, B07CM9S3WV, 3844533168, B0G4943RH8
title = All Books by Author X
subtitle = A complete overview
body-copy = Discover the full catalogue.
cta-text = Browse all
cta-url = https://example.com/browse
items-per-slide = 4
id = abc123
]
```

**Changes from current:**
- Added `audiobook-carousel` and `asin-carousel` as keyword aliases.
- Added `copy` and `description` as aliases for `body-copy`.
- Added `cta` as alias for `cta-text`.
- Added `per-slide` as alias for `items-per-slide`.
- `:` after keyword is now optional.

### CONTENT IMAGE (inline embed)

**Keyword:** `image`, `content-image` (case-insensitive)

**Format:** Block with optional key-value pairs. Image is detected inside the block or in the next paragraph after it (same logic as FEATURED IMAGE).

| Key | Aliases | Required | Default | Description |
|---|---|---|---|---|
| `href` | `link`, `url` | No | None | Link URL when image is clicked |
| `alignment` | `align` | No | None | Image alignment |
| `size` | — | No | None | Image size |
| `title` | — | No | None | Asset title |
| `alt` | — | No | None | Alt text |
| `source-id` | `id` | No | None | Contentful `contentImage` entry ID (round-trip) |

All keys accept both dashes and underscores interchangeably.

**Node type selection:** The adapter picks the appropriate node type automatically:
- If `href`, `alignment`, `size`, or `source-id` are set → `ContentImageNode` (Contentful wrapper entry with extra fields).
- If none of those are set (just an image) → `EmbeddedAssetNode` (simple direct asset embed).
- A bare pasted image in the body with no `[Image]` block at all → `EmbeddedAssetNode` (current behavior, unchanged).

**Image detection:** Same as FEATURED IMAGE — looks for an image-only paragraph inside the block or immediately after it.

**Minimal example (editor-facing):**
```
[Image]
<pasted image>
```

**With link and alignment:**
```
[Image
href = https://example.com
alignment = center
size = large
]
<pasted image>
```

**Round-trip:**
```
[Image
source-id = abc123
href = https://example.com
alignment = center
]
```

**Changes from current:**
- Added `image` as keyword alias (primary, editor-friendly).
- Added `link`, `url` as aliases for `href`.
- Added `align` as alias for `alignment`.
- Added `title` and `alt` keys.
- Image inside the block is now accepted (not just referenced by ID).
- Node type (`ContentImageNode` vs `EmbeddedAssetNode`) is selected automatically based on which keys are present.

### UNKNOWN (round-trip safety)

**Keyword:** `unknown` (case-insensitive)

**Format:** Single-line. Content is raw JSON. No key-value pairs.

```
[Unknown: {"sys":{"id":"abc123"},"fields":{}}]
```

This placeholder exists purely for round-trip safety. When reading from Contentful, any embedded entry with an unrecognized content type is preserved as an `UnknownNode` with the raw JSON. When writing to DOCX, the JSON is serialized into this placeholder. When reading the DOCX back, the JSON is parsed back into an `UnknownNode`.

Editors will never create these. No changes from current implementation.

---

## Post-Processing (Phase 2)

### Principles

- Phase 1 (per-placeholder parsing) returns only what was explicitly set. No cross-referencing, no defaults that depend on other placeholders.
- Phase 2 looks at the assembled result across all placeholders and fills in gaps.
- Placeholder position in the document does not matter.

### Duplicate Placeholders

If the same placeholder type appears multiple times (e.g. two `[Post]` blocks), they are **merged**. For identical keys, the **first-seen value wins**.

### Precedence Rules

**Title:**
1. POST `title` key
2. Filename (minus extension)

**Intro:**
1. `[Intro]` block
2. POST `intro` key
3. First paragraph of body (removed from body when used)

`intro = ""` (empty string) in the POST block explicitly means "no intro" — blocks further fallback including first-paragraph inference.

When writing back to DOCX, if an intro is set, it is written as an `[Intro]` block (not as a POST key).

**Slug:**
1. POST `slug` key
2. Derived from title via slugify

**Date:**
1. POST `date` key
2. Today (UTC)

**Market:**
1. POST `market` key
2. Default: `US`

### Default Values (cross-placeholder)

Applied in order — later rules may depend on earlier ones.

1. **Title** resolved (from POST or filename)
2. **Slug** resolved (from POST or title)
3. **Date** resolved (from POST or today)
4. **Market** resolved (from POST or `US`)
5. **Intro** resolved (from INTRO block, POST key, or first paragraph)
6. **SEO `meta-title`** ← post title if not set
7. **SEO `meta-description`** ← intro if not set
8. **SEO `og-title`** ← SEO `meta-title` if not set
9. **SEO `og-description`** ← SEO `meta-description` if not set
10. **SEO `label`** ← `"SEO Settings {meta_title}"` if not set
11. **Featured image `title`** ← post title if not set
12. **Featured image `alt`** ← post title if not set
13. **LIST `label`** ← post title if not set

### No POST Block

If no `[Post]` block is present, post-processing still assembles a Post using:
- Title from filename
- Date from today
- Market defaults to `US`
- Slug derived from title
- Body from all non-placeholder content
- Other metadata from any placeholders that are present (`[Authors]`, `[Tags]`, `[SEO]`, etc.)
