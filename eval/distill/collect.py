"""Collect the distillation corpus (DESIGN §8, G7): download every document listed in
`corpus.md` into `eval/results/local/distill/` (gitignored), with its source and licence.

    python eval/distill/collect.py [--out DIR] [--only ID ...] [--force]

The manifest is the table in `corpus.md`; this script writes `manifest.json` next to the
files with what was actually fetched (bytes, sha256, time, whether the text was cut at
`MAX_CHARS`). Text is saved as served, except that e-mail addresses and phone numbers are
redacted so that no personal data reaches the corpus or a prompt (corpus.md, "No personal
data"). Files already present are kept unless `--force`; a failed download is reported and
skipped, so one dead link does not stop the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).parent
CORPUS_MD = HERE / "corpus.md"
DEFAULT_OUT = HERE.parent / "results" / "local" / "distill"
MAX_CHARS = 60_000  # text documents longer than this are cut at a paragraph boundary
TEXT_FORMATS = {"txt", "md"}
USER_AGENT = "lectern-eval/0.1 (+https://github.com/xinglu-cmu/lectern; distillation corpus)"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)"  # +1 (555) 123-4567
    r"|(?<!\w)0\d{2,4}[\s-]\d{3,4}[\s-]?\d{3,4}(?!\w)"  # 020 7946 0000 / 0300 123 4567
)


@dataclass
class Source:
    id: str
    kind: str
    format: str
    licence: str
    url: str


def read_manifest(path: Path = CORPUS_MD) -> list[Source]:
    """The rows of the Markdown table in corpus.md, in order."""
    sources: list[Source] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in {"id", ""} or set(cells[0]) <= {"-"}:
            continue
        sources.append(Source(*cells))
    ids = [s.id for s in sources]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate ids in corpus.md: {dupes}")
    return sources


def redact(text: str) -> tuple[str, int]:
    """E-mail addresses and phone numbers become placeholders; returns the count."""
    n = 0

    def email(_m: re.Match) -> str:
        nonlocal n
        n += 1
        return "[email]"

    def phone(_m: re.Match) -> str:
        nonlocal n
        n += 1
        return "[phone]"

    text = _EMAIL.sub(email, text)
    text = _PHONE.sub(phone, text)
    return text, n


def truncate(text: str, max_chars: int = MAX_CHARS) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n\n", 0, max_chars)
    if cut < max_chars // 2:
        cut = max_chars
    return text[:cut].rstrip() + "\n", True


def fetch(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def collect(
    sources: list[Source], out: Path, *, force: bool = False, log=print
) -> tuple[list[dict], list[dict]]:
    """Downloads each source into `out`; returns (entries, failures) and writes manifest.json."""
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = {e["id"]: e for e in json.loads(manifest_path.read_text())["documents"]}
    entries: list[dict] = []
    failures: list[dict] = []
    for src in sources:
        path = out / f"{src.id}.{src.format}"
        if path.exists() and not force and src.id in previous:
            entries.append(previous[src.id])
            continue
        try:
            raw = fetch(src.url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            failures.append({"id": src.id, "url": src.url, "error": str(exc)})
            log(f"  FAILED {src.id}: {exc}")
            continue
        text = raw.decode("utf-8", errors="replace")
        text, redacted = redact(text)
        truncated = False
        if src.format in TEXT_FORMATS:
            text, truncated = truncate(text)
        path.write_text(text, encoding="utf-8")
        entry = {
            **asdict(src),
            "path": path.name,
            "bytes": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "redacted": redacted,
            "truncated": truncated,
        }
        entries.append(entry)
        log(f"  {src.id}: {entry['bytes']} bytes" + (" (truncated)" if truncated else ""))
    manifest_path.write_text(
        json.dumps(
            {"source": str(CORPUS_MD.relative_to(HERE.parent.parent)), "documents": entries},
            indent=2,
        )
    )
    return entries, failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--only", nargs="*", metavar="ID", help="collect only these ids")
    ap.add_argument("--force", action="store_true", help="re-download files already present")
    args = ap.parse_args(argv)
    sources = read_manifest()
    if args.only:
        sources = [s for s in sources if s.id in set(args.only)]
    print(f"{len(sources)} documents listed in {CORPUS_MD.name}; collecting into {args.out}")
    entries, failures = collect(sources, args.out, force=args.force)
    total = sum(e["bytes"] for e in entries)
    print(
        f"{len(entries)} documents, {total / 1000:.0f} kB; "
        f"{sum(e['redacted'] for e in entries)} redactions; "
        f"{sum(e['truncated'] for e in entries)} truncated; {len(failures)} failed"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
