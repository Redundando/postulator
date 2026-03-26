# `author` — [Page] Author

Page that displays author bio, posts and content

**Display field:** `name`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `countryCode` | Symbol | ✓ |  | one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `US`, `ES`, `AU` |
| `name` | Symbol | ✓ |  |  |
| `shortName` | Symbol |  |  |  |
| `title` | Symbol |  |  |  |
| `slug` | Symbol | ✓ |  | regexp: `^([a-z0-9-]+)$` — Must only contain letters, numbers or a dash |
| `bio` | Text |  |  |  |
| `shortBio` | Symbol |  |  |  |
| `genre` | Symbol |  |  |  |
| `picture` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"]} |
| `carouselPicture` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"], "message": "Picture to be used when editors gets added on a carousel"} |
| `excerpt` | Text |  |  |  |
| `postsSectionTitle` | Symbol |  |  |  |
| `pageSettings` | Link<Entry> |  |  | links to: `pageSettings` |
| `seoSettings` | Link<Entry> |  |  | links to: `seoSettings` |
