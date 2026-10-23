"""The distilled zoning classifier: features, abstention, the gate, the model, --distilled."""

import json
from pathlib import Path

from lectern.cli import main
from lectern.models import Method, Segment, SegmentAnchor, Zone
from lectern.pipeline import analyze
from lectern.segment import est_tokens
from lectern.zoning.distilled import (
    MIN_PROB,
    N_BUCKETS,
    ZONES,
    DistilledClassifier,
    default_classifier,
    features,
    zone_with_classifier,
)


def _seg(i: int, text: str, zone=Zone.unknown, conf=0.3, heading=("Deliverables",)) -> Segment:
    return Segment(
        id=f"s{i}",
        seq=i,
        heading_path=list(heading),
        text=text,
        tokens_est=est_tokens(text),
        zone=zone,
        confidence=conf,
        signals=["task_markers=2/3"],
        anchor=SegmentAnchor(block_start=i, block_end=i),
    )


def test_features_are_hashed_normalized_and_deterministic():
    seg = _seg(1, "Submit your report by Friday. Include a plot of running time.")
    vec = features(seg)
    assert vec and all(0 <= k < N_BUCKETS for k in vec)
    assert abs(sum(v * v for v in vec.values()) - 1.0) < 1e-6
    assert vec == features(seg)
    assert features(_seg(2, "Something else entirely about cats.")) != vec


def _constant_classifier(zone: str, strength: float) -> DistilledClassifier:
    """Predicts `zone` for everything, with a probability set by `strength`."""
    bias = [0.0] * len(ZONES)
    bias[ZONES.index(zone)] = strength
    return DistilledClassifier([{} for _ in ZONES], bias)


def test_classifier_upgrades_only_unsure_segments_and_never_hidden():
    segs = [
        _seg(1, "a", Zone.task, 0.9),  # confident: left alone
        _seg(2, "b", Zone.unknown, 0.3),  # unsure: re-zoned
        _seg(3, "c", Zone.hidden, 0.3),  # hidden: never touched
    ]
    changed = zone_with_classifier(segs, _constant_classifier("background", 5.0))
    assert changed == 1
    assert segs[0].zone is Zone.task and segs[0].method is Method.heuristic
    assert segs[1].zone is Zone.background and segs[1].method is Method.distilled
    assert segs[1].confidence <= 0.9 and any(s.startswith("distilled:") for s in segs[1].signals)
    assert segs[2].zone is Zone.hidden and segs[2].method is Method.heuristic


def test_classifier_abstains_when_unsure():
    seg = _seg(1, "b", Zone.unknown, 0.3)
    clf = _constant_classifier("example", 0.1)  # nearly uniform: top probability < MIN_PROB
    assert max(clf.probabilities(features(seg))) < MIN_PROB
    assert zone_with_classifier([seg], clf) == 0
    assert seg.zone is Zone.unknown and seg.method is Method.heuristic
    assert any(s.startswith("distilled:low(") for s in seg.signals)


def test_shipped_model_loads_and_knows_its_provenance():
    clf = default_classifier()
    assert clf.zones == ZONES and "hidden" not in clf.zones
    assert clf.meta["segments"] > 1000 and clf.meta["documents"] >= 40
    assert "cv_by_document" in clf.meta and clf.meta["teacher"]
    zone, prob = clf.predict(
        _seg(1, "```python\ndef bubble_sort(xs):\n    pass\n```", Zone.unknown, 0.3, ("Example",))
    )
    assert zone in Zone and 0 < prob <= 1


def test_save_and_load_round_trip(tmp_path: Path):
    clf = DistilledClassifier(
        [{1: 0.5, 2: -0.25} for _ in ZONES], [0.1] * len(ZONES), meta={"k": 1}
    )
    clf.save(tmp_path / "m.json.gz")
    back = DistilledClassifier.load(tmp_path / "m.json.gz")
    assert back.weights[0] == {1: 0.5, 2: -0.25} and back.bias == [0.1] * len(ZONES)
    assert back.meta == {"k": 1}


def test_distilled_mode_is_offline(assignment_md: Path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "would-not-be-used")
    a = analyze(assignment_md, distilled=True)
    assert a.mode == "distilled" and a.llm is None and a.overview is None
    assert any("distilled classifier" in w for w in a.warnings)
    assert not any("heuristic-only" in w for w in a.warnings)
    assert {s.method for s in a.segments} <= {Method.heuristic, Method.distilled}


def test_cli_scan_distilled(assignment_md: Path, capsys):
    code = main(["scan", str(assignment_md), "--distilled", "--json"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "distilled"
