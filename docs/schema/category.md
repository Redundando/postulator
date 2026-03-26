# `category` — [Page] Category

Page that displays category posts and content

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `countryCode` | Symbol | ✓ |  | one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `ES`, `US`, `AU` |
| `title` | Symbol | ✓ |  |  |
| `slug` | Symbol | ✓ |  | regexp: `^([a-z0-9-]+)$` — Must only contain letters, numbers or a dash |
| `description` | Symbol |  |  |  |
| `image` | Link<Asset> |  |  |  |
| `pageSettings` | Link<Entry> |  |  | links to: `pageSettings` |
| `seoSettings` | Link<Entry> |  |  | links to: `seoSettings` |
| `hideAuthor` | Boolean |  | `False` |  |
| `layout` | Symbol |  | `2024` | one of: `2024`, `2025` |
