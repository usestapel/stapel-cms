"""Keep stapel-cdn's reference tracking in step with what content uses.

cdn deletes media nobody references after its unclaimed TTL; a page whose
picture was uploaded but never claimed would lose it. After every save cms
tells ``cdn.refs_sync`` (``MEDIA_REFS_FUNCTION``) the refs the working copy
and its live/scheduled snapshots use. Best-effort and after commit: an
unreachable cdn leaves ``media_refs`` unchanged so the next save retries the
whole difference.
"""
from __future__ import annotations

import logging

from django.db import transaction

from ..blocks import media_refs

logger = logging.getLogger(__name__)


def refs_of(obj) -> list[str]:
    refs = media_refs(obj.blocks)
    for field in ("og_image", "cover"):
        value = getattr(obj, field, "")
        if value:
            refs.add(value)
    for revision in (obj.live_revision, obj.scheduled_revision):
        if revision is not None:
            snap = revision.snapshot or {}
            refs |= media_refs(snap.get("blocks") or [])
            for field in ("og_image", "cover"):
                if snap.get(field):
                    refs.add(snap[field])
    return sorted(refs)


def sync_after_commit(obj, kind: str) -> None:
    from ..conf import cms_settings

    function = str(cms_settings.MEDIA_REFS_FUNCTION or "")
    if not function:
        return
    new = refs_of(obj)
    old = sorted(obj.media_refs or [])
    if new == old:
        return
    model, pk = type(obj), obj.pk

    def _sync():
        from stapel_core.comm import call, function_unreachable_reason

        if function_unreachable_reason(function):
            return
        try:
            call(function, {"service": "cms", "entity_type": kind, "entity_id": str(pk),
                            "old_hashes": old, "new_hashes": new})
        except Exception:
            logger.warning("cms: %s for %s %s failed; retried on the next save", function, kind, pk, exc_info=True)
            return
        model.objects.filter(pk=pk).update(media_refs=new)

    transaction.on_commit(_sync)


__all__ = ["refs_of", "sync_after_commit"]
