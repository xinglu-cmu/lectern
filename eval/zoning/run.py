"""Zoning accuracy suite (DESIGN §9, suite 2): macro-F1 per zone and a confusion matrix.

    python eval/zoning/run.py [--llm] [--local [MODEL]] [--check] [--json results.json] [--md results.md]

Labeled documents live in `labeled/`: a document (`name.md`, `.html`, `.pdf`, …)
next to `name.labels.json`, a list of `{"match": "...", "zone": "..."}` entries.
`match` is a distinctive phrase from the segment; a produced segment takes the
gold zone of the first entry whose phrase it contains. Segments no entry matches
are left out of the score and listed, so the labels stay robust to changes in
how the segmenter cuts.

`--llm` also runs the Claude pass (needs `ANTHROPIC_API_KEY`), `--local` the local
model (Ollama), and each reports its delta over heuristic-only — the ablation
DESIGN §9 asks for. `--check` applies the gate (macro-F1 ≥ 0.75) once the set
holds 30 documents.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from lectern.models import Zone
from lectern.pipeline import analyze

HERE = Path(__file__).parent
LABELED = HERE / "labeled"
RESULTS_DIR = HERE.parent / "results"
ZONES = [z.value for z in Zone]
F1_GATE = 0.75
GATE_MIN_DOCS = 30  # the gate arms itself once the labeled set is big enough to trust


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


def gold_for(segment_text: str, labels: list[dict]) -> str | None:
    t = _norm(segment_text)
    for entry in labels:
        if _norm(entry["match"]) in t:
            return entry["zone"]
    return None


def evaluate(use_llm: bool, local: bool | str = False) -> dict:
    pairs: list[tuple[str, str]] = []  # (gold, predicted)
    unlabeled: list[dict] = []
    per_doc: dict[str, dict] = {}
    docs = sorted(
        p for p in LABELED.iterdir() if p.suffix != ".json" and not p.name.startswith(".")
    )
    for doc in docs:
        labels_path = doc.with_name(doc.stem + ".labels.json")
        if not labels_path.exists():
            continue
        labels = json.loads(labels_path.read_text())
        a = analyze(doc, use_llm=use_llm, local=local)
        doc_pairs = []
        for s in a.segments:
            g = gold_for(s.text, labels)
            if g is None:
                unlabeled.append(
                    {"doc": doc.name, "segment": s.id, "zone": s.zone.value, "text": s.text[:60]}
                )
                continue
            doc_pairs.append((g, s.zone.value))
        pairs += doc_pairs
        per_doc[doc.name] = {
            "segments": len(a.segments),
            "labeled": len(doc_pairs),
            "accuracy": sum(1 for g, p in doc_pairs if g == p) / len(doc_pairs)
            if doc_pairs
            else None,
            "mode": a.mode,
        }
    return {"pairs": pairs, "unlabeled": unlabeled, "per_doc": per_doc, **metrics(pairs)}


def metrics(pairs: list[tuple[str, str]]) -> dict:
    tp, fp, fn = Counter(), Counter(), Counter()
    confusion: dict[str, Counter] = defaultdict(Counter)
    for g, p in pairs:
        confusion[g][p] += 1
        if g == p:
            tp[g] += 1
        else:
            fp[p] += 1
            fn[g] += 1
    per_zone = {}
    for z in ZONES:
        support = tp[z] + fn[z]
        if not support and not fp[z]:
            continue
        prec = tp[z] / (tp[z] + fp[z]) if tp[z] + fp[z] else 0.0
        rec = tp[z] / support if support else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_zone[z] = {"precision": prec, "recall": rec, "f1": f1, "support": support}
    scored = [v for v in per_zone.values() if v["support"]]
    macro_f1 = sum(v["f1"] for v in scored) / len(scored) if scored else 0.0
    accuracy = sum(1 for g, p in pairs if g == p) / len(pairs) if pairs else 0.0
    return {
        "n": len(pairs),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_zone": per_zone,
        "confusion": {g: dict(c) for g, c in confusion.items()},
    }


def to_markdown(heur: dict, llm: dict | None, local: dict | None = None) -> str:
    lines = [
        "# Zoning accuracy results",
        "",
        f"{len(heur['per_doc'])} labeled documents, {heur['n']} labeled segments "
        f"({len(heur['unlabeled'])} segments without a gold label, skipped).",
        "",
        "| mode | accuracy | macro-F1 |",
        "|---|---:|---:|",
        f"| heuristic-only | {heur['accuracy']:.2f} | {heur['macro_f1']:.2f} |",
    ]
    if llm:
        lines.append(f"| + LLM | {llm['accuracy']:.2f} | {llm['macro_f1']:.2f} |")
        lines.append(
            f"| delta | {llm['accuracy'] - heur['accuracy']:+.2f} | {llm['macro_f1'] - heur['macro_f1']:+.2f} |"
        )
    lines += [
        "",
        "Per zone (heuristic-only):",
        "",
        "| zone | precision | recall | F1 | support |",
        "|---|---:|---:|---:|---:|",
    ]
    for z, v in heur["per_zone"].items():
        lines.append(
            f"| {z} | {v['precision']:.2f} | {v['recall']:.2f} | {v['f1']:.2f} | {v['support']} |"
        )
    lines += ["", "Confusion (rows = gold, columns = predicted, heuristic-only):", ""]
    cols = [
        z
        for z in ZONES
        if any(z in c for c in heur["confusion"].values()) or z in heur["confusion"]
    ]
    lines.append("| gold \\ pred | " + " | ".join(cols) + " |")
    lines.append("|---|" + "---:|" * len(cols))
    for g in cols:
        row = heur["confusion"].get(g, {})
        lines.append(f"| {g} | " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    if heur["unlabeled"]:
        lines += ["", "Unlabeled segments (add a `match` to label them):", ""]
        lines += [
            f"- {u['doc']} {u['segment']} ({u['zone']}): {u['text']!r}"
            for u in heur["unlabeled"][:30]
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--llm", action="store_true", help="also run the Claude pass (needs an API key)"
    )
    ap.add_argument(
        "--local",
        nargs="?",
        const=True,
        default=False,
        metavar="MODEL",
        help="also run a local model (Ollama)",
    )
    ap.add_argument(
        "--check", action="store_true", help=f"exit 1 if heuristic macro-F1 < {F1_GATE}"
    )
    ap.add_argument("--json", type=Path, default=RESULTS_DIR / "zoning.json")
    ap.add_argument("--md", type=Path, default=RESULTS_DIR / "zoning.md")
    args = ap.parse_args(argv)
    heur = evaluate(use_llm=False)
    llm = evaluate(use_llm=True) if args.llm else None
    local = evaluate(use_llm=True, local=args.local) if args.local else None
    args.json.parent.mkdir(parents=True, exist_ok=True)
    out = {"heuristic": {k: v for k, v in heur.items() if k != "pairs"}}
    if llm:
        out["llm"] = {k: v for k, v in llm.items() if k != "pairs"}
    if local:
        out["local"] = {k: v for k, v in local.items() if k != "pairs"}
    args.json.write_text(json.dumps(out, indent=2))
    md = to_markdown(heur, llm, local)
    args.md.write_text(md)
    print(md)
    n_docs = len(heur["per_doc"])
    if args.check:
        if n_docs < GATE_MIN_DOCS:
            print(f"gate not armed: {n_docs} labeled documents (< {GATE_MIN_DOCS})")
        elif heur["macro_f1"] < F1_GATE:
            print(f"GATE FAILED: macro-F1 {heur['macro_f1']:.2f} < {F1_GATE}")
            return 1
        else:
            print("gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
