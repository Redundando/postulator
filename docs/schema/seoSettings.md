# `seoSettings` — [Metadata] SEO Settings

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol | ✓ |  |  |
| `slugReplacement` | Symbol |  |  |  |
| `slugRedirect` | Symbol |  |  |  |
| `noIndex` | Boolean |  | `False` |  |
| `metaTitle` | Symbol |  |  |  |
| `metaDescription` | Text |  |  |  |
| `openGraphTitle` | Symbol |  |  |  |
| `openGraphDescription` | Text |  |  |  |
| `openGraphImage` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"]} |
| `similarContent` | Array<Link<Entry>> |  |  | size: ?–1; links to: `audibleLink` |
| `externalLinksSourceCode` | Symbol |  |  |  |
| `schemaType` | Symbol |  |  | one of: `Article`, `News Article`, `Video` |
| `jsonLd` | Link<Entry> |  |  | links to: `jsonLd` |
