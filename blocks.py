"""The typed block registry.

A page or post body is a list of ``{"type", "id", "data"}`` blocks. Each type
names a pydantic model (``extra="forbid"``) that validates ``data``; the
registry is MERGE-over-built-ins:

    STAPEL_CMS = {"BLOCK_TYPES": {
        "pricing_table": "myapp.blocks.PricingTable",   # a project's own block
        "listing_rail": None,                          # remove a built-in
    }}

``register_block_type()`` is the runtime door (an ``AppConfig.ready()``).
The block JSON schemas (``model_json_schema()``) are published to the staff
editor through ``GET staff/block-types/``.
"""
from __future__ import annotations

import json
import re
import threading
from typing import Literal, Optional

from django.utils.module_loading import import_string
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .richtext import RichDoc
from .safety import embed_host_allowed, is_media_ref, is_safe_url

BLOCK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
BLOCK_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")

#: String keys whose values are human text (translated, counted for reading
#: time). Everything else (urls, media refs, ids, opaque queries) is left alone.
TEXT_KEYS = frozenset({"text", "heading", "subheading", "label", "question", "title", "caption", "alt"})
#: Subtrees no walker enters.
OPAQUE_KEYS = frozenset({"query"})


class BlockData(BaseModel):
    """Base of every block model: unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")


def _media(value: Optional[str]) -> Optional[str]:
    if value is not None and not is_media_ref(value):
        raise ValueError("media must be a cdn reference <type>/<id>")
    return value


class RichTextBlock(BlockData):
    doc: RichDoc


class CallToAction(BlockData):
    label: str = Field(min_length=1, max_length=80)
    href: str = Field(max_length=2000)

    @field_validator("href")
    @classmethod
    def _safe(cls, value: str) -> str:
        if not is_safe_url(value):
            raise ValueError("unsafe link")
        return value


class HeroBlock(BlockData):
    heading: str = Field(min_length=1, max_length=200)
    subheading: Optional[str] = Field(default=None, max_length=500)
    media: Optional[str] = Field(default=None, max_length=200)
    cta: Optional[CallToAction] = None
    align: Literal["start", "center"] = "start"

    @field_validator("media")
    @classmethod
    def _check_media(cls, value):
        return _media(value)


class FaqItem(BlockData):
    question: str = Field(min_length=1, max_length=300)
    answer: RichDoc


class FaqBlock(BlockData):
    title: Optional[str] = Field(default=None, max_length=200)
    items: list[FaqItem] = Field(min_length=1, max_length=100)


class GalleryItem(BlockData):
    media: str = Field(max_length=200)
    alt: str = Field(default="", max_length=300)
    caption: Optional[str] = Field(default=None, max_length=300)

    @field_validator("media")
    @classmethod
    def _check_media(cls, value):
        return _media(value)


class GalleryBlock(BlockData):
    layout: Literal["grid", "carousel"] = "grid"
    items: list[GalleryItem] = Field(min_length=1, max_length=60)


class EmbedBlock(BlockData):
    url: str = Field(max_length=2000)
    title: str = Field(min_length=1, max_length=200)
    aspect_ratio: Literal["16:9", "4:3", "1:1", "9:16"] = "16:9"

    @field_validator("url")
    @classmethod
    def _allowed_host(cls, value: str) -> str:
        from .conf import cms_settings

        if not embed_host_allowed(value, cms_settings.EMBED_HOSTS):
            raise ValueError("embed url must be https on an allowed host (EMBED_HOSTS)")
        return value


class FormBlock(BlockData):
    form_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    title: Optional[str] = Field(default=None, max_length=200)


class ListingRailBlock(BlockData):
    title: Optional[str] = Field(default=None, max_length=200)
    source: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_.-]*$")
    query: dict = Field(default_factory=dict)
    limit: int = Field(default=8, ge=1, le=24)

    @field_validator("query")
    @classmethod
    def _small(cls, value: dict) -> dict:
        if len(json.dumps(value, separators=(",", ":"))) > 2048:
            raise ValueError("query is larger than 2 KiB")
        return value


BUILTIN_BLOCK_TYPES: dict[str, str] = {
    "rich_text": "stapel_cms.blocks.RichTextBlock",
    "hero": "stapel_cms.blocks.HeroBlock",
    "faq": "stapel_cms.blocks.FaqBlock",
    "gallery": "stapel_cms.blocks.GalleryBlock",
    "embed": "stapel_cms.blocks.EmbedBlock",
    "form": "stapel_cms.blocks.FormBlock",
    "listing_rail": "stapel_cms.blocks.ListingRailBlock",
}

_runtime: dict[str, Optional[str]] = {}
_lock = threading.Lock()


def register_block_type(name: str, model: Optional[str | type]) -> None:
    """Add (or with ``None`` remove) a block type at runtime."""
    if not BLOCK_TYPE_RE.match(name):
        raise ValueError(f"block type {name!r} must match {BLOCK_TYPE_RE.pattern}")
    if model is not None and not isinstance(model, str):
        model = f"{model.__module__}.{model.__qualname__}"
    with _lock:
        _runtime[name] = model


def reset_block_types() -> None:
    """Drop runtime registrations (a test lever)."""
    with _lock:
        _runtime.clear()


def get_block_types() -> dict[str, str]:
    """The effective registry: built-ins <- settings <- runtime; ``None`` removes."""
    from .conf import cms_settings

    merged: dict[str, Optional[str]] = dict(BUILTIN_BLOCK_TYPES)
    merged.update(cms_settings.BLOCK_TYPES or {})
    with _lock:
        merged.update(_runtime)
    return {name: path for name, path in merged.items() if path}


def block_model(name: str) -> type[BaseModel]:
    path = get_block_types().get(name)
    if path is None:
        raise KeyError(name)
    model = import_string(path)
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"block type {name!r}: {path} is not a pydantic model")
    return model


class BlockError(Exception):
    """A block list refusal: the error key and its params."""

    def __init__(self, key: str, params: dict | None = None):
        self.key = key
        self.params = params or {}
        super().__init__(key)


def _first_error(exc: ValidationError) -> str:
    err = exc.errors()[0]
    where = ".".join(str(p) for p in err.get("loc", ()))
    return f"{where}: {err.get('msg', 'invalid')}"[:300]


def validate_blocks(raw) -> list[dict]:
    """Validate a block list; return its normalised JSON. Raises :class:`BlockError`."""
    from .conf import cms_settings
    from .errors import ERR_400_BLOCK_TYPE_UNKNOWN, ERR_400_BLOCKS_INVALID, ERR_400_BLOCKS_TOO_LARGE

    max_blocks = int(cms_settings.MAX_BLOCKS)
    max_bytes = int(cms_settings.MAX_BLOCKS_BYTES)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BlockError(ERR_400_BLOCKS_INVALID, {"detail": "blocks must be a list"})
    if len(raw) > max_blocks or len(json.dumps(raw, separators=(",", ":"))) > max_bytes:
        raise BlockError(ERR_400_BLOCKS_TOO_LARGE, {"max_blocks": max_blocks, "max_bytes": max_bytes})
    seen: set[str] = set()
    out: list[dict] = []
    for index, block in enumerate(raw):
        if not isinstance(block, dict) or set(block) - {"type", "id", "data"}:
            raise BlockError(ERR_400_BLOCKS_INVALID, {"detail": f"{index}: a block is {{type, id, data}}"})
        btype, bid = block.get("type"), block.get("id")
        if not isinstance(bid, str) or not BLOCK_ID_RE.match(bid) or bid in seen:
            raise BlockError(ERR_400_BLOCKS_INVALID, {"detail": f"{index}.id: missing, malformed or repeated"})
        seen.add(bid)
        try:
            model = block_model(str(btype))
        except KeyError:
            raise BlockError(ERR_400_BLOCK_TYPE_UNKNOWN, {"type": str(btype)[:48]}) from None
        try:
            data = model.model_validate(block.get("data") or {})
        except ValidationError as exc:
            raise BlockError(ERR_400_BLOCKS_INVALID, {"detail": f"{index}.{_first_error(exc)}"}) from None
        out.append({"type": btype, "id": bid, "data": data.model_dump(mode="json", exclude_none=True)})
    return out


def block_type_schemas() -> list[dict]:
    """``[{type, schema}]`` for every registered type, sorted by type."""
    return [{"type": name, "schema": block_model(name).model_json_schema()} for name in sorted(get_block_types())]


def iter_text(node):
    """Every human-text string under ``node`` (see TEXT_KEYS / OPAQUE_KEYS)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in OPAQUE_KEYS:
                continue
            if key in TEXT_KEYS and isinstance(value, str):
                yield value
            else:
                yield from iter_text(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_text(item)


def map_text(node, fn):
    """A copy of ``node`` with every human-text string replaced by ``fn(text)``."""
    if isinstance(node, dict):
        return {
            key: (fn(value) if key in TEXT_KEYS and isinstance(value, str)
                  else value if key in OPAQUE_KEYS else map_text(value, fn))
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [map_text(item, fn) for item in node]
    return node


def media_refs(node) -> set[str]:
    """Every cdn reference under ``node`` (``media`` keys)."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in OPAQUE_KEYS:
                continue
            if key == "media" and isinstance(value, str) and is_media_ref(value):
                found.add(value)
            else:
                found |= media_refs(value)
    elif isinstance(node, list):
        for item in node:
            found |= media_refs(item)
    return found


def word_count(blocks) -> int:
    return sum(len(text.split()) for text in iter_text(blocks))


__all__ = [
    "BUILTIN_BLOCK_TYPES",
    "BlockData",
    "BlockError",
    "block_model",
    "block_type_schemas",
    "get_block_types",
    "iter_text",
    "map_text",
    "media_refs",
    "register_block_type",
    "reset_block_types",
    "validate_blocks",
    "word_count",
]
