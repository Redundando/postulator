# Postulator CLI Reference

The `postulator` command-line tool provides read access to CMS content and developer utilities for inspecting spaces and models. Commands are namespaced by backend — currently `contentful`, with other backends planned for the future.

```bash
postulator <backend> <command> [options]
```

You can also run it as a Python module:

```bash
python -m postulator.cli <backend> <command> [options]
```

---

## Authentication

All Contentful commands require a space ID and CMA token. These can be provided in two ways:

1. **CLI flags** (highest priority):
   - `--space-id <id>`
   - `--token <token>`
   - `--environment <env>` (defaults to `master`)

2. **Environment variables** (used when flags are not provided):
   - `CONTENTFUL_SPACE_ID`
   - `CONTENTFUL_TOKEN`
   - `CONTENTFUL_ENVIRONMENT`

If a `.env` file exists in the current working directory, it is loaded automatically via `python-dotenv`.

**Flags always override environment variables.**

```bash
# Using env vars (set once in your shell profile or .env)
export CONTENTFUL_SPACE_ID=abc123
export CONTENTFUL_TOKEN=CFPAT-xxxxx
postulator contentful list-posts --locale fr-FR

# Using flags (per-call, useful for scripting or multiple spaces)
postulator contentful list-posts --locale fr-FR --space-id abc123 --token CFPAT-xxxxx
```

---

## Output Options

All commands print to stdout by default. Two flags control file output:

### `-o` / `--output <path>`

Write output to an explicit file path.

```bash
postulator contentful list-posts --locale it-IT -o italian-posts.csv
postulator contentful read-post abc123 --format json -o post.json
```

### `--output-dir <directory>`

Auto-generate a filename and write to the specified directory. The filename is composed of the command name, key parameters, and today's date.

```bash
postulator contentful list-posts --locale fr-FR --output-dir ./exports/
# → writes: ./exports/list-posts_fr-FR_2026-05-29.csv

postulator contentful list-tags --locale de-DE --format json --output-dir ./exports/
# → writes: ./exports/list-tags_de-DE_2026-05-29.json
```

The directory is created if it doesn't exist.

---

## Output Formats

List commands support `--format csv|json|markdown` (default: `csv`).
Single-item read commands support `--format markdown|json` (default: `markdown`).

| Format | Extension | Description |
|---|---|---|
| `csv` | `.csv` | Comma-separated values with header row |
| `json` | `.json` | Pretty-printed JSON |
| `markdown` | `.md` | Markdown table (for lists) or rendered document (for reads) |

---

## Content Commands

### `postulator contentful list-posts`

List posts with optional filters. Returns a summary table (entry ID, slug, title, date).

```bash
postulator contentful list-posts --locale <locale> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--locale` | Yes | — | BCP-47 locale (e.g. `fr-FR`, `it-IT`, `en-GB`) |
| `--author` | No | — | Filter by author slug |
| `--tag` | No | — | Filter by tag slug |
| `--slug` | No | — | Filter by slug pattern (substring match, e.g. `genre-`) |
| `--limit` | No | `10` | Maximum number of posts to return |
| `--format` | No | `csv` | Output format: `csv`, `json`, or `markdown` |

**Examples:**

```bash
# Latest 10 Italian posts (default)
postulator contentful list-posts --locale it-IT

# Latest 5 French posts by a specific author
postulator contentful list-posts --locale fr-FR --author laura-tufari --limit 5

# Posts tagged "thriller" in the UK market, as JSON
postulator contentful list-posts --locale en-GB --tag thriller --format json

# Find all posts with "genre-" in the slug
postulator contentful list-posts --locale de-DE --slug "genre-" --limit 100

# Fetch all posts in a market (pagination handled automatically)
postulator contentful list-posts --locale de-DE --limit 2000
```

**Output columns:** `entry_id`, `slug`, `title`, `date`

Results are ordered by date descending (newest first).

**Pagination:** When the requested limit exceeds a single API page (200 items), the CLI automatically paginates through results in batches. You can safely request any number — it will fetch until the limit is reached or all matching entries are returned.

---

### `postulator contentful read-post`

Read a full post by its Contentful entry ID. Resolves all linked entries (authors, tags, audiobooks, images) and renders the complete body.

```bash
postulator contentful read-post <entry_id> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `<entry_id>` | Yes (positional) | — | Contentful entry ID |
| `--locale` | No | `en-US` | Locale for reading |
| `--format` | No | `markdown` | Output format: `markdown` or `json` |

**Examples:**

```bash
# Read as rendered markdown
postulator contentful read-post 6tYgaQ5P2NxTes7YHGsOXE --locale it-IT

