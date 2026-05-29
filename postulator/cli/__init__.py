"""Postulator CLI — manage content across CMS backends.

Usage::

    postulator contentful list-posts --locale fr-FR
    postulator contentful read-post <entry_id>
    postulator contentful find <slug> --locale fr-FR
    postulator models
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .contentful import register_contentful_commands


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="postulator",
        description="Postulator CLI — manage content across CMS backends.",
    )
    sub = parser.add_subparsers(dest="backend")

    # --- CMS backends ---
    register_contentful_commands(sub)

    # --- Top-level commands (CMS-agnostic) ---
    sub.add_parser("models", help="Dump all postulator Pydantic model schemas as JSON")

    return parser


def main() -> None:
    # Force UTF-8 output on Windows
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = _build_parser()
    args = parser.parse_args()

    if args.backend is None:
        parser.print_help()
        sys.exit(1)

    if args.backend == "models":
        from ._models import cmd_models
        cmd_models(args)
        return

    # Dispatch to the handler set on the subparser
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    if asyncio.iscoroutinefunction(handler):
        try:
            asyncio.run(handler(args))
        except KeyboardInterrupt:
            sys.exit(130)
        except SystemExit:
            raise
        except Exception as exc:
            sys.exit(f"Error: {exc}")
    else:
        try:
            handler(args)
        except SystemExit:
            raise
        except Exception as exc:
            sys.exit(f"Error: {exc}")


if __name__ == "__main__":
    main()
