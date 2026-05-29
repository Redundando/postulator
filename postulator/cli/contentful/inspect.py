"""Contentful inspect/dev commands — entry, content-type, content-types, schema."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .._auth import add_auth_args, client_from_args
from .._output import add_output_args, write_output


def register_inspect_commands(sub: argparse._SubParsersAction) -> None:
    """Register low-level inspection subcommands."""

    # --- entry ---
    p = sub.add_parser("entry", help="Dump a single Contentful entry as JSON")
    p.add_argument("entry_id", help="Contentful entry ID")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_entry)

    # --- content-type ---
    p = sub.add_parser("content-type", help="Dump a Contentful content type definition as JSON")
    p.add_argument("content_type_id", help="Content type ID")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_content_type)

    # --- content-types ---
    p = sub.add_parser("content-types", help="List all Contentful content types as JSON")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_content_types)

    # --- schema ---
    p = sub.add_parser("schema", help="Fetch all content types and write markdown docs")
    p.add_argument(
        "--output-schema-dir",
        default=os.path.join("docs", "schema"),
        help="Output directory for schema docs (default: docs/schema)",
    )
    add_auth_args(p)
    p.set_defaults(handler=_cmd_schema)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _cmd_entry(args: argparse.Namespace) -> None:
    """Dump a single entry as JSON."""
    async with client_from_args(args) as client:
        data = await client.get_entry(args.entry_id)

    result = json.dumps(data, indent=2, ensure_ascii=False)
    # Set format for output helper
    args.format = "json"
    write_output(result, args, f"entry_{args.entry_id}")


async def _cmd_content_type(args: argparse.Namespace) -> None:
    """Dump a content type definition as JSON."""
    async with client_from_args(args) as client:
        data = await client.get_content_type(args.content_type_id)

    result = json.dumps(data, indent=2, ensure_ascii=False)
    args.format = "json"
    write_output(result, args, f"content-type_{args.content_type_id}")


async def _cmd_content_types(args: argparse.Namespace) -> None:
    """List all content types as JSON."""
    async with client_from_args(args) as client:
        resp = await client._request(
            "get", f"{client._base_url}/content_types", params={"limit": 200},
        )
        resp.raise_for_status()
        data = [
            {"id": ct["sys"]["id"], "name": ct.get("name"), "fields": [f["id"] for f in ct.get("fields", [])]}
            for ct in resp.json().get("items", [])
        ]

    result = json.dumps(data, indent=2, ensure_ascii=False)
    args.format = "json"
    write_output(result, args, "content-types")


async def _cmd_schema(args: argparse.Namespace) -> None:
    """Fetch all content types and write markdown schema docs."""
    output_dir = args.output_schema_dir

    async with client_from_args(args) as client:
        resp = await client._request(
            "get", f"{client._base_url}/content_types", params={"limit": 200},
        )
        resp.raise_for_status()
        content_types = resp.json().get("items", [])

    os.makedirs(output_dir, exist_ok=True)

    for ct in content_types:
        ct_id = ct["sys"]["id"]
        path = os.path.join(output_dir, f"{ct_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(_content_type_to_md(ct))
        print(f"  wrote {ct_id}.md", file=sys.stderr)

    index_path = os.path.join(output_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(_index_to_md(content_types))
    print(f"  wrote index.md", file=sys.stderr)
    print(f"\nDone. {len(content_types)} content types written to {output_dir}/", file=sys.stderr)


# ---------------------------------------------------------------------------
# Schema markdown helpers
# ---------------------------------------------------------------------------

def _validation_summary(validations: list) -> str:
    parts: list[str] = []
    for v in validations:
        if "in" in v:
            parts.append("one of: " + ", ".join(f"`{x}`" for x in v["in"]))
        elif "regexp" in v:
            msg = v.get("message", "")
            parts.append(f"regexp: `{v['regexp']['pattern']}`" + (f" — {msg}" if msg else ""))
        elif "linkContentType" in v:
            parts.append("links to: " + ", ".join(f"`{x}`" for x in v["linkContentType"]))
        elif "size" in v:
            s = v["size"]
            parts.append(f"size: {s.get('min', '?')}–{s.get('max', '?')}")
        else:
            parts.append(json.dumps(v))
    return "; ".join(parts)


def _field_type(field: dict) -> str:
    t = field["type"]
    if t == "Link":
        return f"Link<{field.get('linkType', '?')}>"
    if t == "Array":
        items = field.get("items", {})
        it = items.get("type", "?")
        if it == "Link":
            return f"Array<Link<{items.get('linkType', '?')}>>"
        return f"Array<{it}>"
    return t


def _content_type_to_md(ct: dict) -> str:
    ct_id = ct["sys"]["id"]
    name = ct.get("name", ct_id)
    description = ct.get("description", "")
    fields = ct.get("fields", [])

    lines = [f"# `{ct_id}` — {name}", ""]
    if description:
        lines += [description, ""]
    lines += [
        f"**Display field:** `{ct.get('displayField', 'n/a')}`",
        "",
        "## Fields",
        "",
        "| Field ID | Type | Required | Default | Validations |",
        "|----------|------|----------|---------|-------------|",
    ]
    for f in fields:
        if f.get("omitted"):
            continue
        ftype = _field_type(f)
        required = "✓" if f.get("required") else ""
        default = ""
        if "defaultValue" in f:
            dv = f["defaultValue"].get("en-US", "")
            default = f"`{dv}`"
        validations = f.get("validations", [])
        if f.get("type") == "Array":
            validations = validations + f.get("items", {}).get("validations", [])
        val_str = _validation_summary(validations)
        lines.append(f"| `{f['id']}` | {ftype} | {required} | {default} | {val_str} |")

    return "\n".join(lines) + "\n"


def _index_to_md(content_types: list) -> str:
    lines = [
        "# Contentful Content Types",
        "",
        "Auto-generated. Run `postulator contentful schema` to refresh.",
        "",
        "| ID | Name | Fields |",
        "|----|------|--------|",
    ]
    for ct in sorted(content_types, key=lambda x: x["sys"]["id"]):
        ct_id = ct["sys"]["id"]
        name = ct.get("name", ct_id)
        field_count = len([f for f in ct.get("fields", []) if not f.get("omitted")])
        lines.append(f"| [`{ct_id}`](./{ct_id}.md) | {name} | {field_count} |")
    return "\n".join(lines) + "\n"
