"""The ``form`` block's reference check, through stapel-forms by Function name.

``FORM_EXISTS_FUNCTION`` (``forms.form.exists {public_id}`` ->
``{exists, published}``) is asked once per distinct form id:

- on save: an unknown form refuses the block (a field-level 400); a form that
  exists but is not published yet is allowed in the draft with a warning;
- on publish (now or scheduled): an unknown or unpublished form refuses it;
- the Function unreachable, failing or answering nonsense: the shape check
  alone stands and the staff response carries a ``form_unverified`` warning —
  never a 500, never a refusal on a neighbour's outage.

A scheduled snapshot that goes live later (``promote_due``) is not asked
again: the public renderer meets a closed form as stapel-forms answers it.
"""
from __future__ import annotations

import logging

from ..errors import ERR_400_FORM_UNKNOWN, ERR_409_FORM_UNPUBLISHED
from . import CmsError

logger = logging.getLogger(__name__)

CALL_TIMEOUT_SECONDS = 5.0
PUBLISHED, UNPUBLISHED, MISSING, UNVERIFIED = "published", "unpublished", "missing", "unverified"


def references(blocks) -> list[tuple[str, str]]:
    """``[(field, form_id)]`` of every ``form`` block of a raw block list."""
    out = []
    for index, block in enumerate(blocks or []):
        if not isinstance(block, dict) or block.get("type") != "form":
            continue
        form_id = (block.get("data") or {}).get("form_id") if isinstance(block.get("data"), dict) else None
        if isinstance(form_id, str) and form_id:
            out.append((f"blocks.{index}.data.form_id", form_id))
    return out


def _status(function: str, form_id: str) -> str:
    from stapel_core.comm import call, function_unreachable_reason

    if function_unreachable_reason(function):
        return UNVERIFIED
    try:
        answer = call(function, {"public_id": form_id}, timeout=CALL_TIMEOUT_SECONDS)
    except Exception:
        logger.warning("cms: %s for form %r failed; shape check only", function, form_id, exc_info=True)
        return UNVERIFIED
    if not isinstance(answer, dict) or not isinstance(answer.get("exists"), bool):
        logger.warning("cms: %s answered %r for form %r; shape check only", function, answer, form_id)
        return UNVERIFIED
    if not answer["exists"]:
        return MISSING
    return PUBLISHED if answer.get("published") is True else UNPUBLISHED


def statuses(blocks) -> list[tuple[str, str, str]]:
    """``[(field, form_id, status)]``; empty when the check is switched off."""
    from ..conf import cms_settings

    function = str(cms_settings.FORM_EXISTS_FUNCTION or "")
    refs = references(blocks)
    if not function or not refs:
        return []
    known: dict[str, str] = {}
    for _, form_id in refs:
        if form_id not in known:
            known[form_id] = _status(function, form_id)
    return [(field, form_id, known[form_id]) for field, form_id in refs]


def _warning(code: str, field: str, form_id: str) -> dict:
    return {"code": code, "field": field, "params": {"form_id": form_id}}


def check_save(blocks) -> list[dict]:
    """Refuse an unknown form; return the warnings of a draft save.

    The block list's shape is validated first, so a malformed list is
    refused for its shape before stapel-forms is asked anything.
    """
    from ..blocks import BlockError, validate_blocks

    try:
        blocks = validate_blocks(blocks)
    except BlockError as exc:
        raise CmsError(400, exc.key, exc.params) from None
    warnings = []
    for field, form_id, status in statuses(blocks):
        if status == MISSING:
            raise CmsError(400, ERR_400_FORM_UNKNOWN, {"field": field, "form_id": form_id})
        if status == UNPUBLISHED:
            warnings.append(_warning("form_unpublished", field, form_id))
        elif status == UNVERIFIED:
            warnings.append(_warning("form_unverified", field, form_id))
    return warnings


def check_publish(blocks) -> list[dict]:
    """Refuse an unknown or unpublished form; return the warnings of a publish."""
    warnings = []
    for field, form_id, status in statuses(blocks):
        if status == MISSING:
            raise CmsError(400, ERR_400_FORM_UNKNOWN, {"field": field, "form_id": form_id})
        if status == UNPUBLISHED:
            raise CmsError(409, ERR_409_FORM_UNPUBLISHED, {"field": field, "form_id": form_id})
        if status == UNVERIFIED:
            warnings.append(_warning("form_unverified", field, form_id))
    return warnings


__all__ = ["check_publish", "check_save", "references", "statuses"]
