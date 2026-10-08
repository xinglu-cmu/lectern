"""Character-level tricks (H6): text that is in the file but not on the screen.

- zero-width characters (ZWSP, ZWNJ, ZWJ, word joiner, BOM) break words apart
  for a model without a reader noticing;
- bidi controls can make text render in a different order than it is stored;
- private-use characters render as nothing or as boxes;
- Unicode *tag* characters (U+E0000–E007F) are invisible and map one-to-one
  onto ASCII — the "ASCII smuggling" trick for hiding a whole instruction;
- look-alike letters from Cyrillic or Greek inside a Latin word evade exact
  pattern matching ("ignоre" with a Cyrillic о).
"""

from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿", "᠎"}
BIDI = {chr(c) for c in range(0x202A, 0x202F)} | {chr(c) for c in range(0x2066, 0x206A)}
_TAG_RANGE = (0xE0000, 0xE007F)
_WORD = re.compile(r"\w+", re.U)


def is_tag(ch: str) -> bool:
    return _TAG_RANGE[0] <= ord(ch) <= _TAG_RANGE[1]


def is_pua(ch: str) -> bool:
    return 0xE000 <= ord(ch) <= 0xF8FF


def decode_tags(text: str) -> str:
    """The ASCII text smuggled in tag characters, if any."""
    return "".join(
        chr(ord(ch) - 0xE0000) for ch in text if is_tag(ch) and 0x20 <= ord(ch) - 0xE0000 < 0x7F
    )


def strip_invisible(text: str) -> tuple[str, int]:
    """Remove zero-width, bidi, tag and private-use characters. Returns (text, removed)."""
    out = []
    removed = 0
    for ch in text:
        if ch in ZERO_WIDTH or ch in BIDI or is_tag(ch) or is_pua(ch):
            removed += 1
        else:
            out.append(ch)
    return "".join(out), removed


def count_invisible(text: str) -> dict[str, int]:
    counts = {"zero_width": 0, "bidi": 0, "private_use": 0, "tag": 0}
    for ch in text:
        if ch in ZERO_WIDTH:
            counts["zero_width"] += 1
        elif ch in BIDI:
            counts["bidi"] += 1
        elif is_pua(ch):
            counts["private_use"] += 1
        elif is_tag(ch):
            counts["tag"] += 1
    return {k: v for k, v in counts.items() if v}


def _script(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    for s in ("LATIN", "CYRILLIC", "GREEK"):
        if name.startswith(s):
            return s
    return "OTHER"


def mixed_script_words(text: str, limit: int = 5) -> list[str]:
    """Words mixing Latin with Cyrillic or Greek letters: the homoglyph signature."""
    found: list[str] = []
    for word in _WORD.findall(text):
        scripts = {s for s in (_script(ch) for ch in word) if s in ("LATIN", "CYRILLIC", "GREEK")}
        if "LATIN" in scripts and len(scripts) > 1:
            found.append(word)
            if len(found) >= limit:
                break
    return found
