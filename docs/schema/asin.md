# `asin` — [Product] ASIN

Audible Catalog Audiobooks, Podcasts & Shows

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `asin` | Symbol | ✓ |  |  |
| `label` | Symbol | ✓ |  |  |
| `title` | Symbol | ✓ |  |  |
| `marketplace` | Symbol | ✓ |  | one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `US`, `ES`, `AU` |
| `authors` | Object |  |  |  |
| `narrators` | Object |  |  |  |
| `series` | Object |  |  |  |
| `sample` | Symbol |  |  |  |
| `pdp` | Symbol |  |  |  |
| `cover` | Symbol |  |  |  |
| `assetCoverImage` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"]} |
| `summary` | Text |  |  |  |
| `releaseDate` | Symbol |  |  | regexp: `^\d{4}-\d{2}-\d{2}$` |
| `type` | Symbol |  |  |  |
| `deliveryType` | Symbol |  |  |  |
| `uniqueKey` | Symbol | ✓ |  | {"unique": true} |
| `borderOptions` | Array<Symbol> |  |  | one of: `Show border`, `Show shadow` |
