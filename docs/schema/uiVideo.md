# `uiVideo` — [UI] Video

**Display field:** `entryTitle`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `entryTitle` | Symbol | ✓ |  |  |
| `title` | Symbol |  |  |  |
| `thumbnail` | Link<Asset> |  |  | {"linkMimetypeGroup": ["image"]} |
| `subtitle` | Symbol |  |  |  |
| `videoContent` | Link<Asset> | ✓ |  | {"linkMimetypeGroup": ["video"]} |
| `textAlignment` | Symbol |  | `Center` | one of: `Center`, `Right`, `Left` |
| `autoPlay` | Boolean |  | `False` |  |
