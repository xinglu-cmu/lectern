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
class Page:
    items: list[Text] = field(default_factory=list)

    def add(self, text: str, x: float, y: float, **kw) -> Page:
        self.items.append(Text(text, x, y, **kw))
        return self


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content(page: Page) -> bytes:
    ops = []
    for t in page.items:
        font = "/F2" if t.bold else "/F1"
        r, g, b = t.color
        baseline = PAGE_H - t.y - t.size  # y is the top of the text box
        ops.append(
            f"BT {font} {t.size:.1f} Tf {r:.3f} {g:.3f} {b:.3f} rg "
            f"1 0 0 1 {t.x:.1f} {baseline:.1f} Tm ({_esc(t.text)}) Tj ET"
        )
    return ("\n".join(ops) + "\n").encode("latin-1", errors="replace")


def write_pdf(path: Path, pages: list[Page], title: str | None = None) -> Path:
    objs: list[bytes] = []

    def add(body: str | bytes) -> int:
        objs.append(body if isinstance(body, bytes) else body.encode("latin-1"))
        return len(objs)

    font1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    pages_id = len(objs) + 1 + 2 * len(pages)  # reserved after page + content objects
    page_ids = []
    for page in pages:
        content = _content(page)
        cid = add(b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream")
        pid = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
            f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> /Contents {cid} 0 R >>"
        )
        page_ids.append(pid)
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    real_pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    assert real_pages_id == pages_id
    catalog = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    info = add(f"<< /Title ({_esc(title)}) /Producer (lectern-tests) >>") if title else None

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
