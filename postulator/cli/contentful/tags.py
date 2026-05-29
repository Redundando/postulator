"""Contentful tag commands — list-tags."""

from __future__ import annotations

import argparse

from .._auth import add_auth_args, client_from_args
from .._output import add_output_args, write_output
from .._formatters import (
    format_list_csv,
    format_list_json,
    format_list_markdown,
)


def register_tag_commands(sub: argparse._SubParsersAction) -> None:
    """Register list-tags subcommand."""

    p = sub.add_parser("list-tags", help="List tags for a locale/market")
    p.add_argument("--locale", required=True, help="BCP-47 locale (e.g. fr-FR, en-GB)")
    p.add_argument("--format", choices=["csv", "json", "markdown"], default="csv", help="Output format (default: csv)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_list_tags)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _cmd_list_tags(args: argparse.Namespace) -> None:
    """List tags for a given locale."""
    import sys
    from ...marketplace import locale_to_country_code
    from ...adapters.contentful import ContentfulAdapter

    try:
        country_code = locale_to_country_code(args.locale)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    async with client_from_args(args) as client:
        adapter = ContentfulAdapter(client)
        tags = await adapter.list_tags(country_code, locale=args.locale)

    if not tags:
        print(f"No tags found for locale '{args.locale}'.")
        return

    items = [
        {
            "entry_id": t.source_id or "",
            "slug": t.slug,
            "name": t.name,
        }
        for t in tags
    ]

    fieldnames = ["entry_id", "slug", "name"]
    if args.format == "csv":
        result = format_list_csv(items, fieldnames)
    elif args.format == "json":
        result = format_list_json(items)
    else:
        result = format_list_markdown(items, fieldnames)

    write_output(result, args, f"list-tags_{args.locale}")
