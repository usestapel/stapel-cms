"""Optional machine translation of a locale variant, through a comm Function.

``MACHINE_TRANSLATE`` names a Function answering the contract in
``schemas/functions/machine_translate.json``: ``{texts, source, target}`` ->
``{texts}`` (same length, same order). Unset, unreachable or a malformed
answer is a 503 — never a silently untranslated copy.
"""
from __future__ import annotations

import logging

from ..blocks import iter_text, map_text
from ..errors import ERR_503_TRANSLATION_UNAVAILABLE
from . import CmsError

logger = logging.getLogger(__name__)

PLAIN_FIELDS = ("title", "excerpt", "seo_title", "seo_description")
MAX_TEXTS = 2000


def _unavailable() -> CmsError:
    return CmsError(503, ERR_503_TRANSLATION_UNAVAILABLE)


def translate_texts(texts: list[str], source: str, target: str) -> dict[str, str]:
    from stapel_core.comm import call, function_unreachable_reason

    from ..conf import cms_settings

    function = str(cms_settings.MACHINE_TRANSLATE or "")
    if not function or function_unreachable_reason(function):
        raise _unavailable()
    unique = list(dict.fromkeys(t for t in texts if t and t.strip()))[:MAX_TEXTS]
    if not unique:
        return {}
    try:
        answer = call(function, {"texts": unique, "source": source, "target": target})
    except Exception:
        logger.warning("cms: machine translation via %s failed", function, exc_info=True)
        raise _unavailable() from None
    out = answer.get("texts") if isinstance(answer, dict) else None
    if not isinstance(out, list) or len(out) != len(unique) or not all(isinstance(t, str) for t in out):
        logger.warning("cms: %s answered a malformed translation batch", function)
        raise _unavailable()
    return dict(zip(unique, out))


def translate_fields(fields: dict, source: str, target: str) -> dict:
    texts = [fields[name] for name in PLAIN_FIELDS if isinstance(fields.get(name), str)]
    texts += list(iter_text(fields.get("blocks") or []))
    table = translate_texts(texts, source, target)
    out = dict(fields)
    for name in PLAIN_FIELDS:
        if isinstance(out.get(name), str) and out[name] in table:
            out[name] = table[out[name]]
    out["blocks"] = map_text(out.get("blocks") or [], lambda text: table.get(text, text))
    return out


__all__ = ["translate_fields", "translate_texts"]
