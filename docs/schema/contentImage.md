# `contentImage` — [UI] Content Styled Image

Styled images within Content

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `title` | Symbol |  |  |  |
| `image` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"]} |
| `href` | Symbol |  |  | regexp: `^(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-/]))?$` — Hyperlink should be in URL format |
| `options` | Array<Symbol> |  |  | one of: `Full width`, `100% width`, `75% width centered`, `50% width centered`, `25% width centered` |
| `alignment` | Symbol |  |  | one of: `Full width`, `100% width`, `75% width centered`, `50% width centered`, `25% width centered` |
| `justify` | Symbol |  |  | one of: `Left`, `Center`, `Right` |
| `size` | Symbol |  |  | one of: `100% width`, `75% width`, `50% width`, `25% width` |
