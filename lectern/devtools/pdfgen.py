"""A tiny PDF writer for tests: real text with real fonts, sizes, colours and
positions, no dependency. Enough for pdfplumber to read every word back with
its style — which is exactly what the PDF converter and, next week, the
hidden-text detectors need to be tested against. The red-team generator
(eval/redteam) will grow from the same idea.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PAGE_W, PAGE_H = 612.0, 792.0  # US Letter, points


@dataclass
class Text:
    text: str
    x: float
    y: float  # distance from the *top* of the page, like pdfplumber's `top`
    size: float = 11.0
    bold: bool = False
    color: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class Rect:
    x: float
    y: float  # top, like Text
    w: float
    h: float
    color: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class Page:
    items: list[Text] = field(default_factory=list)
    rects: list[Rect] = field(default_factory=list)

    def add(self, text: str, x: float, y: float, **kw) -> Page:
        self.items.append(Text(text, x, y, **kw))
        return self

    def rect(self, x: float, y: float, w: float, h: float, color=(0.0, 0.0, 0.0)) -> Page:
        """A filled rectangle drawn *before* the text (so it sits behind it)."""
        self.rects.append(Rect(x, y, w, h, color))
        return self


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class _Unicode:
    """Characters outside Latin-1 (zero-width, tag characters, …) are written through a
    third font whose ToUnicode CMap maps private byte codes 0x80–0xFF back to the real
    code points — the same mechanism a real document (or attacker) uses, and the one
    pdfminer/pdfplumber decode."""

    def __init__(self) -> None:
        self.codes: dict[str, int] = {}

    def code(self, ch: str) -> int:
        if ch not in self.codes:
            if len(self.codes) >= 128:
                raise ValueError("too many distinct non-Latin-1 characters for one PDF")
            self.codes[ch] = 0x80 + len(self.codes)
        return self.codes[ch]

    def cmap(self) -> bytes:
        entries = []
        for ch, code in self.codes.items():
            utf16 = ch.encode("utf-16-be").hex().upper()
            entries.append(f"<{code:02X}> <{utf16}>")
        body = (
            "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
            "/CMapName /Lectern-UCS def /CMapType 2 def\n"
            "1 begincodespacerange <00> <FF> endcodespacerange\n"
            f"{len(entries)} beginbfchar\n" + "\n".join(entries) + "\nendbfchar\n"
            "endcmap CMapName currentdict /CMap defineresource pop end end\n"
        )
        return body.encode("ascii")


def _needs_unicode(text: str) -> bool:
    return any(ord(ch) > 0xFF for ch in text)


def _content(page: Page, uni: _Unicode) -> bytes:
    ops = []
    for rc in page.rects:
        r, g, b = rc.color
        ops.append(
            f"{r:.3f} {g:.3f} {b:.3f} rg {rc.x:.1f} {PAGE_H - rc.y - rc.h:.1f} "
            f"{rc.w:.1f} {rc.h:.1f} re f"
        )
    for t in page.items:
        r, g, b = t.color
        baseline = PAGE_H - t.y - t.size  # y is the top of the text box
        if _needs_unicode(t.text):
            # split into Latin-1 pieces (F1/F2) and Unicode pieces (F3), same baseline
            pieces: list[tuple[str, str]] = []
            for ch in t.text:
                font = "/F3" if ord(ch) > 0xFF else ("/F2" if t.bold else "/F1")
                if pieces and pieces[-1][0] == font:
                    pieces[-1] = (font, pieces[-1][1] + ch)
                else:
                    pieces.append((font, ch))
            segs = []
            for font, piece in pieces:
                if font == "/F3":
                    raw = "".join(f"\\{uni.code(ch):03o}" for ch in piece)
                    segs.append(f"{font} {t.size:.1f} Tf ({raw}) Tj")
                else:
                    segs.append(f"{font} {t.size:.1f} Tf ({_esc(piece)}) Tj")
            ops.append(
                f"BT {r:.3f} {g:.3f} {b:.3f} rg 1 0 0 1 {t.x:.1f} {baseline:.1f} Tm "
                + " ".join(segs)
                + " ET"
            )
            continue
        font = "/F2" if t.bold else "/F1"
        ops.append(
            f"BT {font} {t.size:.1f} Tf {r:.3f} {g:.3f} {b:.3f} rg "
            f"1 0 0 1 {t.x:.1f} {baseline:.1f} Tm ({_esc(t.text)}) Tj ET"
        )
    return ("\n".join(ops) + "\n").encode("latin-1", errors="replace")


def write_pdf(
    path: Path, pages: list[Page], title: str | None = None, subject: str | None = None
) -> Path:
    objs: list[bytes] = []

    def add(body: str | bytes) -> int:
        objs.append(body if isinstance(body, bytes) else body.encode("latin-1"))
        return len(objs)

    uni = _Unicode()
    contents = [_content(page, uni) for page in pages]  # assigns the private codes
    font1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    cmap = uni.cmap()
    cmap_id = add(b"<< /Length %d >>\nstream\n" % len(cmap) + cmap + b"endstream")
    diffs = " ".join("/space" for _ in uni.codes) or "/space"
    font3 = add(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        f"/Encoding << /Type /Encoding /Differences [128 {diffs}] >> /ToUnicode {cmap_id} 0 R >>"
    )
    pages_id = len(objs) + 1 + 2 * len(pages)  # reserved after page + content objects
    page_ids = []
    for content in contents:
        cid = add(b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream")
        pid = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
            f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R /F3 {font3} 0 R >> >> "
            f"/Contents {cid} 0 R >>"
        )
        page_ids.append(pid)
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    real_pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    assert real_pages_id == pages_id
    catalog = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    info = None
    if title or subject:
        fields = (f"/Title ({_esc(title)}) " if title else "") + (
            f"/Subject ({_esc(subject)}) " if subject else ""
        )
        info = add(f"<< {fields}/Producer (lectern-tests) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R"
    if info:
        trailer += f" /Info {info} 0 R"
    trailer += f" >>\nstartxref\n{xref}\n%%EOF\n"
    out += trailer.encode()
    path.write_bytes(bytes(out))
    return path


def lines(page: Page, x: float, y: float, texts: list[str], size: float = 11.0, **kw) -> float:
    """Lay consecutive lines down the page; returns the next free y."""
    for t in texts:
        page.add(t, x, y, size=size, **kw)
        y += size * 1.35
    return y
