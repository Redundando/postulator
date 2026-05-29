"""Credential resolution for Contentful CLI commands.

Precedence: CLI flags > environment variables.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

# Load .env from cwd if present (user's project, not the package)
load_dotenv()


def add_auth_args(parser: argparse.ArgumentParser) -> None:
    """Add --space-id, --token, --environment flags to a parser."""
    group = parser.add_argument_group("authentication")
    group.add_argument(
        "--space-id",
        default=None,
        help="Contentful space ID (env: CONTENTFUL_SPACE_ID)",
    )
    group.add_argument(
        "--token",
        default=None,
        help="Contentful CMA token (env: CONTENTFUL_TOKEN)",
    )
    group.add_argument(
        "--environment",
        default=None,
        help="Contentful environment (env: CONTENTFUL_ENVIRONMENT, default: master)",
    )


def client_from_args(args: argparse.Namespace):
    """Create a ContentfulClient from CLI args + env vars.

    Returns an async context manager (use with `async with`).
    """
    from ..adapters.contentful import ContentfulClient

    space_id = args.space_id or os.environ.get("CONTENTFUL_SPACE_ID")
    token = args.token or os.environ.get("CONTENTFUL_TOKEN")
    environment = args.environment or os.environ.get("CONTENTFUL_ENVIRONMENT", "master")

    if not space_id or not token:
        sys.exit(
            "Error: --space-id and --token are required "
            "(or set CONTENTFUL_SPACE_ID / CONTENTFUL_TOKEN env vars)."
        )

    return ContentfulClient(space_id=space_id, environment=environment, token=token)
