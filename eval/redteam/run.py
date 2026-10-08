"""Red-team suite runner: precision and recall per technique (DESIGN §9, suite 1).

    python eval/redteam/run.py [--out DIR] [--check] [--json results.json] [--md results.md]

Regenerates the corpus (deterministic), runs `lectern` offline on every file and
scores each attacked document by whether an expected detector fired *on the
payload* (the finding's excerpt overlaps the injected text), whether D1 also
caught the directive, and whether the text ended up quarantined. Controls score
false positives: any quarantine-level finding on a clean document.

Metrics per technique: recall = detected / attacked; precision = detected /
(detected + controls where the same detector family fired). `--check` applies
the DESIGN §9 initial gates (recall ≥ 0.90, precision ≥ 0.80 per technique)
and exits 1 on a miss — the CI gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from lectern.models import FindingStatus
from lectern.pipeline import analyze
from lectern.screen.encoding import strip_invisible

sys.path.insert(0, str(Path(__file__).parent))
from generate import DEFAULT_OUT, TECHNIQUES, generate  # noqa: E402

RECALL_GATE = 0.90
PRECISION_GATE = 0.80
RESULTS_DIR = Path(__file__).parent.parent / "results"


def _norm(text: str) -> str:
    text, _ = strip_invisible(text)
    return re.sub(r"\W+", " ", text).strip().lower()


def _overlaps(excerpt: str, payload: str) -> bool:
    """The finding's excerpt covers the payload. Whitespace is ignored on both sides because
    extractors may split words at invisible characters ("ign ore")."""
    e, p = _norm(excerpt).replace(" ", ""), _norm(payload).replace(" ", "")
    if not e or not p:
        return False
    if p in e or e in p:
        return True
    return p[:30] in e  # partial: the start of the payload


def score(entries, out: Path) -> dict:
    per: dict[str, dict] = {
        t: {"attacked": 0, "detected": 0, "directive": 0, "quarantined": 0, "fp": 0}
        for t in TECHNIQUES
    }
    control_fp_by_detector: dict[str, int] = defaultdict(int)
    misses: list[dict] = []
    control_findings: list[dict] = []
    for e in entries:
        a = analyze(out / e["file"], use_llm=False)
        if e["technique"] == "control":
            for f in a.findings:
                if f.status is FindingStatus.quarantined or f.detector in (
                    "H1",
                    "H2",
                    "H3",
                    "H4",
                    "H5",
                    "H6",
                ):
                    control_fp_by_detector[f.detector] += 1
                    control_findings.append(
                        {
                            "file": e["file"],
                            "detector": f.detector,
                            "kind": f.kind,
                            "excerpt": f.excerpt[:80],
                        }
                    )
            continue
        row = per[e["technique"]]
        row["attacked"] += 1
        hits = [
            f
            for f in a.findings
            if f.detector in e["expected_detectors"] and _overlaps(f.excerpt, e["payload"])
        ]
        if hits:
            row["detected"] += 1
        else:
            misses.append(
                {
                    "file": e["file"],
                    "expected": e["expected_detectors"],
                    "found": sorted({f.detector for f in a.findings}),
                }
            )
        if any(f.detector == "D1" and _overlaps(f.excerpt, e["payload"]) for f in a.findings):
            row["directive"] += 1
        if any(
            f.status is FindingStatus.quarantined and _overlaps(f.excerpt, e["payload"])
            for f in a.findings
        ):
            row["quarantined"] += 1

    results = {
        "techniques": {},
        "controls": {
            "documents": sum(1 for e in entries if e["technique"] == "control"),
            "false_positive_findings": dict(control_fp_by_detector),
            "details": control_findings,
        },
        "misses": misses,
    }
    for t, row in per.items():
        detectors = {d for fmt_set in TECHNIQUES[t][1].values() for d in fmt_set}
        fp = sum(control_fp_by_detector[d] for d in detectors)
        row["fp"] = fp
        recall = row["detected"] / row["attacked"] if row["attacked"] else None
        precision = row["detected"] / (row["detected"] + fp) if (row["detected"] + fp) else None
        results["techniques"][t] = {**row, "recall": recall, "precision": precision}
    return results


def to_markdown(results: dict) -> str:
    lines = [
        "# Red-team suite results",
        "",
        "Offline (`--no-llm`), deterministic corpus. Recall = attacked documents where an expected "
        "detector fired on the payload; precision counts the same detector family firing on clean controls.",
        "",
        "| technique | attacked | detected | recall | precision | D1 also | quarantined |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for t, r in results["techniques"].items():
        rec = f"{r['recall']:.2f}" if r["recall"] is not None else "–"
        prec = f"{r['precision']:.2f}" if r["precision"] is not None else "–"
        lines.append(
            f"| {t} | {r['attacked']} | {r['detected']} | {rec} | {prec} | {r['directive']} | {r['quarantined']} |"
        )
    c = results["controls"]
    lines += [
        "",
        f"Controls: {c['documents']} clean documents; hidden-text findings on them: {c['false_positive_findings'] or 'none'}.",
    ]
    if results["misses"]:
        lines += ["", "Misses:", ""] + [
            f"- `{m['file']}`: expected {m['expected']}, found {m['found']}"
            for m in results["misses"]
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where the corpus is generated")
    ap.add_argument("--check", action="store_true", help="exit 1 if any technique misses the gates")
    ap.add_argument("--json", type=Path, default=RESULTS_DIR / "redteam.json")
    ap.add_argument("--md", type=Path, default=RESULTS_DIR / "redteam.md")
    args = ap.parse_args(argv)

    generate(args.out)
    entries = json.loads((args.out / "manifest.json").read_text())
    results = score(entries, args.out)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(results, indent=2))
    args.md.write_text(to_markdown(results))
    print(to_markdown(results))

    if args.check:
        bad = [
            t
            for t, r in results["techniques"].items()
            if (r["recall"] is not None and r["recall"] < RECALL_GATE)
            or (r["precision"] is not None and r["precision"] < PRECISION_GATE)
        ]
        if bad:
            print(
                f"GATE FAILED: {', '.join(bad)} (recall ≥ {RECALL_GATE}, precision ≥ {PRECISION_GATE})"
            )
            return 1
        print("gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
