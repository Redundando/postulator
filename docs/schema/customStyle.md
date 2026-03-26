# `customStyle` — [UI] Custom Style

Content type for storing CSS custom styles

**Display field:** `name`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `name` | Symbol | ✓ |  |  |
| `css` | Text | ✓ |  | regexp: `^[\s\S]*$` — Must be valid CSS |
| `description` | Text |  |  |  |
