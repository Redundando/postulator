# `uiContentGrid` — [UI] Content Grid

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `title` | Symbol | ✓ |  |  |
| `items` | Array<Link<Entry>> | ✓ |  | size: ?–40; links to: `author`, `audibleLink`, `contentImage` |
| `columns` | Integer |  | `3` | one of: `3`, `4` |
| `showDescriptions` | Boolean |  | `False` |  |
| `showCta` | Boolean |  | `False` |  |
| `ctaText` | Symbol |  | `Text to display in the CTA link` |  |
| `ctaUrl` | Symbol |  |  |  |
| `imageShape` | Symbol |  | `Square` | one of: `Square`, `Rounded` |
| `layout` | Symbol |  | `Bottom text` | one of: `Inside text`, `Bottom text` |
| `customStyles` | Array<Link<Entry>> |  |  | links to: `customStyle` |
| `nt_experiences` | Array<Link<Entry>> |  |  | links to: `nt_experience` |
