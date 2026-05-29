"""Output handling — write to stdout, explicit file, or auto-named file in a directory."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date


def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add -o/--output and --output-dir flags to a parser."""
    group = parser.add_argument_group("output")
    group.add_argument(
        "-o", "--output",
        default=None,
        help="Write output to an explicit file path",
    )
    group.add_argument(
        "--output-dir",
        default=None,
        help="Auto-generate filename and write to this directory",
    )


def write_output(content: str, args: argparse.Namespace, auto_name: str) -> None:
    """Write content to the appropriate destination.

    Args:
        content: The formatted string to output.
        args: Parsed CLI args (expects .output and .output_dir attributes).
        auto_name: Base name for auto-generated files (e.g. 'list-posts_fr-FR').
                   Date and extension will be appended.
    """
    fmt = getattr(args, "format", "csv")
    ext = _extension_for_format(fmt)

    if args.output:
        path = args.output
        _write_file(path, content)
    elif args.output_dir:
        filename = f"{auto_name}_{date.today().isoformat()}.{ext}"
        path = os.path.join(args.output_dir, filename)
        os.makedirs(args.output_dir, exist_ok=True)
        _write_file(path, content)
    else:
        print(content)


def _write_file(path: str, content: str) -> None:
    """Write content to a file and print confirmation to stderr."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written to {path}", file=sys.stderr)


def _extension_for_format(fmt: str) -> str:
    """Map format name to file extension."""
    return {
        "csv": "csv",
        "json": "json",
        "markdown": "md",
    }.get(fmt, "txt")
