# Contentful Schema Reference

> For full field definitions, see the auto-generated schema files in [`docs/schema/`](./schema/index.md).
> Run `python tools/dump.py fetch_schema` to refresh them.

---

## Key Concepts

**Locale vs Country Code:**
All fields are stored under the `en-US` key in the Contentful API response, regardless of market. The `countryCode` field on each entry determines the actual market. See `marketplace.py` for the full locale → country code mapping.

**Object fields:**
`Object` typed fields (e.g. `authors`, `narrators`, `series` on `asin`) are schema-less JSON blobs — Contentful does not validate their structure. The expected shapes are enforced by the codebase only. See the relevant models in `nodes.py`.

---

## Richtext Node Types

| Node Type | Description |
|-----------|-------------|
| `document` | Root container |
| `text` | Leaf node with `value` and `marks` |
| `paragraph` | Text container |
| `heading-1` to `heading-6` | Headings |
| `unordered-list` | Bullet list |
| `ordered-list` | Numbered list |
| `list-item` | List item |
| `table` | Table container |
| `table-row` | Table row |
| `table-cell` | Table cell |
| `hyperlink` | Inline link (`data.uri`) |
| `blockquote` | Quote block |
| `embedded-entry-block` | Embedded entry (`data.target.sys.id`) |

**Mark types:** `bold`, `italic`, `underline`, `code`

---

## Technical Reference

**Contentful API:**
- Space ID: `qpn1gztbusu2`
- Environment: `master`
- Using Content Management API (CMA)
- Token in SSM: `/audible-toolkit/staging/contentful_token`
