"""Described images next to the bare media refs of a public page or post.

When ``MEDIA_DESCRIBE_FUNCTION`` (stapel-cdn's ``cdn.describe_many``
``{refs}`` -> ``{items: {ref: snapshot}, missing}``) is reachable, a public
page or post answer carries ``media``: one image per described ref in
stapel-core's ``StapelImage`` shape (typed ``VariantMeta`` rungs and a
default ``url``) plus its ``ref``, so a renderer draws pictures without a
describe round trip of its own. One batched call per answer, cached with the
page (it is part of the cached body); refs beyond ``MEDIA_DESCRIBE_MAX_REFS``
stay bare. Unreachable, failing or unknown -> refs only, never an error.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CALL_TIMEOUT_SECONDS = 5.0


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _variant(raw) -> dict | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("url"), str) or not raw["url"]:
        return None
    tier = raw.get("tier")
    return {
        "tier": "original" if tier is None else str(tier),
        "branch": raw.get("branch") if raw.get("branch") in ("w", "h") else None,
        "url": raw["url"],
        "width": _int(raw.get("width")),
        "height": _int(raw.get("height")),
    }


def _default_url(variants: list[dict]) -> str | None:
    for variant in variants:
        if variant["tier"] == "original":
            return variant["url"]
    if not variants:
        return None
    return max(variants, key=lambda v: (v["width"] or 0) * (v["height"] or 0))["url"]


def image(ref: str, snapshot: dict) -> dict | None:
    """``{ref, source, url, mime, width, height, aspect, square, preview_b64, variants}`` or ``None``."""
    rungs = snapshot.get("variants") if isinstance(snapshot.get("variants"), list) else []
    variants = [v for v in (_variant(raw) for raw in rungs) if v]
    url = _default_url(variants)
    if url is None:
        return None
    aspect = snapshot.get("aspect")
    preview = snapshot.get("preview_b64")
    return {
        "ref": ref,
        "source": "cdn",
        "url": url,
        "mime": snapshot.get("mime") if isinstance(snapshot.get("mime"), str) else None,
        "width": _int(snapshot.get("width")),
        "height": _int(snapshot.get("height")),
        "aspect": float(aspect) if isinstance(aspect, (int, float)) and not isinstance(aspect, bool) else None,
        "square": bool(snapshot.get("square")),
        "preview_b64": preview if isinstance(preview, str) else None,
        "variants": variants,
    }


def describe(refs) -> list[dict]:
    """Described images for *refs* (first-seen order), one Function call; ``[]`` when unavailable."""
    from stapel_core.comm import call, function_unreachable_reason

    from ..conf import cms_settings

    function = str(cms_settings.MEDIA_DESCRIBE_FUNCTION or "")
    unique = list(dict.fromkeys(str(r) for r in refs if r))[:max(0, int(cms_settings.MEDIA_DESCRIBE_MAX_REFS))]
    if not function or not unique or function_unreachable_reason(function):
        return []
    try:
        answer = call(function, {"refs": unique}, timeout=CALL_TIMEOUT_SECONDS)
    except Exception:
        logger.info("cms: %s unavailable; public media stay bare refs", function, exc_info=True)
        return []
    items = answer.get("items") if isinstance(answer, dict) else None
    if not isinstance(items, dict):
        return []
    out = []
    for ref in unique:
        snapshot = items.get(ref)
        described = image(ref, snapshot) if isinstance(snapshot, dict) else None
        if described is not None:
            out.append(described)
    return out


def absolute(url: str | None, site: str) -> str | None:
    """*url* made absolute against the site's origin (``None`` when it cannot be)."""
    if not url:
        return None
    if url.startswith(("https://", "http://")):
        return url
    from .. import sitekeys

    origin = sitekeys.origin(site)
    return f"{origin}{url}" if origin and url.startswith("/") and not url.startswith("//") else None


__all__ = ["absolute", "describe", "image"]
