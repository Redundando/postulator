# `tag` — [Page] Tag

Page that displays tag posts and content

**Display field:** `name`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `countryCode` | Symbol | ✓ |  | one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `US`, `ES`, `AU` |
| `name` | Symbol | ✓ |  |  |
| `description` | Symbol |  |  |  |
| `slug` | Symbol | ✓ |  | regexp: `^([a-z0-9-]+)$` — Must only contain letters, numbers or a dash |
| `image` | Link<Asset> |  |  |  |
| `seoSettings` | Link<Entry> |  |  | links to: `seoSettings` |
| `pageSettings` | Link<Entry> |  |  | links to: `pageSettings` |
| `postListLayout` | Symbol |  | `2024` | one of: `2024`, `2025` |
