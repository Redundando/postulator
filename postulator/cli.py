"""Postulator CLI — inspect Contentful spaces and postulator models.

Usage::

    postulator entry <entry_id> [--space-id …] [--token …] [--environment …]
    postulator content-type <content_type_id> [--space-id …] [--token …] [--environment …]
    postulator content-types [--space-id …] [--token …] [--environment …]
    postulator schema [--output docs/schema] [--space-id …] [--token …] [--environment …]
    postulator models
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Contentful helpers (lazy import to keep `models` command dependency-free)
# ---------------------------------------------------------------------------

def _client_from_args(args: argparse.Namespace):
    from .adapters.contentful import ContentfulClient

    space_id = args.space_id or os.environ.get("CONTENTFUL_SPACE_ID")
    token = args.token or os.environ.get("CONTENTFUL_TOKEN")
    environment = args.environment or os.environ.get("CONTENTFUL_ENVIRONMENT", "master")

    if not space_id or not token:
        sys.exit(
            "Error: --space-id and --token are required "
            "(or set CONTENTFUL_SPACE_ID / CONTENTFUL_TOKEN env vars)."
        )

    return ContentfulClient(space_id=space_id, environment=environment, token=token)


# ---------------------------------------------------------------------------
# Schema markdown generation
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
        "Auto-generated. Run `postulator schema` to refresh.",
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


# ---------------------------------------------------------------------------
# Model schema generation
# ---------------------------------------------------------------------------

def _collect_models() -> dict[str, Any]:
    """Return JSON-serialisable schema dict for all public postulator models."""
    from . import models as m
    from .models import nodes as n

    model_classes = [
        m.Post, m.AuthorRef, m.TagRef, m.SeoMeta, m.Author,
        n.AssetRef, n.LocalAsset,
        n.TextNode, n.HyperlinkNode,
        n.ParagraphNode, n.HeadingNode, n.ListNode, n.ListItemNode,
        n.BlockquoteNode, n.HrNode,
        n.AudiobookAuthor, n.AudiobookNarrator, n.AudiobookSeries,
        n.AudiobookNode, n.AudiobookListItem, n.AudiobookListNode,
        n.AudiobookCarouselNode, n.ContentImageNode,
        n.TableNode, n.TableRowNode, n.TableCellNode,
        n.UnknownNode,
    ]
    return {cls.__name__: cls.model_json_schema() for cls in model_classes}


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

async def _cmd_entry(args: argparse.Namespace) -> None:
    async with _client_from_args(args) as client:
        data = await client.get_entry(args.entry_id)
        print(json.dumps(data, indent=2))


async def _cmd_content_type(args: argparse.Namespace) -> None:
    async with _client_from_args(args) as client:
        data = await client.get_content_type(args.content_type_id)
        print(json.dumps(data, indent=2))


async def _cmd_content_types(args: argparse.Namespace) -> None:
    async with _client_from_args(args) as client:
        resp = await client._request(
            "get", f"{client._base_url}/content_types", params={"limit": 200},
        )
        resp.raise_for_status()
        data = [
            {"id": ct["sys"]["id"], "name": ct.get("name"), "fields": [f["id"] for f in ct.get("fields", [])]}
            for ct in resp.json().get("items", [])
        ]
        print(json.dumps(data, indent=2))


async def _cmd_schema(args: argparse.Namespace) -> None:
    output_dir = args.output

    async with _client_from_args(args) as client:
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


def _cmd_models(_args: argparse.Namespace) -> None:
    print(json.dumps(_collect_models(), indent=2))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--space-id", default=None, help="Contentful space ID (env: CONTENTFUL_SPACE_ID)")
    parser.add_argument("--token", default=None, help="Contentful CMA token (env: CONTENTFUL_TOKEN)")
    parser.add_argument("--environment", default=None, help="Contentful environment (env: CONTENTFUL_ENVIRONMENT, default: master)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="postulator", description="Postulator CLI — inspect Contentful spaces and postulator models.")
    sub = parser.add_subparsers(dest="command")

    # entry
    p = sub.add_parser("entry", help="Dump a single Contentful entry as JSON")
    p.add_argument("entry_id", help="Contentful entry ID")
    _add_auth_args(p)

    # content-type
    p = sub.add_parser("content-type", help="Dump a Contentful content type definition as JSON")
    p.add_argument("content_type_id", help="Content type ID")
    _add_auth_args(p)

    # content-types
    p = sub.add_parser("content-types", help="List all Contentful content types as JSON")
    _add_auth_args(p)

    # schema
    p = sub.add_parser("schema", help="Fetch all content types and write markdown files")
    p.add_argument("--output", default=os.path.join("docs", "schema"), help="Output directory (default: docs/schema)")
    _add_auth_args(p)

    # models
    sub.add_parser("models", help="Dump all postulator Pydantic model schemas as JSON")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "entry": _cmd_entry,
        "content-type": _cmd_content_type,
        "content-types": _cmd_content_types,
        "schema": _cmd_schema,
        "models": _cmd_models,
    }

    handler = handlers[args.command]

    if asyncio.iscoroutinefunction(handler):
        try:
            asyncio.run(handler(args))
        except Exception as exc:
            sys.exit(f"Error: {exc}")
    else:
        handler(args)


if __name__ == "__main__":
    main()
