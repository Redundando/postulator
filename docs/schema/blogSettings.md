# `blogSettings` — [Config] Blog Site Settings

**Display field:** `countryCode`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `countryCode` | Symbol | ✓ |  | {"unique": true}; one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `US`, `ES`, `AU` |
| `blogNav` | Array<Link<Entry>> |  |  | size: ?–15; links to: `audibleLink` |
| `pageSettings` | Link<Entry> |  |  | links to: `pageSettings` |
| `footer` | Array<Link<Entry>> |  |  | size: ?–25; links to: `audibleLink` |
| `seoSettings` | Link<Entry> |  |  | links to: `seoSettings` |
| `freeTrialModule` | Link<Entry> |  |  | links to: `uiCtaSection` |
| `recommendedContent` | Array<Link<Entry>> |  |  | links to: `post`, `audibleLink`, `category`, `tag` |
