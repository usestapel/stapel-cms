"""Optional machine translation of a locale variant, through a comm Function.

``MACHINE_TRANSLATE`` names a Function answering the contract in
``schemas/functions/machine_translate.json`` (stapel-translate's
``translate.text``): ``{texts, source, target}`` -> ``{texts}``, same length
and order. What is sent is human text only — the plain fields, the strings
block schemas mark translatable and the text nodes of rich documents, one by
one (never serialized JSON, so marks and structure survive).

The provider bounds a request (``MACHINE_TRANSLATE_MAX_TEXT_CHARS`` per text,
``MACHINE_TRANSLATE_MAX_ITEMS`` / ``MACHINE_TRANSLATE_MAX_CHARS`` per call):
a longer text is split at sentence boundaries (then whitespace, then hard)
and rejoined with its own separators, and a big page becomes several
sequential calls, each with ``MACHINE_TRANSLATE_TIMEOUT_SECONDS``.

Everything is translated before anything is written: a failure on any call
— unset, unreachable, unavailable, a refusal, a malformed answer — is a 503
with a ``reason`` and no variant is created.
"""
from __future__ import annotations

import logging
import re

from ..blocks import map_text
from ..errors import ERR_503_TRANSLATION_UNAVAILABLE
from . import CmsError

logger = logging.getLogger(__name__)

PLAIN_FIELDS = ("title", "excerpt", "seo_title", "seo_description")

_SENTENCE_END = re.compile(r"(?<=[.!?…。！？])(\s+)")
_WHITESPACE = re.compile(r"(\s+)")
_UPSTREAM_KEY = re.compile(r"(error\.\d{3}\.[a-z_]+\.[a-z_]+)(?::\s*([a-z_]+))?")


def _unavailable(reason: str, upstream: str = "") -> CmsError:
    params = {"reason": reason}
    if upstream:
        params["upstream_error"] = upstream
    return CmsError(503, ERR_503_TRANSLATION_UNAVAILABLE, params)


def _limits() -> tuple[int, int, int]:
    from ..conf import cms_settings

    per_text = max(1, int(cms_settings.MACHINE_TRANSLATE_MAX_TEXT_CHARS))
    items = max(1, int(cms_settings.MACHINE_TRANSLATE_MAX_ITEMS))
    chars = max(per_text, int(cms_settings.MACHINE_TRANSLATE_MAX_CHARS))
    return per_text, items, chars


def _tokens(text: str, pattern: re.Pattern, sep_after: str) -> list[tuple[str, str]]:
    parts = pattern.split(text)
    pieces, seps = parts[0::2], parts[1::2] + [sep_after]
    return [(piece, sep) for piece, sep in zip(pieces, seps) if piece or sep]


def split_text(text: str, limit: int) -> list[tuple[str, str]]:
    """``[(piece, separator after it)]`` with every piece at most *limit* chars.

    ``"".join(piece + sep)`` gives back *text*. Pieces are whole sentences
    where possible, packed greedily; a sentence longer than *limit* is split
    at whitespace, a word longer than *limit* is cut.
    """
    if len(text) <= limit:
        return [(text, "")]
    fine: list[tuple[str, str]] = []
    for sentence, sep in _tokens(text, _SENTENCE_END, ""):
        if len(sentence) <= limit:
            fine.append((sentence, sep))
            continue
        for word, wsep in _tokens(sentence, _WHITESPACE, sep):
            if len(word) <= limit:
                fine.append((word, wsep))
                continue
            cuts = [word[i:i + limit] for i in range(0, len(word), limit)]
            fine += [(cut, "") for cut in cuts[:-1]] + [(cuts[-1], wsep)]
    packed: list[tuple[str, str]] = []
    for piece, sep in fine:
        if packed:
            prev, prev_sep = packed[-1]
            if len(prev) + len(prev_sep) + len(piece) <= limit:
                packed[-1] = (prev + prev_sep + piece, sep)
                continue
        packed.append((piece, sep))
    return packed


def _batches(texts: list[str], max_items: int, max_chars: int):
    batch: list[str] = []
    size = 0
    for text in texts:
        if batch and (len(batch) >= max_items or size + len(text) > max_chars):
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        yield batch


def _call(function: str, batch: list[str], source: str, target: str, timeout: float) -> list[str]:
    from stapel_core.comm import call

    try:
        answer = call(function, {"texts": batch, "source": source, "target": target}, timeout=timeout)
    except Exception as exc:
        match = _UPSTREAM_KEY.search(str(exc)) or _UPSTREAM_KEY.search(str(exc.__cause__ or ""))
        upstream = match.group(1) if match else ""
        if upstream.startswith("error.503."):
            reason = match.group(2) or "unavailable"
        elif upstream.startswith("error.4"):
            reason = "refused"
        else:
            reason = "failed"
        logger.warning("cms: machine translation via %s failed (%s)", function, reason, exc_info=True)
        raise _unavailable(reason, upstream) from None
    out = answer.get("texts") if isinstance(answer, dict) else None
    if not isinstance(out, list) or len(out) != len(batch) or not all(isinstance(t, str) for t in out):
        logger.warning("cms: %s answered a malformed translation batch", function)
        raise _unavailable("malformed")
    return out


def translate_texts(texts: list[str], source: str, target: str) -> dict[str, str]:
    """``{text: translation}`` for every non-blank text, or a 503 :class:`CmsError`."""
    from stapel_core.comm import function_unreachable_reason

    from ..conf import cms_settings

    unique = list(dict.fromkeys(t for t in texts if t and t.strip()))
    if not unique:
        return {}
    function = str(cms_settings.MACHINE_TRANSLATE or "")
    if not function:
        raise _unavailable("not_configured")
    if function_unreachable_reason(function):
        raise _unavailable("unreachable")
    per_text, max_items, max_chars = _limits()
    timeout = float(cms_settings.MACHINE_TRANSLATE_TIMEOUT_SECONDS)
    # A text node's edge whitespace is structure (it separates it from the
    # next node); providers trim it, so it is kept here and put back.
    layout = {text: (_edges(text), split_text(text.strip(), per_text)) for text in unique}
    pieces = list(dict.fromkeys(piece for _, parts in layout.values() for piece, _ in parts if piece.strip()))
    table: dict[str, str] = {}
    for batch in _batches(pieces, max_items, max_chars):
        table.update(zip(batch, _call(function, batch, source, target, timeout)))
    return {text: lead + "".join(table.get(piece, piece) + sep for piece, sep in parts) + trail
            for text, ((lead, trail), parts) in layout.items()}


def _edges(text: str) -> tuple[str, str]:
    core = text.strip()
    start = text.index(core) if core else len(text)
    return text[:start], text[start + len(core):]


def translate_fields(fields: dict, source: str, target: str) -> dict:
    """A translated copy of a page's or post's content fields (nothing is written)."""
    blocks = fields.get("blocks") or []
    texts = [fields[name] for name in PLAIN_FIELDS if isinstance(fields.get(name), str)]
    collected: list[str] = []
    map_text(blocks, lambda text: collected.append(text) or text)
    table = translate_texts(texts + collected, source, target)
    out = dict(fields)
    for name in PLAIN_FIELDS:
        if isinstance(out.get(name), str) and out[name] in table:
            out[name] = table[out[name]]
    out["blocks"] = map_text(blocks, lambda text: table.get(text, text))
    return out


__all__ = ["split_text", "translate_fields", "translate_texts"]
