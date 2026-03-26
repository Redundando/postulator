# `interview` — [UI] Inline Audio

Small audio player within Posts content

**Display field:** `title`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `title` | Symbol | ✓ |  |  |
| `description` | Symbol |  |  |  |
| `extraDescription` | Symbol |  |  |  |
| `audioURL` | Link<Asset> | ✓ |  | {"linkMimetypeGroup": ["audio"]} |
| `linkURL` | Symbol |  |  | regexp: `^(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?$` |
| `thumbnailURL` | Symbol | ✓ |  | regexp: `^(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?$` |
