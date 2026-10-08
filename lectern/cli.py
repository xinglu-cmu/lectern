"""`lectern` — the command-line front door (DESIGN §6).

    lectern scan  DOC [--json] [--no-llm | --local [MODEL]] [--full-text] [--fail-on LEVEL]
                      [--model MODEL]
    lectern clean DOC [-o out.md] [--keep Z,Z] [--drop Z,Z] [--interactive]
                      [--no-llm] [--no-report] [--model MODEL]
    lectern brief DOC [-o brief.md] [--keep Z,Z] [--no-llm] [--model MODEL]
    lectern mcp                      (stdio MCP server: scan / clean / brief as tools)
    lectern serve [--port 8765] [--no-browser] [--no-llm]   (review UI on 127.0.0.1)

Exit codes: 0 done; 1 the file could not be read or analyzed; 2 usage error;
3 `scan --fail-on LEVEL` found a finding at or above LEVEL (a CI / ingest gate).
"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

import lectern
from lectern.converters import UnsupportedFormat
from lectern.llm import DEFAULT_MODEL
from lectern.models import Severity, Zone

ZONES = [z.value for z in Zone]


def _local_flag(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--local",
        nargs="?",
        const=True,
        default=False,
        metavar="MODEL",
        help="use a model served on this machine (Ollama at $LECTERN_LOCAL_URL, default "
        "http://127.0.0.1:11434) instead of Claude; optionally name the model",
    )


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
    _local_flag(scan)
    scan.add_argument(
        "--fail-on",
        choices=[s.value for s in Severity],
        help="exit with code 3 if any finding is at or above this severity",
    )
    scan.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Claude model (default {DEFAULT_MODEL})"
    )
    scan.set_defaults(func=cmd_scan)

    clean = sub.add_parser("clean", help="write a clean Markdown copy with only the zones you keep")
    clean.add_argument("doc", help="PDF, DOCX, HTML, PPTX, Markdown or text file")
    clean.add_argument("-o", "--output", help="output file (default: stdout)")
    clean.add_argument(
        "--keep", help="zones to keep, comma-separated (default: task,background,example,unknown)"
    )
    clean.add_argument("--drop", help="zones to drop from the kept set, comma-separated")
    clean.add_argument(
        "--interactive",
        action="store_true",
        help="confirm each zone in the terminal before writing",
    )
    clean.add_argument("--no-llm", action="store_true", help="offline: heuristic zoning only")
    _local_flag(clean)
    clean.add_argument("--no-report", action="store_true", help="omit the removal report footer")
    clean.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Claude model (default {DEFAULT_MODEL})"
    )
    clean.set_defaults(func=cmd_clean)

    brief = sub.add_parser(
        "brief", help="write a one-page brief: what it is, what it asks, what was found"
    )
    brief.add_argument("doc", help="PDF, DOCX, HTML, PPTX, Markdown or text file")
    brief.add_argument("-o", "--output", help="output file (default: stdout)")
    brief.add_argument("--keep", help="zones the clean copy would keep (for the last section)")
    brief.add_argument("--no-llm", action="store_true", help="offline: no model-written half")
    _local_flag(brief)
    brief.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Claude model (default {DEFAULT_MODEL})"
    )
    brief.set_defaults(func=cmd_brief)

    mcp = sub.add_parser(
        "mcp", help="run the MCP server on stdio (for Claude Code, Claude Desktop, agents)"
    )
    mcp.add_argument("--no-llm", action="store_true", help="never call a model from the tools")
    _local_flag(mcp)
    mcp.set_defaults(func=cmd_mcp)

    serve = sub.add_parser(
        "serve", help="open the local review UI in your browser (127.0.0.1 only)"
    )
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--no-browser", action="store_true", help="don't open the browser")
    serve.add_argument("--no-llm", action="store_true", help="never call a model")
    _local_flag(serve)
    serve.add_argument("--model", default=None, help=f"Claude model (default {DEFAULT_MODEL})")
    serve.set_defaults(func=cmd_serve)
    return parser


def _analyze_or_exit(args: argparse.Namespace):
    from lectern.pipeline import analyze

    err = Console(stderr=True)
    try:
        return analyze(args.doc, use_llm=not args.no_llm, model=args.model, local=args.local)
    except FileNotFoundError:
        err.print(f"[red]error:[/] file not found: {args.doc}")
    except UnsupportedFormat as exc:
        err.print(f"[red]error:[/] {exc}")
    except Exception as exc:  # a converter blew up on this file: say so, don't traceback
        if args.verbose:
            raise
        err.print(f"[red]error:[/] could not analyze {args.doc}: {exc.__class__.__name__}: {exc}")
        err.print("[dim]run with -v for the full traceback[/]")
    return None


def cmd_scan(args: argparse.Namespace) -> int:
    from lectern.pipeline import fails_threshold
    from lectern.report import render

    analysis = _analyze_or_exit(args)
    if analysis is None:
        return 1
    if args.json:
        sys.stdout.write(analysis.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        render(analysis, Console(), full_text=args.full_text)
    if args.fail_on and fails_threshold(analysis, Severity(args.fail_on)):
        Console(stderr=True).print(f"[red]findings at or above '{args.fail_on}': exit 3[/]")
        return 3
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    from lectern.brief import render_brief, write_brief
    from lectern.emit import resolve_selection
    from lectern.pipeline import analyze, make_llm

    err = Console(stderr=True)

    def usage(msg: str) -> None:
        err.print(f"[red]error:[/] {msg}")
        raise SystemExit(2)

    keep = resolve_selection(_parse_zones(args.keep, usage), None)
    llm = None if args.no_llm else make_llm(args.model, local=args.local)
    try:
        analysis = analyze(args.doc, use_llm=not args.no_llm, llm=llm, model=args.model)
    except FileNotFoundError:
        err.print(f"[red]error:[/] file not found: {args.doc}")
        return 1
    except UnsupportedFormat as exc:
        err.print(f"[red]error:[/] {exc}")
        return 1
    out = write_brief(analysis, llm if analysis.mode == "llm" else None)
    text = render_brief(analysis, out, keep)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        err.print(f"[green]wrote[/] {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    try:
        from lectern.mcp_server import build_server
    except ImportError:
        Console(stderr=True).print(
            "[red]error:[/] the MCP server needs the `mcp` package: pip install 'lectern-cli[mcp]'"
        )
        return 1
    build_server(use_llm=not args.no_llm, local=args.local).run(transport="stdio")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        from lectern.serve.app import main as serve_main
    except ImportError:
        Console(stderr=True).print(
            "[red]error:[/] the review UI needs FastAPI: pip install 'lectern-cli[serve]'"
        )
        return 1
    serve_main(
        args.port,
        open_browser=not args.no_browser,
        use_llm=not args.no_llm,
        model=args.model,
        local=args.local,
    )
    return 0


def _parse_zones(value: str | None, parser_error) -> set[Zone] | None:
    if not value:
        return None
    out = set()
    for name in value.split(","):
        name = name.strip()
        if name not in ZONES:
            parser_error(f"unknown zone '{name}' (zones: {', '.join(ZONES)})")
        out.add(Zone(name))
    return out


def cmd_clean(args: argparse.Namespace) -> int:
    from lectern.emit import NEVER_KEEP, clean_markdown, resolve_selection
    from lectern.report import render_selection_prompt

    err = Console(stderr=True)

    def usage(msg: str) -> None:
        err.print(f"[red]error:[/] {msg}")
        raise SystemExit(2)

    keep = _parse_zones(args.keep, usage)
    drop = _parse_zones(args.drop, usage)
    if keep and keep & NEVER_KEEP:
        never = ", ".join(sorted(z.value for z in keep & NEVER_KEEP))
        err.print(f"[yellow]note:[/] {never} can never be kept; listed in the report instead")
    analysis = _analyze_or_exit(args)
    if analysis is None:
        return 1
    selected = resolve_selection(keep, drop)
    if args.interactive:
        selected = render_selection_prompt(analysis, selected, Console(stderr=True))
    text = clean_markdown(analysis, selected, report=not args.no_report)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        kept = sum(1 for s in analysis.segments if s.zone in selected)
        zones = ", ".join(sorted(z.value for z in selected))
        err.print(
            f"[green]wrote[/] {args.output}: kept {kept} of {len(analysis.segments)} segments "
            f"({zones}); {len(analysis.findings)} finding(s) in the report"
        )
    else:
        sys.stdout.write(text)
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
