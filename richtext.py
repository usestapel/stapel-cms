"""The rich-text document: a typed ProseMirror/TipTap JSON subset.

Why a document and not sanitised HTML: no HTML ever reaches a renderer, so
there is no sanitiser to get wrong (docs/SPEC.md §5). Every node and mark is
a pydantic model with ``extra="forbid"`` — the document arrives from an
editor and is untrusted structured text. An unknown node, an unknown
attribute (``style``, ``class``, ``onclick``) or an unsafe link is a
validation error, never something to clean.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .safety import is_media_ref, is_safe_url

MAX_DEPTH = 12
MAX_NODES = 5000
#: A text leaf may be longer than a translation provider accepts per text;
#: machine translation splits it at sentence boundaries and rejoins it.
TEXT_MAX = 20_000
#: JSON-schema marker of a rich document (block walkers translate its text nodes).
RICHTEXT_KEY = "x-cms-richtext"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


# ── Marks ──────────────────────────────────────────────────────────────────


class BoldMark(_Strict):
    type: Literal["bold"]


class ItalicMark(_Strict):
    type: Literal["italic"]


class UnderlineMark(_Strict):
    type: Literal["underline"]


class StrikeMark(_Strict):
    type: Literal["strike"]


class CodeMark(_Strict):
    type: Literal["code"]


class LinkAttrs(_Strict):
    href: str = Field(max_length=2000)
    new_tab: bool = False

    @field_validator("href")
    @classmethod
    def _safe(cls, value: str) -> str:
        if not is_safe_url(value):
            raise ValueError("unsafe link")
        return value


class LinkMark(_Strict):
    type: Literal["link"]
    attrs: LinkAttrs


Mark = Annotated[
    Union[BoldMark, ItalicMark, UnderlineMark, StrikeMark, CodeMark, LinkMark],
    Field(discriminator="type"),
]


# ── Inline nodes ───────────────────────────────────────────────────────────


class TextNode(_Strict):
    type: Literal["text"]
    text: str = Field(min_length=1, max_length=TEXT_MAX)
    marks: list[Mark] = Field(default_factory=list, max_length=6)


class HardBreak(_Strict):
    type: Literal["hardBreak"]


Inline = Annotated[Union[TextNode, HardBreak], Field(discriminator="type")]


# ── Block nodes ────────────────────────────────────────────────────────────


class Paragraph(_Strict):
    type: Literal["paragraph"]
    content: list[Inline] = Field(default_factory=list, max_length=2000)


class HeadingAttrs(_Strict):
    level: int = Field(ge=1, le=6)


class Heading(_Strict):
    type: Literal["heading"]
    attrs: HeadingAttrs
    content: list[Inline] = Field(default_factory=list, max_length=2000)


class CodeBlockAttrs(_Strict):
    language: Optional[str] = Field(default=None, max_length=32, pattern=r"^[a-z0-9+#-]*$")


class CodeBlock(_Strict):
    type: Literal["codeBlock"]
    attrs: CodeBlockAttrs = Field(default_factory=CodeBlockAttrs)
    content: list[TextNode] = Field(default_factory=list, max_length=2000)


class HorizontalRule(_Strict):
    type: Literal["horizontalRule"]


class ImageAttrs(_Strict):
    media: str = Field(max_length=200)
    alt: str = Field(default="", max_length=300)
    title: Optional[str] = Field(default=None, max_length=300)

    @field_validator("media")
    @classmethod
    def _media(cls, value: str) -> str:
        if not is_media_ref(value):
            raise ValueError("media must be a cdn reference <type>/<id>")
        return value


class Image(_Strict):
    type: Literal["image"]
    attrs: ImageAttrs


class ListItem(_Strict):
    type: Literal["listItem"]
    content: list["Block"] = Field(min_length=1, max_length=200)


class BulletList(_Strict):
    type: Literal["bulletList"]
    content: list[ListItem] = Field(min_length=1, max_length=1000)


class OrderedListAttrs(_Strict):
    start: int = Field(default=1, ge=1, le=100_000)


class OrderedList(_Strict):
    type: Literal["orderedList"]
    attrs: OrderedListAttrs = Field(default_factory=OrderedListAttrs)
    content: list[ListItem] = Field(min_length=1, max_length=1000)


class Blockquote(_Strict):
    type: Literal["blockquote"]
    content: list["Block"] = Field(min_length=1, max_length=200)


Block = Annotated[
    Union[Paragraph, Heading, CodeBlock, HorizontalRule, Image, BulletList, OrderedList, Blockquote],
    Field(discriminator="type"),
]


class RichDoc(_Strict):
    """The root node. ``content`` is the document's block list."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={RICHTEXT_KEY: True})

    type: Literal["doc"]
    content: list[Block] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="before")
    @classmethod
    def _bounded(cls, data: Any) -> Any:
        depth, nodes = _measure(data)
        if depth > MAX_DEPTH:
            raise ValueError(f"document nested deeper than {MAX_DEPTH}")
        if nodes > MAX_NODES:
            raise ValueError(f"document has more than {MAX_NODES} nodes")
        return data


ListItem.model_rebuild()
Blockquote.model_rebuild()
RichDoc.model_rebuild()


def _measure(node: Any, depth: int = 1) -> tuple[int, int]:
    """(depth, node count) of a raw document, bounded before pydantic recurses."""
    if depth > MAX_DEPTH + 1:
        return depth, 1
    if not isinstance(node, dict):
        return depth, 1
    deepest, count = depth, 1
    children = node.get("content")
    if isinstance(children, list):
        for child in children:
            child_depth, child_count = _measure(child, depth + 1)
            deepest = max(deepest, child_depth)
            count += child_count
            if count > MAX_NODES:
                return deepest, count
    return deepest, count


def map_doc_text(node, fn):
    """A copy of a raw document with each human text replaced by ``fn(text)``.

    Text nodes are mapped one by one, so marks and structure stay as they
    are; image ``alt``/``title`` are text too. Code (a ``codeBlock``, a text
    node with a ``code`` mark) is left untranslated.
    """
    if isinstance(node, list):
        return [map_doc_text(child, fn) for child in node]
    if not isinstance(node, dict):
        return node
    kind = node.get("type")
    if kind == "codeBlock":
        return node
    out = dict(node)
    if kind == "text" and isinstance(node.get("text"), str):
        is_code = any(isinstance(m, dict) and m.get("type") == "code" for m in node.get("marks") or [])
        if not is_code and node["text"].strip():
            out["text"] = fn(node["text"])
    elif kind == "image" and isinstance(node.get("attrs"), dict):
        attrs = dict(node["attrs"])
        for key in ("alt", "title"):
            if isinstance(attrs.get(key), str) and attrs[key].strip():
                attrs[key] = fn(attrs[key])
        out["attrs"] = attrs
    if isinstance(node.get("content"), list):
        out["content"] = map_doc_text(node["content"], fn)
    return out


def empty_doc() -> dict:
    return {"type": "doc", "content": []}


def paragraph_doc(*paragraphs: str) -> dict:
    """A document of plain paragraphs (seed content, tests)."""
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]} for text in paragraphs
        ],
    }


__all__ = ["MAX_DEPTH", "MAX_NODES", "RICHTEXT_KEY", "TEXT_MAX", "RichDoc", "empty_doc", "map_doc_text", "paragraph_doc"]