# Read as JSON (full Pydantic model dump)
postulator contentful read-post 6tYgaQ5P2NxTes7YHGsOXE --locale it-IT --format json

# Save to file
postulator contentful read-post 6tYgaQ5P2NxTes7YHGsOXE --locale it-IT -o post.md
```

**Markdown output includes:**
- Title, entry ID, slug, locale, date
- Authors and tags
- Introduction (if present)
- Full body rendered as markdown (headings, paragraphs, lists, blockquotes, audiobook embeds, tables, images)

**JSON output** is the full `Post` model serialized via Pydantic's `model_dump_json()`.

---

### `postulator contentful find`

Find a post or category entry by its slug.

```bash
postulator contentful find <slug> --locale <locale> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `<slug>` | Yes (positional) | — | Post or category slug |
| `--locale` | Yes | — | BCP-47 locale |
| `--format` | No | `json` | Output format: `json` or `markdown` |

**Examples:**

```bash
# Find by slug
postulator contentful find migliori-libri-2026 --locale it-IT

# Markdown summary
postulator contentful find top-books-june --locale en-GB --format markdown
```

Returns the raw Contentful entry (JSON) or a brief markdown summary. Prints a message if no entry is found.

---

### `postulator contentful list-authors`

List authors for a locale/market.

```bash
postulator contentful list-authors --locale <locale> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--locale` | Yes | — | BCP-47 locale |
| `--limit` | No | `10` | Maximum number of authors to return |
| `--format` | No | `csv` | Output format: `csv`, `json`, or `markdown` |

**Examples:**

```bash
postulator contentful list-authors --locale it-IT
postulator contentful list-authors --locale fr-FR --limit 20 --format markdown
```

**Output columns:** `entry_id`, `slug`, `name`, `title`

---

### `postulator contentful read-author`

Read a full author by entry ID.

```bash
postulator contentful read-author <entry_id> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `<entry_id>` | Yes (positional) | — | Contentful entry ID |
| `--locale` | No | `en-US` | Locale for reading |
| `--format` | No | `markdown` | Output format: `markdown` or `json` |

**Examples:**

```bash
postulator contentful read-author 28rBK7rpTDSZ1SgCKfZWg2 --locale it-IT
postulator contentful read-author 28rBK7rpTDSZ1SgCKfZWg2 --format json
```

---

### `postulator contentful list-tags`

List all tags for a locale/market.

```bash
postulator contentful list-tags --locale <locale> [options]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--locale` | Yes | — | BCP-47 locale |
| `--format` | No | `csv` | Output format: `csv`, `json`, or `markdown` |

**Examples:**

```bash
postulator contentful list-tags --locale it-IT
postulator contentful list-tags --locale en-GB --format json -o uk-tags.json
```

**Output columns:** `entry_id`, `slug`, `name`

---

## Inspection Commands

Low-level commands for inspecting raw Contentful data. Useful for debugging and schema documentation.

### `postulator contentful entry`

Dump a single Contentful entry as raw JSON.

```bash
postulator contentful entry <entry_id>
```

```bash
postulator contentful entry 6nY8mRqIVO42icaoSquMYS
postulator contentful entry 6nY8mRqIVO42icaoSquMYS --space-id abc --token CFPAT-xxx
```

---

### `postulator contentful content-type`

Dump a content type definition as JSON.

```bash
postulator contentful content-type <content_type_id>
```

```bash
postulator contentful content-type post
postulator contentful content-type asin
```

---

### `postulator contentful content-types`

List all content types in the space as JSON (ID, name, field names).

```bash
postulator contentful content-types
```

---

### `postulator contentful schema`

Fetch all content types and generate markdown documentation files — one per content type plus an index.

```bash
postulator contentful schema [--output-schema-dir <dir>]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--output-schema-dir` | No | `docs/schema` | Output directory for generated markdown files |

```bash
postulator contentful schema                              # writes to docs/schema/
postulator contentful schema --output-schema-dir my-docs/ # custom directory
```

---

## Top-Level Commands

### `postulator models`

Dump the JSON Schema for every postulator Pydantic model (Post, Author, all body nodes, assets, SEO, etc.). No Contentful credentials required.

```bash
postulator models
postulator models > models.json
```

Designed for LLM consumers that need to understand the full type system.

---

## Supported Locales

The `--locale` flag accepts BCP-47 locale strings. These map to Contentful country codes and Audible marketplaces:

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

---

## Error Handling

- Missing credentials → clear error message listing what's needed
- Invalid locale → error with list of valid options
- Author/tag not found (when filtering) → error naming the slug that wasn't found
- API errors → HTTP status code and Contentful error message
- No results → informational message (not an error exit code)
