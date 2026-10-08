from pathlib import Path

from lectern.converters import load
from lectern.models import Anchor, Block, BlockType, Document
from lectern.segment import MAX_TOKENS, MIN_TOKENS, est_tokens, segment


def _doc(blocks: list[tuple[BlockType, str, int | None]], flags=None) -> Document:
    out = []
    for i, (t, text, level) in enumerate(blocks):
        out.append(
            Block(
                type=t,
                text=text,
                level=level,
                flags=(flags or {}).get(i, []),
                anchor=Anchor(block=i),
            )
        )
    return Document(source="x.md", format="md", converter="test", blocks=out)


def test_headings_bound_segments_and_build_paths(assignment_md: Path):
    segs = segment(load(assignment_md))
    paths = [s.heading_path for s in segs]
    assert paths[0] == ["Assignment 2: Sorting"]
    assert ["Assignment 2: Sorting", "Deliverables"] in paths
    assert ["Assignment 2: Sorting", "Policies"] in paths
    assert [s.id for s in segs] == [f"s{i}" for i in range(1, len(segs) + 1)]
    assert all(s.anchor.block_start <= s.anchor.block_end for s in segs)
    code = next(s for s in segs if "code_heavy" in s.flags)
    assert code.heading_path[-1] == "Example"


def test_paragraphs_are_pooled_up_to_the_ceiling():
    para = "Sentence number one is here. " * 8  # ~60 tokens each
    doc = _doc([(BlockType.heading, "Long", 1)] + [(BlockType.paragraph, para, None)] * 12)
    segs = segment(doc)
    assert len(segs) > 1
    assert all(s.tokens_est <= MAX_TOKENS * 1.25 for s in segs)
    assert all(s.tokens_est >= MIN_TOKENS for s in segs[:-1])
    assert all(s.heading_path == ["Long"] for s in segs)


def test_huge_paragraph_is_split_at_sentence_ends():
    para = " ".join(f"This is sentence {i} of a very long paragraph." for i in range(200))
    assert est_tokens(para) > MAX_TOKENS * 1.5
    segs = segment(_doc([(BlockType.paragraph, para, None)]))
    assert len(segs) >= 3
    assert all(s.text.endswith(".") for s in segs)
    assert " ".join(s.text for s in segs) == para


def test_furniture_blocks_form_their_own_segments():
    doc = _doc(
        [
            (BlockType.other, "Header", None),
            (BlockType.heading, "Intro", 1),
            (BlockType.paragraph, "Body text here.", None),
            (BlockType.other, "Page 1", None),
            (BlockType.other, "Header", None),
            (BlockType.paragraph, "More body.", None),
        ],
        flags={0: ["header", "repeated"], 3: ["footer", "page_number"], 4: ["header", "repeated"]},
    )
    segs = segment(doc)
    furn = [s for s in segs if set(s.flags) & {"header", "footer"}]
    assert len(furn) == 2  # the p1 footer + p2 header are adjacent and pooled
    assert "page_number" in furn[1].flags
    body = [s for s in segs if s not in furn]
    assert body[0].text.startswith("# Intro")


def test_pdf_bullets_render_as_markdown_dashes(assignment_pdf: Path):
    segs = segment(load(assignment_pdf))
    deliverables = next(s for s in segs if s.heading_path[-1:] == ["Deliverables"])
    assert "\n\n1. Implement" in deliverables.text
    assert deliverables.anchor.page_start == 1
