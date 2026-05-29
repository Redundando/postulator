"""Contentful author commands — list-authors, read-author."""

from __future__ import annotations

import argparse

from .._auth import add_auth_args, client_from_args
from .._output import add_output_args, write_output
from .._formatters import (
    format_list_csv,
    format_list_json,
    format_list_markdown,
    format_author_markdown,
    format_author_json,
)


def register_author_commands(sub: argparse._SubParsersAction) -> None:
    """Register list-authors and read-author subcommands."""

    # --- list-authors ---
    p = sub.add_parser("list-authors", help="List authors for a locale/market")
    p.add_argument("--locale", required=True, help="BCP-47 locale (e.g. fr-FR, en-GB)")
    p.add_argument("--limit", type=int, default=10, help="Max authors to return (default: 10)")
    p.add_argument("--format", choices=["csv", "json", "markdown"], default="csv", help="Output format (default: csv)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_list_authors)

    # --- read-author ---
    p = sub.add_parser("read-author", help="Read a full author by entry ID")
    p.add_argument("entry_id", help="Contentful entry ID")
    p.add_argument("--locale", default="en-US", help="Locale for reading (default: en-US)")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format (default: markdown)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_read_author)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _cmd_list_authors(args: argparse.Namespace) -> None:
    """List authors for a given locale."""
    import sys
    from ...marketplace import locale_to_country_code
    from ...adapters.contentful import ContentfulAdapter

    try:
        country_code = locale_to_country_code(args.locale)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    async with client_from_args(args) as client:
        adapter = ContentfulAdapter(client)
        authors = await adapter.list_authors(country_code, locale=args.locale)

    # Apply limit
    authors = authors[:args.limit]

    if not authors:
        print(f"No authors found for locale '{args.locale}'.")
        return

    # Build summary dicts
    items = [
        {
            "entry_id": a.source_id or "",
            "slug": a.slug,
            "name": a.name,
            "title": a.title or "",
        }
        for a in authors
    ]

    fieldnames = ["entry_id", "slug", "name", "title"]
    if args.format == "csv":
        result = format_list_csv(items, fieldnames)
    elif args.format == "json":
        result = format_list_json(items)
    else:
        result = format_list_markdown(items, fieldnames)

    write_output(result, args, f"list-authors_{args.locale}")


async def _cmd_read_author(args: argparse.Namespace) -> None:
    """Read a full author by entry ID."""
    from ...adapters.contentful import ContentfulAdapter

    async with client_from_args(args) as client:
        adapter = ContentfulAdapter(client)
        author = await adapter.read_author(args.entry_id, locale=args.locale)

    if args.format == "json":
        result = format_author_json(author)
    else:
        result = format_author_markdown(author)

    write_output(result, args, f"read-author_{args.entry_id}")
