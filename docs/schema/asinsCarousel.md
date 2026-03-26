# `asinsCarousel` — [UI] ASINS Carousel

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `title` | Symbol |  |  |  |
| `subtitle` | Symbol |  |  |  |
| `cmsLabel` | Symbol |  |  |  |
| `itemsPerSlide` | Integer |  | `3` | one of: `3`, `4` |
| `jumplink` | Symbol |  |  |  |
| `copy` | Text |  |  |  |
| `ctaText` | Symbol |  |  |  |
| `ctaUrl` | Symbol |  |  |  |
| `asins` | Array<Link<Entry>> | ✓ |  | size: 4–28; links to: `asin` |
| `customSummaries` | Object |  |  |  |
| `options` | Array<Symbol> |  |  | one of: `Enable custom summaries`, `Hide summaries`, `Hide audiobooks metadata`, `Hide titles` |
| `customStyles` | Array<Link<Entry>> |  |  | links to: `customStyle` |
