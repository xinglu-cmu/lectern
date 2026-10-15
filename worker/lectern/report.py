"""Terminal report for `lectern scan`: the analysis a person actually reads.

Order follows the questions a reader asks: what is this (overview), what is it
made of (zone map), is anything in here aimed at the AI (findings), then the
segment list for anyone who wants to check the labels. Page furniture is
collapsed into one line so a 50-slide deck doesn't print 50 footers.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lectern.models import Analysis, FindingStatus, Segment, Severity, Zone

ZONE_STYLE = {
    Zone.task: "bold green",
    Zone.background: "cyan",
    Zone.structure: "dim",
    Zone.example: "blue",
    Zone.ai_directive: "bold red",
    Zone.ai_policy: "yellow",
    Zone.hidden: "bold magenta",
    Zone.unknown: "white",
}
SEVERITY_STYLE = {
    Severity.info: "yellow",
    Severity.warning: "bold yellow",
    Severity.critical: "bold red",
}
ZONE_ORDER = [
    Zone.task,
    Zone.background,
    Zone.example,
    Zone.structure,
    Zone.ai_policy,
    Zone.ai_directive,
    Zone.hidden,
    Zone.unknown,
]


def render(analysis: Analysis, console: Console, *, full_text: bool = False) -> None:
    console.print(_header(analysis))
    if analysis.overview:
        console.print(
            Panel(
                Text(analysis.overview.overview),
                title=f"Overview · {analysis.overview.doc_type.value}",
                border_style="green",
            )
        )
    console.print(_zone_table(analysis))
    console.print(_findings_table(analysis))
    console.print(_segment_table(analysis))
    if full_text:
        for seg in analysis.segments:
            console.rule(f"[{ZONE_STYLE[seg.zone]}]{seg.id} · {seg.zone.value}[/]")
            console.print(seg.text)
    for w in analysis.warnings:
        console.print(f"[yellow]note:[/] {w}")
    if analysis.llm:
        u = analysis.llm
        console.print(
            f"[dim]LLM: {u.model} · {u.calls} call(s) · {u.input_tokens} in / {u.output_tokens} out"
            f" · ${u.cost_usd:.4f}[/]"
        )


def _header(a: Analysis) -> Panel:
    lines = [f"[bold]{a.title or a.source.rsplit('/', 1)[-1]}[/]"]
    meta = f"{a.format}" + (f" · {a.pages} pages" if a.pages else "")
    meta += f" · {len(a.segments)} segments · converter: {a.converter} · mode: {a.mode}"
    lines.append(f"[dim]{meta}[/]")
    return Panel("\n".join(lines), title="lectern scan", border_style="blue")


def _zone_table(a: Analysis) -> Table:
    t = Table(title="Zone map (share of text)", show_lines=False)
    t.add_column("zone")
    t.add_column("share", justify="right")
    t.add_column("", min_width=22)
    t.add_column("segments", justify="right")
    counts = {z: sum(1 for s in a.segments if s.zone is z) for z in Zone}
    for z in ZONE_ORDER:
        share = a.zone_shares.get(z.value, 0.0)
        if not share and not counts[z]:
            continue
        bar = "█" * round(share * 20)
        t.add_row(
            Text(z.value, style=ZONE_STYLE[z]),
            f"{share * 100:.0f}%",
            Text(bar, style=ZONE_STYLE[z]),
            str(counts[z]),
        )
    return t


def _findings_table(a: Analysis) -> Table | Text:
    if not a.findings:
        return Text(
            "Findings: none. No AI-directed text or AI-use policy statements found.", style="green"
        )
    t = Table(title=f"Findings ({len(a.findings)})")
    t.add_column("det.")
    t.add_column("kind")
    t.add_column("severity")
    t.add_column("status")
    t.add_column("where")
    t.add_column("excerpt", overflow="fold")
    for f in a.findings:
        where = f.segment_id or ""
        if f.page:
            where += f" · p{f.page}"
        status = Text(
            f.status.value,
            style="bold magenta" if f.status is FindingStatus.quarantined else "dim",
        )
        excerpt = Text(f.excerpt)
        if f.note:
            excerpt.append(f"\n{f.note}", style="dim")
        t.add_row(
            f.detector,
            f.kind,
            Text(f.severity.value, style=SEVERITY_STYLE[f.severity]),
            status,
            where or "doc",
            excerpt,
        )
    return t


def render_selection_prompt(analysis: Analysis, selected: set[Zone], console: Console) -> set[Zone]:
    """`clean --interactive`: one yes/no per zone that has content, in the terminal."""
    from lectern.emit import NEVER_KEEP

    console.print("[bold]Choose what to keep.[/] Enter = keep the default shown in brackets.")
    chosen: set[Zone] = set()
    for z in ZONE_ORDER:
        segs = [s for s in analysis.segments if s.zone is z]
        if not segs:
            continue
        tokens = sum(s.tokens_est for s in segs)
        sample = _preview(segs[0]).plain
        if z in NEVER_KEEP:
            console.print(
                f"  [{ZONE_STYLE[z]}]{z.value:13}[/] {len(segs):3} seg · ~{tokens:5} tok · "
                "never kept, reported instead"
            )
            continue
        default = "Y/n" if z in selected else "y/N"
        console.print(
            f"  [{ZONE_STYLE[z]}]{z.value:13}[/] {len(segs):3} seg · ~{tokens:5} tok · "
            f"e.g. {sample[:70]}"
        )
        answer = console.input(f"    keep {z.value}? [{default}] ").strip().lower()
        keep = (z in selected) if not answer else answer.startswith("y")
        if keep:
            chosen.add(z)
    return chosen


def _segment_table(a: Analysis) -> Table:
    t = Table(title="Segments")
    t.add_column("id", justify="right")
    t.add_column("page", justify="right")
    t.add_column("zone")
    t.add_column("conf", justify="right")
    t.add_column("via")
    t.add_column("section / first line", overflow="fold")
    furniture = [s for s in a.segments if s.zone is Zone.structure and _is_furniture(s)]
    for s in a.segments:
        if s in furniture:
            continue
        t.add_row(
            s.id,
            _pages(s),
            Text(s.zone.value, style=ZONE_STYLE[s.zone]),
            f"{s.confidence:.2f}",
            s.method.value,
            _preview(s),
        )
    if furniture:
        pages = sorted({p for s in furniture for p in (s.anchor.page_start,) if p})
        t.add_row(
            f"{len(furniture)}×",
            f"{pages[0]}–{pages[-1]}" if len(pages) > 1 else (str(pages[0]) if pages else ""),
            Text("structure", style=ZONE_STYLE[Zone.structure]),
            "",
            "heuristic",
            Text(f"page headers / footers / page numbers ({len(furniture)} segments)", style="dim"),
        )
    return t


def _is_furniture(s: Segment) -> bool:
    return bool({"header", "footer", "page_number", "repeated"} & set(s.flags))


def _pages(s: Segment) -> str:
    if s.anchor.page_start is None:
        return ""
    if s.anchor.page_end and s.anchor.page_end != s.anchor.page_start:
        return f"{s.anchor.page_start}–{s.anchor.page_end}"
    return str(s.anchor.page_start)


def _preview(s: Segment) -> Text:
    first = next((ln for ln in s.text.splitlines() if ln.strip() and not ln.startswith("#")), "")
    first = " ".join(first.split())
    if len(first) > 90:
        first = first[:89].rstrip() + "…"
    out = Text()
    if s.heading_path:
        out.append(" > ".join(s.heading_path[-2:]), style="bold")
        out.append("  ")
    out.append(first, style="dim")
    return out
