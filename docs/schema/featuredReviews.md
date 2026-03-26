# `featuredReviews` — [UI] Featured Reviews

**Display field:** `None`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `entryName` | Symbol | ✓ |  | {"unique": true} |
| `image` | Link<Asset> |  |  |  |
| `title` | Symbol |  |  |  |
| `copy` | Text | ✓ |  |  |
| `reference` | Link<Entry> |  |  | links to: `post`, `audibleLink`, `asin` |
