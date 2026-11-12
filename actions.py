"""Action subscriptions of stapel-cms. Handlers are idempotent.

- ``user.merged`` (stapel-auth) — authorship ids follow the surviving
  account. Staff are rarely guests, but a silent answer to a merge is the
  defect class ``stapel_core.comm.lifecycle_checks`` exists for.
- ``user.deleted`` / ``gdpr.erasure.requested`` are answered by
  ``register_gdpr_owner`` (``apps.py``), not here.
"""
import json
import logging
from pathlib import Path

from django.db import transaction
from stapel_core.comm import on_action

logger = logging.getLogger(__name__)

_CONSUMES = Path(__file__).resolve().parent / "schemas" / "consumes"


def _schema(name: str) -> dict:
    return json.loads((_CONSUMES / f"{name}.json").read_text(encoding="utf-8"))


def reparent_authors(from_user_id: str, into_user_id: str) -> dict:
    """Move every authorship id from one account to another; counts what moved."""
    from .models import Page, Post, Redirect, Revision

    moved = {}
    for model in (Page, Post):
        moved[f"{model._meta.model_name}_authors"] = model.objects.filter(author_id=from_user_id).update(
            author_id=into_user_id)
        moved[f"{model._meta.model_name}_editors"] = model.objects.filter(updated_by_id=from_user_id).update(
            updated_by_id=into_user_id)
    moved["revisions"] = Revision.objects.filter(created_by_id=from_user_id).update(created_by_id=into_user_id)
    moved["redirects"] = Redirect.objects.filter(created_by_id=from_user_id).update(created_by_id=into_user_id)
    return moved


@on_action("user.merged", schema=_schema("user.merged"))
def handle_user_merged(event):
    """Re-parent the guest's authorship ids to the surviving account."""
    payload = event.payload or {}
    from_user_id = str(payload.get("from_user_id") or "")
    into_user_id = str(payload.get("into_user_id") or "")
    if not from_user_id or not into_user_id:
        logger.error("user.merged without from/into user id: %s", event.event_id)
        return
    if from_user_id == into_user_id:
        return
    with transaction.atomic():
        moved = reparent_authors(from_user_id, into_user_id)
    if any(moved.values()):
        logger.info("user.merged %s -> %s: %s", from_user_id, into_user_id, moved)
