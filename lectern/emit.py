"""`emit`: the clean Markdown copy and its removal report (DESIGN §4, §6).

The clean copy keeps the selected zones in reading order, exactly as the
segments read them (headings normalized to `#` levels, lists to dashes), with
invisible characters stripped. It never contains `hidden` text, and never
contains `ai_directive` or `ai_policy` text — those appear in the report
instead. The report is the provenance of the *absence*: what was dropped, what
was quarantined, every finding with its location. Policy findings are listed
unconditionally, so a clean file can never launder a "no AI tools" rule.
"""

from __future__ import annotations

from collections import Counter

from lectern.models import Analysis, FindingStatus, Zone
from lectern.screen.encoding import strip_invisible

DEFAULT_KEEP = {Zone.task, Zone.background, Zone.example, Zone.unknown}
NEVER_KEEP = {Zone.hidden, Zone.ai_directive, Zone.ai_policy}
ZONE_ORDER = [
    Zone.task,
    Zone.background,
    Zone.example,
    Zone.structure,
    Zone.unknown,
    Zone.ai_policy,
    Zone.ai_directive,
    Zone.hidden,
]


def resolve_selection(keep: set[Zone] | None, drop: set[Zone] | None) -> set[Zone]:
    """`--keep` replaces the default set; `--drop` removes from it; the never-keep zones win."""
    selected = set(keep) if keep else set(DEFAULT_KEEP)
    if drop:
        selected -= set(drop)
    return selected - NEVER_KEEP


def clean_markdown(analysis: Analysis, keep: set[Zone], *, report: bool = True) -> str:
    kept = [s for s in analysis.segments if s.zone in keep]
    parts: list[str] = []
    removed_chars = 0
    for seg in kept:
        text, removed = strip_invisible(seg.text)
        removed_chars += removed
        parts.append(text.strip())
    body = "\n\n".join(p for p in parts if p)
    if not report:
        return body + "\n"
    return body + "\n\n" + removal_report(analysis, keep, removed_chars) + "\n"


def removal_report(analysis: Analysis, keep: set[Zone], removed_chars: int = 0) -> str:
    counts = Counter(s.zone for s in analysis.segments)
    tokens = Counter()
    for s in analysis.segments:
        tokens[s.zone] += s.tokens_est
    total = sum(tokens.values()) or 1
    kept_tokens = sum(t for z, t in tokens.items() if z in keep)
    src = analysis.source.rsplit("/", 1)[-1]

    lines = [
        "---",
        "",
        "## Lectern removal report",
        "",
        f"Source: `{src}` ({analysis.format}"
        + (f", {analysis.pages} pages" if analysis.pages else "")
        + f") · zoning: {analysis.mode} · lectern {analysis.lectern_version}, "
        + f"taxonomy v{analysis.taxonomy_v}",
        f"Kept {kept_tokens / total * 100:.0f}% of the text"
        f" ({sum(counts[z] for z in keep)} of {len(analysis.segments)} segments).",
        "",
        "| zone | segments | share | kept |",
        "|---|---:|---:|---|",
    ]
    for z in ZONE_ORDER:
        if not counts[z]:
            continue
        status = "yes" if z in keep else ("never" if z in NEVER_KEEP else "no")
        lines.append(f"| {z.value} | {counts[z]} | {tokens[z] / total * 100:.0f}% | {status} |")
    if removed_chars:
        lines += [
            "",
            f"{removed_chars} invisible character(s) (zero-width, bidi, tag) removed "
            "from kept text.",
        ]

    policy = [f for f in analysis.findings if f.kind == "ai_policy"]
    others = [f for f in analysis.findings if f.kind != "ai_policy"]
    lines += ["", f"### Findings ({len(analysis.findings)})", ""]
    if not analysis.findings:
        lines.append(
            "None. No hidden text, AI-directed instructions or AI-use policy statements were found."
        )
    if policy:
        lines.append(
            "**AI-use policy statements** (always reported, never included in the clean copy):"
        )
        lines.append("")
        for f in policy:
            lines.append(f"- {_where(f)} {f.excerpt}")
        lines.append("")
    if others:
        lines.append("| detector | kind | severity | status | where | excerpt |")
        lines.append("|---|---|---|---|---|---|")
        for f in others:
            lines.append(
                f"| {f.detector} | {f.kind} | {f.severity.value} | {f.status.value} | "
                f"{_where(f)} | {_cell(f.excerpt)} |"
            )
    quarantined = [f for f in analysis.findings if f.status is FindingStatus.quarantined]
    if quarantined:
        lines += [
            "",
            f"{len(quarantined)} finding(s) quarantined: that text was excluded from every "
            "LLM call and from this copy.",
        ]
    for w in analysis.warnings:
        lines.append(f"- note: {w}")
    return "\n".join(lines)


def _where(f) -> str:
    bits = []
    if f.page:
        bits.append(f"p{f.page}")
    if f.segment_id:
        bits.append(f.segment_id)
    return "(" + ", ".join(bits) + ")" if bits else "(document properties)"


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")
