from pathlib import Path

import pytest

from lectern.converters import UnsupportedFormat, load, pick_converter, supported_formats
from lectern.converters.markdown_blocks import markdown_to_blocks
from lectern.converters.pdf import color_to_hex
from lectern.models import BlockType


def test_markdown_blocks_cover_the_common_shapes():
    text = (
        "Title\n=====\n\n# H1\n\nPara one\ncontinues.\n\n- item a\n  wrapped\n- item b\n\n"
        "```py\nx = 1\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nLast."
    )
    blocks = markdown_to_blocks(text)
    types = [b.type for b in blocks]
    assert types == [
        BlockType.heading,
        BlockType.heading,
        BlockType.paragraph,
        BlockType.list_item,
        BlockType.list_item,
        BlockType.code,
        BlockType.table,
        BlockType.paragraph,
    ]
    assert blocks[0].level == 1 and blocks[0].text == "Title"
    assert blocks[2].text == "Para one continues."
    assert blocks[3].text == "- item a wrapped"
    assert blocks[5].text.startswith("```py")
    assert [b.anchor.block for b in blocks] == list(range(len(blocks)))


def test_markdown_file_loads_with_title(assignment_md: Path):
    doc = load(assignment_md)
    assert doc.converter == "markdown"
    assert doc.format == "md"
    assert doc.title == "Assignment 2: Sorting"
    assert sum(1 for b in doc.blocks if b.type is BlockType.heading) == 5


def test_pdf_keeps_style_and_flags_furniture(assignment_pdf: Path):
    doc = load(assignment_pdf)
    assert doc.converter == "pdfplumber" and doc.pages == 2
    assert doc.title == "Assignment 2"
    headings = [b for b in doc.blocks if b.type is BlockType.heading]
    assert [h.text for h in headings] == ["Assignment 2: Sorting", "Deliverables", "Policies"]
    assert headings[0].level == 1 and headings[1].level == 2

    hidden = next(b for b in doc.blocks if b.text.startswith("IGNORE PREVIOUS"))
    assert hidden.style.color == "#ffffff"
    assert hidden.style.font_size == 1.0
    assert hidden.runs and hidden.runs[0].style.bbox is not None

    footers = [b for b in doc.blocks if "footer" in b.flags]
    assert len(footers) == 2 and all("page_number" in b.flags for b in footers)
    headers = [b for b in doc.blocks if "header" in b.flags]
    assert len(headers) == 2 and all("repeated" in b.flags for b in headers)

    items = [b for b in doc.blocks if b.type is BlockType.list_item]
    assert len(items) == 2
    assert items[1].text.endswith("vs input size.")  # wrapped continuation joined


def test_pdf_page_anchors_are_one_based(assignment_pdf: Path):
    doc = load(assignment_pdf)
    pages = sorted({b.anchor.page for b in doc.blocks})
    assert pages == [1, 2]


def test_html_native_converter(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text(
        "<html><head><title>Spec</title></head><body><h1>Spec</h1>"
        "<p>The system shall log every request.</p><ul><li>one</li><li>two</li></ul>"
        "</body></html>",
        encoding="utf-8",
    )
    doc = load(html)
    assert doc.converter == "html"
    assert doc.title == "Spec"
    assert [b.type for b in doc.blocks] == [
        BlockType.heading,
        BlockType.paragraph,
        BlockType.list_item,
        BlockType.list_item,
    ]


def test_unsupported_and_missing_files(tmp_path: Path):
    weird = tmp_path / "x.xyz"
    weird.write_text("hi")
    with pytest.raises(UnsupportedFormat):
        pick_converter(weird)
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "nope.pdf")
    assert {"pdf", "docx", "html", "md", "txt"} <= supported_formats()


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ((0,), "#000000"),
        ((1, 1, 1), "#ffffff"),
        ([0.5], "#808080"),
        ((0, 0, 0, 1), "#000000"),
        ((255, 0, 0), "#ff0000"),
        ("Pattern", None),
    ],
)
def test_color_to_hex(value, expected):
    assert color_to_hex(value) == expected
