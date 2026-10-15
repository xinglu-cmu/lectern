"""DOCX -> blocks with run-level style, straight from the XML.

A .docx is a zip; the text is in `word/document.xml` as paragraphs of runs, each
run with properties: the hidden flag (`w:vanish`), colour, size. MarkItDown
would hand us clean Markdown with all of that gone, so this converter reads the
XML itself (standard library only). Observations become flags and run styles:
`hidden:vanish` for hidden runs, and colour / size on each run so H1 and H2 can
judge white or 1pt text the same way they do for PDF. Document properties
(`docProps/core.xml`, `docProps/app.xml`) go into `Document.meta` for H5.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from lectern.models import Anchor, Block, BlockType, Document, Run, Style

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PROP_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}


def _run_style(rpr) -> tuple[Style, list[str]]:
    flags: list[str] = []
    style = Style()
    if rpr is None:
        return style, flags
    if rpr.find(f"{W}vanish") is not None:
        flags.append("hidden:vanish")
    color = rpr.find(f"{W}color")
    if color is not None:
        val = (color.get(f"{W}val") or "").lower()
        if re.fullmatch(r"[0-9a-f]{6}", val):
            style.color = f"#{val}"
    sz = rpr.find(f"{W}sz")
    if sz is not None and (sz.get(f"{W}val") or "").isdigit():
        style.font_size = int(sz.get(f"{W}val")) / 2  # half-points
    fonts = rpr.find(f"{W}rFonts")
    if fonts is not None:
        style.font_name = fonts.get(f"{W}ascii") or fonts.get(f"{W}hAnsi")
    return style, flags


def _paragraph(p) -> tuple[list[Run], str, int | None, bool]:
    ppr = p.find(f"{W}pPr")
    level = None
    is_list = False
    if ppr is not None:
        pstyle = ppr.find(f"{W}pStyle")
        if pstyle is not None:
            name = (pstyle.get(f"{W}val") or "").lower()
            m = re.fullmatch(r"(heading|berschrift|titre)(\d)", name) or re.fullmatch(
                r"heading(\d)", name
            )
            if m:
                level = int(m.groups()[-1])
            elif name == "title":
                level = 1
            elif "list" in name:
                is_list = True
        if ppr.find(f"{W}numPr") is not None:
            is_list = True
    runs: list[Run] = []
    for r in p.iter(f"{W}r"):
        texts = []
        for node in r:
            if node.tag == f"{W}t":
                texts.append(node.text or "")
            elif node.tag == f"{W}tab":
                texts.append("\t")
            elif node.tag in (f"{W}br", f"{W}cr"):
                texts.append("\n")
        text = "".join(texts)
        if not text:
            continue
        style, flags = _run_style(r.find(f"{W}rPr"))
        runs.append(Run(text=text, style=style, flags=flags))
    text = "".join(r.text for r in runs)
    return runs, text, level, is_list


class DocxConverter:
    name = "docx"
    formats = frozenset({"docx"})

    def convert(self, path: Path) -> Document:
        meta: dict[str, str] = {}
        blocks: list[Block] = []
        with zipfile.ZipFile(path) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
            for name in ("docProps/core.xml", "docProps/app.xml"):
                if name in zf.namelist():
                    try:
                        props = ET.fromstring(zf.read(name))
                    except ET.ParseError:
                        continue
                    for el in props.iter():
                        if el.text and el.text.strip() and "}" in el.tag:
                            key = el.tag.split("}", 1)[1].lower()
                            if key in (
                                "title",
                                "creator",
                                "description",
                                "subject",
                                "keywords",
                                "lastmodifiedby",
                                "company",
                                "manager",
                                "category",
                                "comments",
                            ):
                                meta[key] = el.text.strip()
        body = root.find(f"{W}body")
        if body is None:
            return Document(
                source=str(path), format="docx", converter=self.name, meta=meta, blocks=[]
            )

        def add(btype: BlockType, text: str, runs: list[Run], level=None, extra_flags=()) -> None:
            text = text.strip()
            if not text:
                return
            flags = sorted(
                {f for r in runs for f in r.flags if f.startswith("hidden:")} | set(extra_flags)
            )
            if flags and any(f.startswith("hidden:") for f in flags):
                # only whole-paragraph hiding is a block flag; partial hiding stays on the runs
                visible = sum(
                    len(r.text) for r in runs if not any(x.startswith("hidden:") for x in r.flags)
                )
                if visible > 0:
                    flags = [f for f in flags if not f.startswith("hidden:")]
            dominant = max(runs, key=lambda r: len(r.text)).style if runs else Style()
            blocks.append(
                Block(
                    type=btype,
                    text=text,
                    level=level,
                    style=dominant.model_copy(),
                    runs=runs,
                    flags=flags,
                    anchor=Anchor(block=len(blocks)),
                )
            )

        for el in body:
            if el.tag == f"{W}p":
                runs, text, level, is_list = _paragraph(el)
                if level:
                    add(BlockType.heading, text, runs, level=level)
                elif is_list:
                    add(BlockType.list_item, "- " + text, runs)
                else:
                    add(BlockType.paragraph, text, runs)
            elif el.tag == f"{W}tbl":
                rows = []
                all_runs: list[Run] = []
                for tr in el.iter(f"{W}tr"):
                    cells = []
                    for tc in tr.findall(f"{W}tc"):
                        parts = []
                        for p in tc.iter(f"{W}p"):
                            runs, text, _, _ = _paragraph(p)
                            all_runs += runs
                            parts.append(text)
                        cells.append(" ".join(" ".join(parts).split()))
                    rows.append("| " + " | ".join(cells) + " |")
                add(BlockType.table, "\n".join(rows), all_runs)
        title = meta.get("title") or next(
            (b.text for b in blocks if b.type is BlockType.heading and b.level == 1), None
        )
        return Document(
            source=str(path),
            format="docx",
            converter=self.name,
            title=title,
            meta=meta,
            blocks=blocks,
        )
