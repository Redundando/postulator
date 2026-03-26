# `typography` — Component: Typography

A text block with customizable alignment (Left, Center, Right), designed to be embedded within Rich Text fields.

**Display field:** `name`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `name` | Symbol | ✓ |  |  |
| `alignment` | Symbol | ✓ |  | one of: `Left`, `Center`, `Right` |
| `content` | RichText |  |  | {"enabledNodeTypes": ["heading-1", "heading-2", "heading-3", "heading-4", "heading-5", "heading-6", "ordered-list", "unordered-list", "hr", "blockquote", "table"]}; {"enabledMarks": ["bold", "italic", "underline", "code", "superscript", "subscript"]} |
