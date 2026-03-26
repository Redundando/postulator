# `pageSettings` — [Block] Page UI Settings

**Display field:** `label`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `label` | Symbol |  |  |  |
| `featuredPost` | Link<Entry> |  |  | links to: `post`, `category`, `tag` |
| `uiSections` | Array<Link<Entry>> |  |  | links to: `asinsCarousel`, `carousel`, `fullBleedHero`, `asinsList`, `contentImage`, `uiCtaSection`, `uiCustomCopy`, `recommendedListens`, `uiEditorsCarousel`, `uiPageRecommendedContent`, `uiHeadingSection`, `youtubeVideo`, `uiContentGrid`, `uiVideo` |
| `uiSectionsBelowFeed` | Array<Link<Entry>> |  |  | links to: `asinsCarousel`, `carousel`, `fullBleedHero`, `asinsList`, `uiCtaSection`, `uiCustomCopy`, `recommendedListens`, `uiEditorsCarousel`, `uiPageRecommendedContent`, `uiHeadingSection`, `youtubeVideo`, `contentImage`, `uiContentGrid`, `uiVideo` |
| `uiSkin` | Symbol |  |  | one of: `Content on Top`, `Authors`, `BOTY`, `Newsletter Hub`, `Hub Page Layout` |
| `optionalContent` | RichText |  |  | {"enabledMarks": ["bold", "italic", "underline", "code"], "message": "Only bold, italic, underline, and code marks are allowed"}; {"enabledNodeTypes": ["heading-1", "heading-2", "heading-3", "heading-4", "heading-5", "heading-6", "ordered-list", "unordered-list", "hr", "blockquote", "embedded-entry-block", "embedded-asset-block", "hyperlink", "entry-hyperlink", "asset-hyperlink", "embedded-entry-inline", "table"], "message": "Only heading 1, heading 2, heading 3, heading 4, heading 5, heading 6, ordered list, unordered list, horizontal rule, quote, block entry, asset, link to Url, link to entry, link to asset, inline entry, and table nodes are allowed"}; {"nodes": {"embedded-entry-block": [{"linkContentType": ["audiobookModule", "moduleAudio", "moduleCta", "galleryModule", "moduleImage", "moduleOpinary", "moduleQuote", "moduleTable", "moduleTypeform", "moduleYoutube", "asinsList", "asinsCarousel"]}], "embedded-entry-inline": [{"linkContentType": ["nt_mergetag"], "message": null}]}} |
| `nt_experiences` | Array<Link<Entry>> |  |  | links to: `nt_experience` |
