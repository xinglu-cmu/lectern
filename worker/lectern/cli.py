"""`lectern` — the command-line front door (DESIGN §6).

    lectern scan DOC [--json] [--no-llm] [--full-text] [--model MODEL]

Exit codes: 0 analysis printed; 1 the file could not be read or analyzed;
2 usage error. Code 3 (findings above a threshold, `--fail-on`) is reserved for
week 3 alongside `lectern clean`.
"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

import lectern
from lectern.converters import UnsupportedFormat
from lectern.llm import DEFAULT_MODEL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lectern",
        description="Know what your AI is reading: scan a document for its overview, zone map "
        "and AI-directed content before handing it to an AI tool.",
    )
    parser.add_argument("--version", action="version", version=f"lectern {lectern.__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log pipeline details")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="analyze a document and print the report")
    scan.add_argument("doc", help="PDF, DOCX, HTML, PPTX, Markdown or text file")
    scan.add_argument("--json", action="store_true", help="print the full analysis as JSON")
    scan.add_argument(
        "--no-llm",
        action="store_true",
        help="offline: heuristic zoning and pattern detectors only, no overview",
    )
    scan.add_argument("--full-text", action="store_true", help="also print every segment's text")
    scan.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Claude model (default {DEFAULT_MODEL})"
    )
    scan.set_defaults(func=cmd_scan)
    return parser


def cmd_scan(args: argparse.Namespace) -> int:
    from lectern.pipeline import analyze
    from lectern.report import render

    err = Console(stderr=True)
    try:
        analysis = analyze(args.doc, use_llm=not args.no_llm, model=args.model)
    except FileNotFoundError:
        err.print(f"[red]error:[/] file not found: {args.doc}")
        return 1
    except UnsupportedFormat as exc:
        err.print(f"[red]error:[/] {exc}")
        return 1
    except Exception as exc:  # a converter blew up on this file: say so, don't traceback
        if args.verbose:
            raise
        err.print(f"[red]error:[/] could not analyze {args.doc}: {exc.__class__.__name__}: {exc}")
        err.print("[dim]run with -v for the full traceback[/]")
        return 1

    if args.json:
        sys.stdout.write(analysis.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        render(analysis, Console(), full_text=args.full_text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
