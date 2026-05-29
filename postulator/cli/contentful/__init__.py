"""Contentful CLI subcommand group — registers all contentful commands."""

from __future__ import annotations

import argparse

from .posts import register_post_commands
from .authors import register_author_commands
from .tags import register_tag_commands
from .inspect import register_inspect_commands


def register_contentful_commands(parent_subparsers: argparse._SubParsersAction) -> None:
    """Register the 'contentful' command group with all its subcommands."""
    contentful_parser = parent_subparsers.add_parser(
        "contentful",
        help="Contentful CMS commands",
        description="Manage content in Contentful spaces.",
    )
    sub = contentful_parser.add_subparsers(dest="contentful_command")

    register_post_commands(sub)
    register_author_commands(sub)
    register_tag_commands(sub)
    register_inspect_commands(sub)

    # Set a default handler that prints help if no subcommand given
    contentful_parser.set_defaults(handler=lambda _: contentful_parser.print_help())
