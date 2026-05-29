"""Contentful post commands — list-posts, read-post, find."""

from __future__ import annotations

import argparse

from .._auth import add_auth_args, client_from_args
from .._output import add_output_args, write_output
from .._formatters import (
    format_list_csv,
    format_list_json,
    format_list_markdown,
    format_post_markdown,
    format_post_json,
)


def register_post_commands(sub: argparse._SubParsersAction) -> None:
    """Register list-posts, read-post, and find subcommands."""

    # --- list-posts ---
    p = sub.add_parser("list-posts", help="List posts (filterable by locale, author, tag)")
    p.add_argument("--locale", default=None, help="BCP-47 locale (e.g. fr-FR, en-GB, it-IT)")
    p.add_argument("--author", default=None, help="Filter by author slug")
    p.add_argument("--tag", default=None, help="Filter by tag slug")
    p.add_argument("--slug", default=None, help="Filter by slug pattern (substring match, e.g. 'genre-')")
    p.add_argument("--limit", type=int, default=10, help="Max posts to return (default: 10)")
    p.add_argument("--format", choices=["csv", "json", "markdown"], default="csv", help="Output format (default: csv)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_list_posts)

    # --- read-post ---
    p = sub.add_parser("read-post", help="Read a full post by entry ID")
    p.add_argument("entry_id", help="Contentful entry ID")
    p.add_argument("--locale", default="en-US", help="Locale for reading (default: en-US)")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format (default: markdown)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_read_post)

    # --- find ---
    p = sub.add_parser("find", help="Find a post or category by slug")
    p.add_argument("slug", help="Post or category slug")
    p.add_argument("--locale", required=True, help="BCP-47 locale (required)")
    p.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    add_auth_args(p)
    add_output_args(p)
    p.set_defaults(handler=_cmd_find)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _cmd_list_posts(args: argparse.Namespace) -> None:
    """List posts with optional filters."""
    import sys
    from ...marketplace import locale_to_country_code
    from ...adapters.contentful import ContentfulAdapter

    if not args.locale:
        sys.exit("Error: --locale is required for list-posts.")

    try:
        country_code = locale_to_country_code(args.locale)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    filters: dict = {"fields.countryCode": country_code}

    async with client_from_args(args) as client:
        # If filtering by author, resolve author entry first
        if args.author:
            author_entries = await client.find_entries(
                "author",
                {"fields.slug": args.author, "fields.countryCode": country_code},
            )
            if not author_entries:
                sys.exit(f"Error: Author '{args.author}' not found in {args.locale}.")
            author_id = author_entries[0]["sys"]["id"]
            filters["fields.authors.sys.id"] = author_id

        # If filtering by tag, resolve tag entry first
        if args.tag:
            tag_entries = await client.find_entries(
                "tag",
                {"fields.slug": args.tag, "fields.countryCode": country_code},
            )
            if not tag_entries:
                sys.exit(f"Error: Tag '{args.tag}' not found in {args.locale}.")
            tag_id = tag_entries[0]["sys"]["id"]
            filters["fields.tags.sys.id"] = tag_id

        # If filtering by slug pattern (substring match)
        if args.slug:
            filters["fields.slug[match]"] = args.slug

        # Paginate through results in batches of 200 (Contentful's max per request)
        batch_size = 200
        entries: list[dict] = []
        skip = 0
        while len(entries) < args.limit:
            page_limit = min(batch_size, args.limit - len(entries))
            params = {
                "content_type": "post",
                "limit": page_limit,
                "skip": skip,
                "order": "-fields.date",
                **filters,
            }
            resp = await client._request("get", f"{client._base_url}/entries", params=params)
            resp.raise_for_status()
            data = resp.json()
            page = data.get("items", [])
            entries.extend(page)
            total = data.get("total", 0)
            if not page or len(entries) >= total:
                break
            skip += len(page)

    # Extract summary data
    posts = []
    for entry in entries:
        fields = entry.get("fields", {})
        # Contentful CMA stores fields with locale keys
        locale_key = "en-US"  # CMA always uses en-US as the locale key
        posts.append({
            "entry_id": entry["sys"]["id"],
            "slug": fields.get("slug", {}).get(locale_key, ""),
            "title": fields.get("title", {}).get(locale_key, ""),
            "date": fields.get("date", {}).get(locale_key, ""),
        })

    if not posts:
        print(f"No posts found for locale '{args.locale}'.")
        return

    # Format
    fieldnames = ["entry_id", "slug", "title", "date"]
    if args.format == "csv":
        result = format_list_csv(posts, fieldnames)
    elif args.format == "json":
        result = format_list_json(posts)
    else:
        result = format_list_markdown(posts, fieldnames)

    # Auto-name parts
    auto_name = f"list-posts_{args.locale}"
    if args.author:
        auto_name += f"_{args.author}"
    if args.tag:
        auto_name += f"_{args.tag}"
    if args.slug:
        auto_name += f"_{args.slug}"

    write_output(result, args, auto_name)


async def _cmd_read_post(args: argparse.Namespace) -> None:
    """Read a full post by entry ID."""
    from ...adapters.contentful import ContentfulAdapter

    async with client_from_args(args) as client:
        adapter = ContentfulAdapter(client)
        post = await adapter.read(args.entry_id, locale=args.locale)

    if args.format == "json":
        result = format_post_json(post)
    else:
        result = format_post_markdown(post)

    write_output(result, args, f"read-post_{args.entry_id}")


async def _cmd_find(args: argparse.Namespace) -> None:
    """Find a post or category by slug."""
    import json
    from ...adapters.contentful import ContentfulAdapter

    async with client_from_args(args) as client:
        adapter = ContentfulAdapter(client)
        entry = await adapter.find_entry_by_slug(args.slug, args.locale)

    if not entry:
        print(f"No entry found with slug '{args.slug}' in locale '{args.locale}'.")
        return

    if args.format == "json":
        result = json.dumps(entry, indent=2, ensure_ascii=False, default=str)
    else:
        # Simple markdown summary for found entries
        fields = entry.get("fields", {})
        locale_key = "en-US"
        lines = [
            f"# {fields.get('title', {}).get(locale_key, fields.get('slug', {}).get(locale_key, 'Unknown'))}",
            "",
            f"- **Entry ID:** {entry['sys']['id']}",
            f"- **Content Type:** {entry['sys'].get('contentType', {}).get('sys', {}).get('id', 'unknown')}",
            f"- **Slug:** {fields.get('slug', {}).get(locale_key, '')}",
        ]
        date_val = fields.get("date", {}).get(locale_key)
        if date_val:
            lines.append(f"- **Date:** {date_val}")
        result = "\n".join(lines)

    write_output(result, args, f"find_{args.slug}")
