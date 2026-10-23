"""The distilled zoning classifier (DESIGN §8, G7): a small linear model trained on Claude's
labels, giving the segments the heuristics were unsure about a second opinion with no key, no
network and no model server.

The model is multinomial logistic regression over hashed features: word unigrams and bigrams of
the segment text, the heading path, the segment's flags, the heuristic verdict (zone, confidence
bucket, signal names) and a few shape counts, each token hashed into one of `N_BUCKETS` slots with
a stable CRC. `eval/distill/train.py` fits it on `eval/results/local/distill/labels.jsonl` and
writes the sparse weights to `distilled.json.gz` next to this file, which ships with the package.
Prediction is a few hundred multiply-adds per segment. `hidden` is never predicted, and the
classifier abstains (keeps the heuristic label) below `MIN_PROB`.
"""

from __future__ import annotations

import gzip
import json
import math
import re
import zlib
from collections import Counter
from functools import lru_cache
from pathlib import Path

from lectern.models import Method, Segment, Zone

FEATURE_VERSION = 1
N_BUCKETS = 1 << 14
MAX_CHARS = 1500  # as much text as the LLM pass sees
MAX_WORDS = 300
MIN_PROB = 0.55  # below this the classifier abstains and the heuristic label stands
THRESHOLD = 0.7  # heuristics below this get the classifier's opinion (same bar as the LLM pass)
PRUNE = 0.1  # weights smaller than this are dropped on save: 118 kB instead of 430, same score
ZONES = ["task", "background", "structure", "example", "ai_directive", "ai_policy"]
MODEL_PATH = Path(__file__).with_name("distilled.json.gz")

_WORD = re.compile(r"[a-z][a-z'-]*|\d+")
_HEADING = re.compile(r"^#+ .*$", re.M)
_IMPERATIVE = re.compile(
    r"^\W*(submit|implement|write|describe|explain|use|include|provide|list|run|install|"
    r"ensure|make sure|read|do not|don't|never|always|check|click|open|select|enter|add|"
    r"create|set|configure|follow|see|note)\b",
    re.I | re.M,
)


def _bucket(x: float, edges: tuple[float, ...]) -> str:
    for i, e in enumerate(edges):
        if x < e:
            return str(i)
    return str(len(edges))


def _signal_name(signal: str) -> str:
    return re.sub(r"[\d×/=().]+", "", signal).strip(":")


def features(seg: Segment) -> dict[int, float]:
    """Hashed, L2-normalized feature vector of a segment as the heuristics left it."""
    feats: Counter[str] = Counter()
    text = seg.text[:MAX_CHARS]
    body = _HEADING.sub("", text)
    words = _WORD.findall(body.lower())[:MAX_WORDS]
    for w in words:
        feats["w:" + w] += 1
    for a, b in zip(words, words[1:], strict=False):
        feats["b:" + a + " " + b] += 1
    for h in seg.heading_path:
        for w in _WORD.findall(h.lower()):
            feats["h:" + w] += 1
    if seg.heading_path:
        for w in _WORD.findall(seg.heading_path[-1].lower()):
            feats["hl:" + w] += 1
    for line in text.splitlines():
        if line.startswith("#"):
            for w in _WORD.findall(line.lower()):
                feats["ho:" + w] += 1
    for f in seg.flags:
        feats["f:" + f] = 1
    feats["hz:" + seg.zone.value] = 1
    feats["hc:" + _bucket(seg.confidence, (0.4, 0.6, 0.7, 0.85))] = 1
    for s in seg.signals:
        if not s.startswith(("llm:", "distilled:")):
            feats["s:" + _signal_name(s)] = 1
    lines = [ln for ln in body.splitlines() if ln.strip()]
    bullets = sum(1 for ln in lines if re.match(r"^\s*([-*+•]|\d+[.)])\s", ln))
    feats["n:len" + _bucket(len(text), (200, 500, 1000))] = 1
    feats["n:lines" + _bucket(len(lines), (2, 5, 12))] = 1
    feats["n:bullets" + _bucket(bullets / max(1, len(lines)), (0.1, 0.5, 0.9))] = 1
    feats["n:urls" + _bucket(text.count("http") + text.count("]("), (1, 3, 8))] = 1
    feats["n:imperative" + _bucket(len(_IMPERATIVE.findall(body)), (1, 3))] = 1
    feats["n:you" + _bucket(sum(1 for w in words if w in ("you", "your")), (1, 3))] = 1
    feats["n:digits" + _bucket(sum(c.isdigit() for c in body) / max(1, len(body)), (0.02, 0.1))] = 1
    if "```" in text:
        feats["n:fence"] = 1
    if "?" in body:
        feats["n:question"] = 1
    vec: dict[int, float] = {}
    for key, count in feats.items():
        slot = zlib.crc32(key.encode("utf-8")) % N_BUCKETS
        vec[slot] = vec.get(slot, 0.0) + math.log1p(count)
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {k: v / norm for k, v in vec.items()}


