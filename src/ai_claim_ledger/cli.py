from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import STATUSES, load_ledger, render_markdown, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a review checklist from supplied AI claims."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--status", action="append", choices=sorted(STATUSES))
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = report(load_ledger(args.input), set(args.status or []))
        rendered = (
            json.dumps(result, indent=2, ensure_ascii=False) + "\n"
            if args.format == "json"
            else render_markdown(result)
        )
        if args.output:
            if args.output.exists():
                raise ValueError(f"output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
