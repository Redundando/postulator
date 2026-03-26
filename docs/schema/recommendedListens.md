# `recommendedListens` — [UI] Recommended Listens

Used to embed Recommended Listens sections using ASIN references. Recommended listens can be used within Post content or at the bottom

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `title` | Symbol |  |  |  |
| `subtitle` | Symbol |  |  |  |
| `listens` | Array<Link<Entry>> |  |  | links to: `asin` |
| `customCopy` | Object |  |  |  |
| `options` | Array<Symbol> |  |  | one of: `Show Release Date`, `Enable Custom Copy`, `Display Credits`, `Left Align ASIN`, `Without ASINs` |
