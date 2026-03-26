# `carousel` — [UI] Carousel

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol | ✓ |  |  |
| `title` | Symbol |  |  |  |
| `subtitle` | Symbol |  |  |  |
| `items` | Array<Link<Entry>> |  |  | links to: `post`, `asin`, `audibleLink`, `author`, `carouselSimpleItem`, `fullBleedHero`, `featuredReviews` |
| `jumplink` | Symbol |  |  |  |
| `gradient` | Symbol |  |  | one of: `No gradient`, `Solar`, `Carbon`, `Pewter`, `Sand`, `Slate`, `Blue`, `Sapphire`, `Royal`, `Sky`, `Sunrise`, `Coral` |
| `itemsPerSlide` | Integer |  | `1` | one of: `1`, `3`, `4` |
| `layout` | Symbol |  |  | one of: `2024`, `2025`, `post-carousel`, `fullbleed-carousel`, `featured-reviews-carousel` |
| `customStyles` | Array<Link<Entry>> |  |  | links to: `customStyle` |
