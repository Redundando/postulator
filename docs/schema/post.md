# `post` — [Page] Post

Page that displays post content and its related posts

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `countryCode` | Symbol | ✓ |  | one of: `DE`, `UK`, `FR`, `IT`, `CA_EN`, `CA_FR`, `ES`, `US`, `AU` |
| `slug` | Symbol | ✓ |  |  |
| `title` | Symbol | ✓ |  |  |
| `customRecommendedTitle` | Symbol |  |  |  |
| `introduction` | Text |  |  |  |
| `hideFromBlogFeed` | Boolean |  | `False` |  |
| `date` | Date | ✓ |  |  |
| `updateDate` | Date |  |  |  |
| `hidePublishDate` | Boolean |  | `False` |  |
| `image` | Link<Asset> |  |  |  |
| `hideHeroImage` | Boolean |  | `False` |  |
| `interviewAudio` | Link<Asset> |  |  | {"linkMimetypeGroup": ["audio"]} |
| `tags` | Array<Link<Entry>> |  |  | links to: `tag` |
| `category` | Link<Entry> |  |  | links to: `category` |
| `authors` | Array<Link<Entry>> |  |  | links to: `author` |
| `seoSettings` | Link<Entry> |  |  | links to: `seoSettings` |
| `content` | RichText |  |  | {"enabledMarks": ["bold", "italic", "underline", "code", "superscript", "subscript"], "message": "Only bold, italic, underline, code, superscript, and subscript marks are allowed"}; {"enabledNodeTypes": ["heading-1", "heading-2", "heading-3", "heading-4", "heading-5", "heading-6", "ordered-list", "unordered-list", "hr", "blockquote", "embedded-entry-block", "embedded-asset-block", "hyperlink", "entry-hyperlink", "asset-hyperlink", "table"], "message": "Only heading 1, heading 2, heading 3, heading 4, heading 5, heading 6, ordered list, unordered list, horizontal rule, quote, block entry, asset, link to Url, link to entry, link to asset, and table nodes are allowed"}; {"nodes": {"entry-hyperlink": [{"linkContentType": ["asin"], "message": null}]}} |
| `heroSection` | Link<Entry> |  |  | links to: `fullBleedHero` |
| `relatedPosts` | Array<Link<Entry>> |  |  | links to: `post`, `audibleLink`, `category`, `tag` |
| `recommendedListensEntry` | Link<Entry> |  |  | links to: `recommendedListens` |
| `hideFreeTrial` | Boolean |  | `False` |  |
| `uniqueKey` | Symbol |  |  |  |
