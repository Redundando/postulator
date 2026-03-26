# `asinsList` — [UI] ASIN Lists

Lists of ASIN featured in Posts and content pages

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol |  |  |  |
| `title` | Symbol | ✓ |  |  |
| `copy` | Symbol |  |  |  |
| `jumplink` | Symbol |  |  |  |
| `playerType` | Symbol | ✓ | `Cover` | one of: `None`, `Cover`, `Simple` |
| `asinsPerRow` | Number | ✓ | `1` | one of: `1`, `3`, `4`, `5` |
| `filtersLabel` | Symbol |  |  |  |
| `filters` | Array<Symbol> |  |  | {"prohibitRegexp": {"pattern": "^all$", "flags": "i"}, "message": "All is default filter and added by default"} |
| `descriptions` | Symbol |  | `Full` | one of: `None`, `Full`, `Short`, `Custom` |
| `asinDescriptions` | Object |  |  |  |
| `asins` | Array<Link<Entry>> |  |  | links to: `asin` |
| `layout` | Symbol |  | `2024` | one of: `2024`, `2025-variant-1`, `2025-variant-2`, `2025-variant-3`, `2025-variant-4` |
| `options` | Array<Symbol> |  |  | one of: `Hide audiobooks titles`, `Hide author names`, `Hide summaries`, `Enable filters`, `Hide Series`, `Hide cta`, `Move cta below the sample button`, `Hide list title` |
| `nt_experiences` | Array<Link<Entry>> |  |  | links to: `nt_experience` |
