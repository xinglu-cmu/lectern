"""Train the distilled zoning classifier (DESIGN §8, G7) on Claude's labels.

    python eval/distill/train.py [--labels FILE] [--out lectern/zoning/distilled.json.gz]
                                 [--epochs N] [--folds K] [--no-save]

Reads `labels.jsonl` from `eval/distill/label.py`, rebuilds each segment as the heuristics
left it (zone, confidence, signals, flags) and fits multinomial logistic regression over the
hashed features of `lectern.zoning.distilled` by SGD, in pure Python (the training set is
small: a couple of thousand segments). Rows the model did not label, or labeled `unknown`,
are dropped. First a K-fold cross-validation *by document* reports how well the model
reproduces Claude on documents it has not seen; then the model is refit on everything and
saved with that number in its metadata. The real test is the labeled set:
`python eval/zoning/run.py --distilled`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

from lectern.models import Segment, SegmentAnchor, Zone
from lectern.zoning.distilled import MODEL_PATH, ZONES, DistilledClassifier, features

HERE = Path(__file__).parent
DEFAULT_LABELS = HERE.parent / "results" / "local" / "distill" / "labels.jsonl"


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r.get("model_zone") in ZONES]


def to_segment(row: dict) -> Segment:
    return Segment(
        id=row["segment"],
        seq=row["seq"],
        heading_path=row["heading_path"],
        text=row["text"],
        tokens_est=row["tokens_est"],
        zone=Zone(row["heuristic_zone"]),
        confidence=row["heuristic_confidence"],
        signals=row.get("heuristic_signals", []),
        flags=row.get("flags", []),
        anchor=SegmentAnchor(block_start=0, block_end=0),
    )


def fit(
    samples: list[tuple[dict[int, float], int]],
    *,
    epochs: int = 30,
    lr: float = 0.5,
    l2: float = 1e-4,
    seed: int = 0,
) -> DistilledClassifier:
    """Multinomial logistic regression by SGD with inverse-sqrt-frequency class weights."""
    rng = random.Random(seed)
    k = len(ZONES)
    counts = Counter(y for _, y in samples)
    class_w = [math.sqrt(len(samples) / (k * counts[c])) if counts[c] else 0.0 for c in range(k)]
    weights: list[dict[int, float]] = [{} for _ in range(k)]
    bias = [0.0] * k
    order = list(range(len(samples)))
    for epoch in range(epochs):
        rng.shuffle(order)
        step = lr / (1 + epoch * 0.3)
        for i in order:
            x, y = samples[i]
            logits = [
                bias[c] + sum(weights[c].get(j, 0.0) * v for j, v in x.items()) for c in range(k)
            ]
            top = max(logits)
            exps = [math.exp(z - top) for z in logits]
            total = sum(exps)
            cw = class_w[y]
            for c in range(k):
                g = (exps[c] / total - (1.0 if c == y else 0.0)) * cw
                if not g:
                    continue
                bias[c] -= step * g
                wc = weights[c]
                for j, v in x.items():
                    wc[j] = wc.get(j, 0.0) * (1 - step * l2) - step * g * v
    return DistilledClassifier(weights, bias)


def evaluate(clf: DistilledClassifier, samples: list[tuple[dict[int, float], int]]) -> dict:
    tp, fp, fn = Counter(), Counter(), Counter()
    correct = 0
    for x, y in samples:
        probs = clf.probabilities(x)
        p = max(range(len(probs)), key=probs.__getitem__)
        if p == y:
            correct += 1
            tp[y] += 1
        else:
            fp[p] += 1
            fn[y] += 1
    f1s = []
    for c in range(len(ZONES)):
        if not tp[c] + fn[c]:
            continue
        prec = tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else 0.0
        rec = tp[c] / (tp[c] + fn[c])
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return {
        "n": len(samples),
        "accuracy": correct / len(samples) if samples else 0.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
    }


def cross_validate(rows: list[dict], folds: int, epochs: int, l2: float) -> dict:
    docs = sorted({r["doc"] for r in rows})
    rng = random.Random(0)
    rng.shuffle(docs)
    fold_of = {d: i % folds for i, d in enumerate(docs)}
    vec = {id(r): (features(to_segment(r)), ZONES.index(r["model_zone"])) for r in rows}
    results = []
    for f in range(folds):
        train = [vec[id(r)] for r in rows if fold_of[r["doc"]] != f]
        test = [vec[id(r)] for r in rows if fold_of[r["doc"]] == f]
        clf = fit(train, epochs=epochs, l2=l2)
        results.append(evaluate(clf, test))
    n = sum(r["n"] for r in results)
    return {
        "folds": folds,
        "accuracy": sum(r["accuracy"] * r["n"] for r in results) / n,
        "macro_f1": sum(r["macro_f1"] * r["n"] for r in results) / n,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--out", type=Path, default=MODEL_PATH)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--l2", type=float, default=1e-4, help="L2 penalty per step")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)
    rows = load_rows(args.labels)
    by_zone = Counter(r["model_zone"] for r in rows)
    print(
        f"{len(rows)} labeled segments from {len({r['doc'] for r in rows})} documents: {dict(by_zone)}"
    )
    t0 = time.perf_counter()
    cv = cross_validate(rows, args.folds, args.epochs, args.l2)
    print(
        f"{args.folds}-fold by document, agreement with Claude on unseen documents: "
        f"accuracy {cv['accuracy']:.3f}, macro-F1 {cv['macro_f1']:.3f} ({time.perf_counter() - t0:.0f} s)"
    )
    samples = [(features(to_segment(r)), ZONES.index(r["model_zone"])) for r in rows]
    clf = fit(samples, epochs=args.epochs, l2=args.l2)
    fit_score = evaluate(clf, samples)
    print(f"refit on everything: training accuracy {fit_score['accuracy']:.3f}")
    clf.meta = {
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest()[:16],
        "teacher": rows[0].get("model"),
        "documents": len({r["doc"] for r in rows}),
        "segments": len(rows),
        "label_counts": dict(sorted(by_zone.items())),
        "cv_by_document": {k: round(v, 4) if isinstance(v, float) else v for k, v in cv.items()},
        "epochs": args.epochs,
        "l2": args.l2,
    }
    if not args.no_save:
        clf.save(args.out)
        nonzero = sum(len(w) for w in clf.weights)
        print(f"saved {args.out} ({args.out.stat().st_size / 1000:.0f} kB, {nonzero} weights)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
