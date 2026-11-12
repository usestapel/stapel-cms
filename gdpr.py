"""GDPR for stapel-cms — content stays, the person goes.

Content is staff-authored site content owned by the site; the only personal
data is staff ids (``author_id``, ``updated_by_id``, ``Revision.created_by_id``,
``Redirect.created_by_id``). Export lists what the person authored;
erasure replaces their id by the fleet pseudonym
(``stapel_core.gdpr.pseudonymize``) and keeps every page and post — the site
does not lose its pages when an editor leaves.
"""
from __future__ import annotations

from stapel_core.gdpr import GDPRProvider


class CmsGDPRProvider(GDPRProvider):
    section = "cms"

    def export(self, user_id) -> dict:
        from .models import Page, Post, Revision

        user_id = str(user_id)
        return {
            "pages_authored": [
                {"id": p.pk, "site": p.site, "locale": p.locale, "path": p.path, "title": p.title,
                 "created_at": p.created_at.isoformat()}
                for p in Page.objects.filter(author_id=user_id)
            ],
            "posts_authored": [
                {"id": p.pk, "site": p.site, "locale": p.locale, "slug": p.slug, "title": p.title,
                 "created_at": p.created_at.isoformat()}
                for p in Post.objects.filter(author_id=user_id)
            ],
            "revisions": [
                {"kind": r.kind, "object_id": r.object_id, "number": r.number, "note": r.note,
                 "created_at": r.created_at.isoformat()}
                for r in Revision.objects.filter(created_by_id=user_id)
            ],
        }

    def delete(self, user_id) -> None:
        erase_subject("account", user_id)

    #: Pseudonymizing the ids IS the anonymisation here.
    anonymize = delete


OWNER = CmsGDPRProvider.section
SUBJECT_TYPES = ("account",)


def erase_subject(subject_type, subject_key, workspace_id=None):
    """Pseudonymize one account's authorship ids. Idempotent; counts rows touched."""
    from django.db import transaction
    from stapel_core.gdpr.owners import pseudonymize

    from .actions import reparent_authors

    if subject_type != "account" or not subject_key:
        return None
    with transaction.atomic():
        return reparent_authors(str(subject_key), pseudonymize(str(subject_key)))
