# `nt_experience` — Ninetailed Experience

Ninetailed Experience

**Display field:** `nt_name`

## Fields

| Field ID | Type | Required | Default | Validations |
|----------|------|----------|---------|-------------|
| `nt_name` | Symbol | ✓ |  | {"unique": true} |
| `nt_description` | Text |  |  |  |
| `nt_type` | Symbol | ✓ |  | one of: `nt_experiment`, `nt_personalization` |
| `nt_config` | Object | ✓ |  |  |
| `nt_audience` | Link<Entry> |  |  | links to: `nt_audience` |
| `nt_variants` | Array<Link<Entry>> |  |  |  |
| `nt_experience_id` | Symbol |  |  | {"unique": true} |
| `nt_metadata` | Object |  |  |  |
