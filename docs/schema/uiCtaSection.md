# `uiCtaSection` — [UI] CTA

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol | ✓ |  |  |
| `ctaText` | Symbol | ✓ |  |  |
| `heading` | Symbol |  |  |  |
| `subheading` | Symbol |  |  |  |
| `topSubheading` | Symbol |  |  |  |
| `image` | Link<Asset> |  |  |  |
| `href` | Symbol | ✓ |  |  |
| `asins` | Array<Link<Entry>> |  |  | size: ?–8; links to: `asin` |
| `uiSkin` | Symbol |  |  | one of: `Rounded`, `quiz` |
