"""A tiny DOCX writer for tests and the red-team generator.

Writes the few XML parts a .docx needs: paragraphs with a style (Heading1,
ListParagraph) and runs with colour, size and the hidden (`vanish`) flag.
Word opens the result; more importantly, `lectern` reads it back with every
run's style intact.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass
class RunSpec:
    text: str
    color: str | None = None  # "FFFFFF"
    size_pt: float | None = None
    hidden: bool = False
    bold: bool = False


@dataclass
class Para:
    runs: list[RunSpec] = field(default_factory=list)
    style: str | None = None  # "Heading1", "Heading2", "ListParagraph", "Title"

    @classmethod
    def text(cls, text: str, style: str | None = None, **kw) -> Para:
        return cls(runs=[RunSpec(text, **kw)], style=style)


def _run_xml(r: RunSpec) -> str:
    props = []
    if r.bold:
        props.append("<w:b/>")
    if r.hidden:
        props.append("<w:vanish/>")
    if r.color:
        props.append(f'<w:color w:val="{r.color}"/>')
    if r.size_pt is not None:
        props.append(f'<w:sz w:val="{int(round(r.size_pt * 2))}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(r.text)}</w:t></w:r>'


def _para_xml(p: Para) -> str:
    ppr = ""
    if p.style:
        ppr = (
            f'<w:pPr><w:pStyle w:val="{p.style}"/>'
            + (
                '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
                if p.style == "ListParagraph"
                else ""
            )
            + "</w:pPr>"
        )
    return f"<w:p>{ppr}{''.join(_run_xml(r) for r in p.runs)}</w:p>"


def write_docx(
    path: Path, paras: list[Para], *, title: str | None = None, description: str | None = None
) -> Path:
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>'
        + "".join(_para_xml(p) for p in paras)
        + "</w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
        'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        + (f"<dc:title>{escape(title)}</dc:title>" if title else "")
        + (f"<dc:description>{escape(description)}</dc:description>" if description else "")
        + "</cp:coreProperties>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
        'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-'
        'package.core-properties+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
        'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)
        zf.writestr("docProps/core.xml", core)
    return path