class DistilledClassifier:
    """Sparse weights per zone plus a bias; `predict` returns the zone and its probability."""

    def __init__(
        self,
        weights: list[dict[int, float]],
        bias: list[float],
        zones: list[str] = ZONES,
        meta: dict | None = None,
    ) -> None:
        self.weights = weights
        self.bias = bias
        self.zones = zones
        self.meta = meta or {}

    def probabilities(self, vec: dict[int, float]) -> list[float]:
        logits = [
            b + sum(w.get(k, 0.0) * v for k, v in vec.items())
            for w, b in zip(self.weights, self.bias, strict=True)
        ]
        top = max(logits)
        exps = [math.exp(z - top) for z in logits]
        total = sum(exps)
        return [e / total for e in exps]

    def predict(self, seg: Segment) -> tuple[Zone, float]:
        probs = self.probabilities(features(seg))
        best = max(range(len(probs)), key=probs.__getitem__)
        return Zone(self.zones[best]), probs[best]

    def save(self, path: Path = MODEL_PATH) -> None:
        payload = {
            "feature_version": FEATURE_VERSION,
            "n_buckets": N_BUCKETS,
            "zones": self.zones,
            "bias": [round(b, 5) for b in self.bias],
            "weights": [
                {str(k): round(v, 4) for k, v in w.items() if abs(v) >= PRUNE} for w in self.weights
            ],
            "meta": self.meta,
        }
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"))

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> DistilledClassifier:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
        if (
            payload.get("feature_version") != FEATURE_VERSION
            or payload.get("n_buckets") != N_BUCKETS
        ):
            raise ValueError(f"{path.name} was trained for another feature version; retrain it")
        weights = [{int(k): float(v) for k, v in w.items()} for w in payload["weights"]]
        return cls(weights, payload["bias"], payload["zones"], payload.get("meta"))


@lru_cache(maxsize=1)
def default_classifier() -> DistilledClassifier:
    return DistilledClassifier.load()


def zone_with_classifier(
    segments: list[Segment],
    clf: DistilledClassifier | None = None,
    *,
    threshold: float = THRESHOLD,
) -> int:
    """Upgrades low-confidence segments in place, like `zone_with_llm` but offline; returns how
    many segments changed. Never assigns `hidden`; abstains below `MIN_PROB`."""
    clf = clf or default_classifier()
    changed = 0
    for seg in segments:
        if seg.confidence >= threshold or seg.zone is Zone.hidden:
            continue
        zone, prob = clf.predict(seg)
        if prob < MIN_PROB:
            seg.signals.append(f"distilled:low({zone.value} {prob:.2f})")
            continue
        if zone is not seg.zone:
            changed += 1
        seg.zone = zone
        seg.confidence = round(min(0.9, prob), 2)
        seg.method = Method.distilled
        seg.signals.append(f"distilled:{prob:.2f}")
    return changed
