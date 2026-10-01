"""HTML -> blocks, keeping what the page would hide from a reader.

MarkItDown gives good Markdown for HTML but strips every style, so a
`display:none` paragraph reads like any other. This converter walks the DOM
itself (BeautifulSoup, already a MarkItDown dependency) and records, per block,
the ways the page hides it: inline or `<style>` rules for `display:none`,
`visibility:hidden`, `font-size:0`, `opacity:0`, off-screen positioning, text
coloured like its background, the `hidden` attribute, and HTML comments. Those
observations become `hidden:<reason>` flags; detector H4 turns them into
findings. The text itself is kept — nothing is dropped at load time.

`<meta>` tags and the `<title>` go into `Document.meta` for H5.
"""

from __future__ import annotations

import re
from pathlib import Path

from lectern.models import Anchor, Block, BlockType, Document, Style

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
BLOCK_TAGS = {
    "p",
    "li",
    "pre",
    "table",
    "blockquote",
    "div",
    "section",
    "article",
    "td",
    "th",
} | set(HEADINGS)
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}
CONTAINER_TAGS = {
    "body",
    "html",
    "main",
    "nav",
    "footer",
    "header",
    "aside",
    "ul",
    "ol",
    "dl",
    "form",
    "tr",
    "tbody",
    "thead",
}
_DECL = re.compile(r"([a-z-]+)\s*:\s*([^;]+)")
_OFFSCREEN = re.compile(r"-?\d{4,}px|-100%|-9999")


def _parse_style(text: str) -> dict[str, str]:
    return {k.strip().lower(): v.strip().lower() for k, v in _DECL.findall(text or "")}


def _stylesheet_rules(soup) -> list[tuple[str, dict[str, str]]]:
    """Very small CSS reader: `.cls { ... }`, `#id { ... }`, `tag { ... }` only."""
    rules = []
    for st in soup.find_all("style"):
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", st.get_text() or ""):
            decls = _parse_style(m.group(2))
            for sel in m.group(1).split(","):
                sel = sel.strip().lower()
                if re.fullmatch(r"[.#]?[a-z0-9_-]+", sel):
                    rules.append((sel, decls))
    return rules


def _css_for(el, rules) -> dict[str, str]:
    out: dict[str, str] = {}
    classes = {c.lower() for c in (el.get("class") or [])}
    el_id = (el.get("id") or "").lower()
    for sel, decls in rules:
        if (
            sel == el.name
            or (sel.startswith(".") and sel[1:] in classes)
            or (sel.startswith("#") and sel[1:] == el_id)
        ):
            out.update(decls)
    out.update(_parse_style(el.get("style")))
    return out


def _parse_color(value: str | None) -> tuple[float, float, float] | None:
    if not value:
        return None
    v = value.strip().lower()
    named = {"white": (1, 1, 1), "black": (0, 0, 0), "transparent": None}
    if v in named:
        return named[v]
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    m = re.fullmatch(r"rgba?\(([^)]+)\)", v)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
        try:
            nums = [float(p.rstrip("%")) / (100 if p.endswith("%") else 255) for p in parts[:3]]
        except ValueError:
            return None
        if len(parts) > 3:
            try:
                if float(parts[3].rstrip("%")) == 0:
                    return None
            except ValueError:
                pass
        return (nums[0], nums[1], nums[2])
    return None


def hiding_reasons(
    css: dict[str, str], inherited_bg: tuple[float, float, float] | None
) -> list[str]:
    reasons = []
    if css.get("display") == "none":
        reasons.append("display-none")
    if css.get("visibility") in ("hidden", "collapse"):
        reasons.append("visibility-hidden")
    fs = css.get("font-size", "")
    if re.fullmatch(r"0(\.0+)?(px|pt|em|rem|%)?", fs) or re.fullmatch(r"0?\.\d+px", fs):
        reasons.append("font-size-0")
    if re.fullmatch(r"0(\.0+)?", css.get("opacity", "")):
        reasons.append("opacity-0")
    if css.get("position") in ("absolute", "fixed") and any(
        _OFFSCREEN.search(css.get(k, "")) for k in ("left", "top", "right", "bottom", "text-indent")
    ):
        reasons.append("offscreen")
    if _OFFSCREEN.search(css.get("text-indent", "")):
        reasons.append("offscreen")
    fg = _parse_color(css.get("color"))
    bg = _parse_color(css.get("background-color") or css.get("background")) or inherited_bg
    if (
        fg is not None
        and bg is not None
        and max(abs(a - b) for a, b in zip(fg, bg, strict=True)) < 0.06
    ):
        reasons.append("fg-bg")
    if css.get("width") in ("0", "0px") or css.get("height") in ("0", "0px"):
        reasons.append("zero-size")
    return reasons


