"""Label the distillation corpus with Claude (DESIGN §8, G7): every segment of every document,
not only the ones the heuristics were unsure about.

    python eval/distill/label.py [--corpus DIR] [--out labels.jsonl] [--model MODEL]
                                 [--local [MODEL]] [--only ID ...] [--limit N] [--dry-run] [--force]

Each document goes through Lectern's own pipeline with the LLM off (heuristic zones and
confidences), then every non-hidden segment is sent to the model through the zoning prompt
(`lectern.zoning.llm_pass.SYSTEM`, the same one the CLI uses) in the same batches, and the
raw reply is kept: nothing is merged, so a `low`-confidence model label is recorded even
where the CLI would keep the heuristic. Output is one JSONL row per segment (document, segment
id, heading path, text, heuristic zone and confidence, model zone and confidence, cost) plus
`summary.json` / `summary.md` with cost and label distribution. `--dry-run` runs only the
heuristics and estimates the model's input. Documents already in the output file are skipped
unless `--force`, so an interrupted run can be resumed without paying twice.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from lectern.llm import DEFAULT_MODEL, LLMUnavailable
from lectern.models import Zone
from lectern.pipeline import analyze, make_llm
from lectern.zoning.llm_pass import CONFIDENCE_VALUE, SEGMENT_MAX_CHARS, SYSTEM, ask_llm, batches

HERE = Path(__file__).parent
DEFAULT_CORPUS = HERE.parent / "results" / "local" / "distill"
SYSTEM_TOKENS_EST = len(SYSTEM) // 4  # the prompt's fixed part, paid once per batch


def load_manifest(corpus: Path) -> list[dict]:
    manifest = corpus / "manifest.json"
    if not manifest.exists():
        raise SystemExit(f"{manifest} not found: run eval/distill/collect.py first")
    return json.loads(manifest.read_text())["documents"]


def label_document(entry: dict, corpus: Path, llm, *, dry_run: bool) -> tuple[list[dict], dict]:
    """Rows for one document and a per-document summary (calls, cost, seconds)."""
    t0 = time.perf_counter()
    a = analyze(corpus / entry["path"], use_llm=False)
    segments = [s for s in a.segments if s.zone is not Zone.hidden]
    rows_by_id: dict[str, dict] = {}
    for s in segments:
        rows_by_id[s.id] = {
            "doc": entry["id"],
            "kind": entry["kind"],
            "format": a.format,
            "source_url": entry["url"],
            "licence": entry["licence"],
            "segment": s.id,
            "seq": s.seq,
            "heading_path": s.heading_path,
            "text": s.text,
            "tokens_est": s.tokens_est,
            "flags": s.flags,
            "heuristic_zone": s.zone.value,
            "heuristic_confidence": s.confidence,
            "heuristic_signals": s.signals,
            "model": None,
            "model_zone": None,
            "model_confidence": None,
            "model_confidence_value": None,
            "batch": None,
            "cost_usd": None,
        }
    est_input = sum(
        SYSTEM_TOKENS_EST + sum(min(s.tokens_est, SEGMENT_MAX_CHARS // 4) for s in b)
        for b in batches(segments)
    )
    doc_summary = {
        "doc": entry["id"],
        "kind": entry["kind"],
        "segments": len(segments),
        "hidden_skipped": len(a.segments) - len(segments),
        "batches": len(batches(segments)),
        "est_input_tokens": est_input,
        "calls": 0,
        "failures": 0,
        "cost_usd": 0.0,
        "seconds": 0.0,
    }
    if dry_run or llm is None:
        doc_summary["seconds"] = round(time.perf_counter() - t0, 2)
        return list(rows_by_id.values()), doc_summary
    for b_index, batch in enumerate(batches(segments)):
        calls0, failures0, cost0 = llm.usage.calls, llm.usage.failures, llm.usage.cost_usd
        labels = ask_llm(batch, llm, title=a.title)
        batch_cost = round(llm.usage.cost_usd - cost0, 6)
        doc_summary["calls"] += llm.usage.calls - calls0
        doc_summary["failures"] += llm.usage.failures - failures0
        doc_summary["cost_usd"] = round(doc_summary["cost_usd"] + batch_cost, 6)
        for s in batch:
            row = rows_by_id[s.id]
            row["model"] = llm.model
            row["batch"] = f"{entry['id']}#{b_index}"
            row["cost_usd"] = round(batch_cost / len(batch), 7)
            label = labels.get(s.id)
            if label is None:
                continue  # the batch failed, or the id came back missing or duplicated
            row["model_zone"] = label.zone.value
            row["model_confidence"] = label.confidence.value
            row["model_confidence_value"] = CONFIDENCE_VALUE[label.confidence]
    doc_summary["seconds"] = round(time.perf_counter() - t0, 2)
    return list(rows_by_id.values()), doc_summary


def summarize(rows: list[dict], docs: list[dict], model: str | None) -> dict:
    labeled = [r for r in rows if r["model_zone"] is not None]
    agree = sum(1 for r in labeled if r["model_zone"] == r["heuristic_zone"])
    sure = [r for r in labeled if r["heuristic_confidence"] >= 0.7]
    agree_sure = sum(1 for r in sure if r["model_zone"] == r["heuristic_zone"])
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in labeled:
        confusion[r["heuristic_zone"]][r["model_zone"]] += 1
    kinds = Counter(d["kind"] for d in docs)
    return {
        "model": model,
        "documents": len(docs),
        "kinds": dict(sorted(kinds.items())),
        "segments": len(rows),
        "tokens_est": sum(r["tokens_est"] for r in rows),
        "labeled": len(labeled),
        "unlabeled": len(rows) - len(labeled),
        "calls": sum(d["calls"] for d in docs),
        "failures": sum(d["failures"] for d in docs),
        "est_input_tokens": sum(d["est_input_tokens"] for d in docs),
        "cost_usd": round(sum(d["cost_usd"] for d in docs), 4),
        "seconds": round(sum(d["seconds"] for d in docs), 1),
        "model_zones": dict(sorted(Counter(r["model_zone"] for r in labeled).items())),
        "model_confidence": dict(sorted(Counter(r["model_confidence"] for r in labeled).items())),
        "heuristic_zones": dict(sorted(Counter(r["heuristic_zone"] for r in rows).items())),
        "agreement": round(agree / len(labeled), 4) if labeled else None,
        "agreement_heuristic_confident": round(agree_sure / len(sure), 4) if sure else None,
        "confusion_heuristic_vs_model": {g: dict(c) for g, c in confusion.items()},
    }


def to_markdown(s: dict) -> str:
    lines = [
        "# Distillation corpus: labels",
        "",
        f"{s['documents']} documents, {s['segments']} segments (≈ {s['tokens_est'] / 1000:.0f}k tokens of text); "
        f"model `{s['model']}`: {s['calls']} calls, {s['failures']} failures, "
        f"{s['labeled']} segments labeled, ${s['cost_usd']:.2f}, {s['seconds'] / 60:.1f} min.",
        "",
        "| zone | model labels | share | heuristic labels |",
        "|---|---:|---:|---:|",
    ]
    for z in [z.value for z in Zone]:
        m = s["model_zones"].get(z, 0)
        h = s["heuristic_zones"].get(z, 0)
        if m or h:
            lines.append(f"| {z} | {m} | {m / max(1, s['labeled']):.0%} | {h} |")
    lines += [
        "",
        f"Model confidence: {s['model_confidence']}. Agreement with the heuristics: "
        f"{s['agreement']:.0%} overall, {s['agreement_heuristic_confident']:.0%} where the heuristics "
        "were confident (≥ 0.7)."
        if s["agreement"] is not None
        else "No model labels (dry run).",
        "",
        "Kinds: " + ", ".join(f"{k} {n}" for k, n in s["kinds"].items()) + ".",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--out", type=Path, help="JSONL output (default: CORPUS/labels.jsonl)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--local", nargs="?", const=True, default=False, metavar="MODEL")
    ap.add_argument("--only", nargs="*", metavar="ID")
    ap.add_argument("--limit", type=int, help="label only the first N documents")
    ap.add_argument(
        "--dry-run", action="store_true", help="heuristics only; estimate the model input"
    )
    ap.add_argument("--force", action="store_true", help="relabel documents already in the output")
    args = ap.parse_args(argv)
    out = args.out or args.corpus / "labels.jsonl"
    docs = load_manifest(args.corpus)
    if args.only:
        docs = [d for d in docs if d["id"] in set(args.only)]
    if args.limit:
        docs = docs[: args.limit]

    done_rows: list[dict] = []
    if out.exists() and not args.force and not args.dry_run:
        done_rows = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
    done_ids = {r["doc"] for r in done_rows}
    summaries_path = out.with_name("summary.json")
    done_docs = []
    if done_ids and summaries_path.exists():
        done_docs = [
            d
            for d in json.loads(summaries_path.read_text()).get("per_doc", [])
            if d["doc"] in done_ids
        ]
    todo = [d for d in docs if d["id"] not in done_ids]

    llm = None
    if not args.dry_run:
        llm = make_llm(args.model, local=args.local)
        if llm is None:
            raise SystemExit("no ANTHROPIC_API_KEY in the environment (or use --local)")
    print(
        f"{len(todo)} documents to label ({len(done_ids)} already in {out.name}); model {llm.model if llm else '(dry run)'}"
    )

    rows = list(done_rows)
    per_doc = list(done_docs)
    mode = "w" if (args.force or args.dry_run) else "a"
    if args.dry_run:
        out = out.with_name("labels.dry-run.jsonl")  # summary.*  follow the same name below
    with out.open(mode, encoding="utf-8") as fh:
        for entry in todo:
            try:
                doc_rows, doc_summary = label_document(
                    entry, args.corpus, llm, dry_run=args.dry_run
                )
            except LLMUnavailable as exc:
                print(f"stopping: {exc}")
                break
            for r in doc_rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            rows += doc_rows
            per_doc.append(doc_summary)
            print(
                f"  {entry['id']}: {doc_summary['segments']} segments, {doc_summary['batches']} batches, "
                f"${doc_summary['cost_usd']:.4f}, {doc_summary['seconds']:.1f} s"
            )
    summary = summarize(rows, per_doc, llm.model if llm else None)
    summary["per_doc"] = per_doc
    stem = "summary.dry-run" if args.dry_run else "summary"
    out.with_name(f"{stem}.json").write_text(json.dumps(summary, indent=2))
    md = to_markdown(summary)
    out.with_name(f"{stem}.md").write_text(md)
    print()
    print(md)
    if args.dry_run:
        est = summary["est_input_tokens"]
        print(
            f"estimated model input: ≈ {est / 1000:.0f}k tokens (≈ ${est / 1e6 * 1.0:.2f} at Haiku's input rate, plus output)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
