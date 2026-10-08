"""Conversion snapshots (DESIGN §9, suite 3): what the converters read from a fixed corpus.

    python eval/conversion/run.py [--update]

The corpus is the red-team seeds rendered clean as PDF, HTML and DOCX by our own
writers — redistributable, deterministic, and exactly the files the detectors
are measured on. For each file, the converter's output (block type, heading
level, flags, text) is compared with the stored snapshot in `snapshots/`. A
difference fails the run: a library upgrade or a converter change altered what
Lectern reads, and someone should look. `--update` rewrites the snapshots after
an intended change.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import tempfile
from pathlib import Path

from lectern.converters import load

sys.path.insert(0, str(Path(__file__).parent.parent / "redteam"))
from generate import FORMATS, RENDER, parse_seed  # noqa: E402

HERE = Path(__file__).parent
SNAPSHOTS = HERE / "snapshots"
SEEDS = HERE.parent / "redteam" / "seeds"


def snapshot_of(path: Path) -> dict:
    doc = load(path)
    return {
        "converter": doc.converter,
        "format": doc.format,
        "pages": doc.pages,
        "title": doc.title,
        "meta_keys": sorted(k for k in doc.meta if k not in ("producer", "creator")),
        "blocks": [
            {
                "type": b.type.value,
                "level": b.level,
                "flags": sorted(b.flags),
                "page": b.anchor.page,
                "text": b.text,
            }
            for b in doc.blocks
        ],
    }


def render_corpus(out: Path) -> list[Path]:
    files = []
    for seed in sorted(SEEDS.glob("*.md")):
        title, sections = parse_seed(seed.read_text(encoding="utf-8"))
        for fmt in FORMATS:
            f = out / f"{seed.stem}.{fmt}"
            RENDER[fmt](f, title, sections, None)
            files.append(f)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--update", action="store_true", help="rewrite the snapshots")
    args = ap.parse_args(argv)
    SNAPSHOTS.mkdir(exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for f in render_corpus(Path(tmp)):
            snap = snapshot_of(f)
            target = SNAPSHOTS / f"{f.name}.json"
            text = json.dumps(snap, indent=1, ensure_ascii=False) + "\n"
            if args.update or not target.exists():
                target.write_text(text, encoding="utf-8")
                print(f"wrote {target.name} ({len(snap['blocks'])} blocks)")
                continue
            old = target.read_text(encoding="utf-8")
            if old == text:
                print(f"ok    {target.name} ({len(snap['blocks'])} blocks)")
                continue
            failures += 1
            print(f"DIFF  {target.name}")
            for line in difflib.unified_diff(
                old.splitlines(), text.splitlines(), "snapshot", "now", lineterm="", n=1
            ):
                print("      " + line)
    if failures:
        print(f"{failures} snapshot(s) differ; run with --update if the change is intended")
        return 1
    print("conversion snapshots match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