class HtmlConverter:
    name = "html"
    formats = frozenset({"html", "htm"})

    def convert(self, path: Path) -> Document:
        from bs4 import BeautifulSoup, Comment

        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
        meta: dict[str, str] = {}
        if soup.title and soup.title.string:
            meta["title"] = soup.title.string.strip()
        for tag in soup.find_all("meta"):
            key = tag.get("name") or tag.get("property") or tag.get("http-equiv")
            if key and tag.get("content"):
                meta[f"meta:{key.lower()}"] = str(tag.get("content")).strip()
        rules = _stylesheet_rules(soup)
        blocks: list[Block] = []

        def add(btype: BlockType, text: str, level=None, flags=None, color=None) -> None:
            if btype is BlockType.code:
                text = text.strip("\n")
            elif btype is BlockType.table:
                text = "\n".join(" ".join(row.split()) for row in text.splitlines() if row.strip())
            else:
                text = " ".join(text.split())
            if not text:
                return
            blocks.append(
                Block(
                    type=btype,
                    text=text,
                    level=level,
                    flags=list(flags or []),
                    style=Style(color=color),
                    anchor=Anchor(block=len(blocks)),
                )
            )

        body = soup.body or soup

        def walk(el, inherited: list[str], bg) -> None:
            """Block children become blocks; runs of inline content pool into one paragraph."""
            inline: list[str] = []

            def flush_inline() -> None:
                text = " ".join(" ".join(inline).split())
                inline.clear()
                if text:
                    add(BlockType.paragraph, text, flags=[f"hidden:{r}" for r in inherited])

            for child in list(el.children):
                if isinstance(child, Comment):
                    flush_inline()
                    txt = " ".join(str(child).split())
                    if txt:
                        add(BlockType.other, txt, flags=["hidden:comment"])
                    continue
                name = getattr(child, "name", None)
                if name is None:
                    inline.append(str(child))
                    continue
                if name in SKIP_TAGS:
                    continue
                css = _css_for(child, rules)
                reasons = list(inherited)
                if child.has_attr("hidden"):
                    reasons.append("hidden-attr")
                reasons += hiding_reasons(css, bg)
                reasons = list(dict.fromkeys(reasons))
                child_bg = _parse_color(css.get("background-color") or css.get("background")) or bg
                flags = [f"hidden:{r}" for r in reasons]
                has_block_inside = child.find(BLOCK_TAGS) is not None
                if name not in BLOCK_TAGS and name not in CONTAINER_TAGS and not has_block_inside:
                    if reasons != inherited:
                        flush_inline()
                        add(BlockType.paragraph, child.get_text(" "), flags=flags)
                    else:
                        inline.append(
                            child.get_text(" ")
                        )  # <a>, <b>, <span>, … stay in the paragraph
                    continue
                flush_inline()
                if name in HEADINGS:
                    add(BlockType.heading, child.get_text(" "), level=HEADINGS[name], flags=flags)
                elif name == "pre":
                    add(BlockType.code, child.get_text(), flags=flags)
                elif name == "table":
                    rows = []
                    for tr in child.find_all("tr"):
                        cells = [
                            " ".join(td.get_text(" ").split()) for td in tr.find_all(["td", "th"])
                        ]
                        rows.append("| " + " | ".join(cells) + " |")
                    add(BlockType.table, "\n".join(rows), flags=flags)
                elif name == "li":
                    own = child.find_all(["ul", "ol"])
                    for sub in own:
                        sub.extract()
                    add(BlockType.list_item, "- " + child.get_text(" "), flags=flags)
                    for sub in own:
                        walk(sub, reasons, child_bg)
                elif (
                    name in ("p", "blockquote", "td", "th", "figcaption", "dt", "dd")
                    and not has_block_inside
                ):
                    add(BlockType.paragraph, child.get_text(" "), flags=flags)
                elif name in ("nav", "footer", "header", "aside"):
                    before = len(blocks)
                    walk(child, reasons, child_bg)
                    for b in blocks[before:]:
                        b.flags.append(name)
                else:
                    walk(child, reasons, child_bg)
            flush_inline()

        # A page with no declared background is white: white text on it is hidden.
        body_css = _css_for(body, rules) if getattr(body, "name", None) else {}
        page_bg = _parse_color(body_css.get("background-color") or body_css.get("background")) or (
            1.0,
            1.0,
            1.0,
        )
        walk(body, [f"hidden:{r}" for r in []], page_bg)
        title = meta.get("title") or next(
            (b.text for b in blocks if b.type is BlockType.heading and b.level == 1), None
        )
        return Document(
            source=str(path),
            format=path.suffix.lower().lstrip("."),
            converter=self.name,
            title=title,
            meta=meta,
            blocks=blocks,
        )
