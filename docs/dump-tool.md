# tools/dump.py

A CLI utility for inspecting Contentful content types and entries.

## Usage

```
python tools/dump.py entry <entry_id>
python tools/dump.py content_type <content_type_id>
python tools/dump.py content_types
python tools/dump.py fetch_schema
```

## Subcommands

### `entry <entry_id>`
Prints the raw JSON of a single Contentful entry as returned by the CMA.

### `content_type <content_type_id>`
Prints the raw JSON schema of a single content type, including all field definitions and validations.

### `content_types`
Prints a compact summary of all content types — ID, name, and list of field IDs.

### `fetch_schema`
Fetches all content types and writes them as markdown files to `docs/schema/`:

- `docs/schema/index.md` — table of all content types with links
- `docs/schema/<content_type_id>.md` — one file per content type with a full field table (type, required, default, validations)

Run this whenever content types are added or modified in Contentful to keep the schema reference up to date.

## Notes

- `Object` fields in Contentful are schema-less JSON blobs — their structure is a convention enforced by the codebase, not by Contentful. See the relevant `nodes.py` models for the expected structure.
- Omitted fields are excluded from the generated markdown.
- Array and Link types are expanded for clarity, e.g. `Array<Link<Entry>>`.
