# `fullBleedHero` — [UI] Full Bleed Hero

Full width background image section displayed on top of the page

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol | ✓ |  |  |
| `title` | Symbol |  |  |  |
| `subtitle` | Symbol |  |  |  |
| `image` | Link<Asset> |  |  |  |
| `mobileImage` | Link<Asset> |  |  |  |
| `reference` | Link<Entry> |  |  | links to: `post`, `audibleLink` |
| `sectionSlug` | Symbol |  |  |  |
| `inline` | Boolean |  |  |  |
| `titleOnTop` | Boolean |  |  |  |
| `layout` | Symbol |  |  | one of: `full-length`, `new-design` |
| `ctaText` | Symbol |  |  |  |
| `customStyles` | Array<Link<Entry>> |  |  | links to: `customStyle` |
| `nt_experiences` | Array<Link<Entry>> |  |  | links to: `nt_experience` |
| `backgroundColor` | Symbol |  |  |  |
| `invertRows` | Boolean |  |  |  |
