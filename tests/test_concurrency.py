"""Two editors, one page: the version counter never loses an update.

SQLite has no row locks (Django drops FOR UPDATE there), so OS threads
cannot prove the lock on this harness. What is proved:

1. the row lock (``select_for_update`` on Page) is asked for before the
   version is compared (ordering spy);
2. the interleaving the lock prevents on Postgres — a rival save commits
   between our read and our write — still ends in one save and one 409,
   because the write is ``UPDATE … WHERE version = <read>`` (a guard that
   holds on any database); the rival's title survives;
3. inversion: the same interleaving with the guard's WHERE removed loses
   the rival's update — the test can see the defect;
4. revision numbers are unique per object by constraint.
"""
import pytest
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from stapel_cms.models import Page, Revision
from stapel_cms.services import CmsError, content

from .helpers import make_page

pytestmark = pytest.mark.django_db


def test_lock_is_taken_before_the_version_is_compared(staff_client, staff, monkeypatch):
    page = make_page(staff_client, "about")
    order = []
    real_sfu = QuerySet.select_for_update

    def sfu_spy(self, *a, **kw):
        order.append(f"lock:{self.model.__name__}")
        return real_sfu(self, *a, **kw)

    monkeypatch.setattr(QuerySet, "select_for_update", sfu_spy)
    with pytest.raises(CmsError) as info:
        content.update("page", page["id"], staff, {"version": 99, "title": "x"})
    assert info.value.key == "error.409.cms_version_conflict"
    assert order and order[0] == "lock:Page"


def _rival_between_read_and_write(monkeypatch, page_id):
    """Our read saw version 1; a rival's save (version 2) committed before our write."""
    Page.objects.filter(pk=page_id).update(title="Rival", version=2)
    real_locked = content._locked

    def stale_read(kind, obj_id):
        obj = real_locked(kind, obj_id)
        obj.title, obj.version = "About", 1
        return obj

    monkeypatch.setattr(content, "_locked", stale_read)


def test_interleaved_save_is_refused_and_the_rival_survives(staff_client, staff, monkeypatch):
    page = make_page(staff_client, "about")
    _rival_between_read_and_write(monkeypatch, page["id"])
    with pytest.raises(CmsError) as info:
        content.update("page", page["id"], staff, {"version": 1, "title": "Mine"})
    assert info.value.status == 409
    row = Page.objects.get(pk=page["id"])
    assert (row.title, row.version) == ("Rival", 2)


def test_inversion_without_the_guard_the_rival_is_lost(staff_client, staff, monkeypatch):
    page = make_page(staff_client, "about")
    _rival_between_read_and_write(monkeypatch, page["id"])
    real_filter = QuerySet.filter

    def no_version_guard(self, *args, **kwargs):
        kwargs.pop("version", None)
        return real_filter(self, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "filter", no_version_guard)
    content.update("page", page["id"], staff, {"version": 1, "title": "Mine"})
    assert Page.objects.get(pk=page["id"]).title == "Mine", "the defect the guard exists for"


def test_revision_numbers_are_unique_per_object(staff_client):
    page = make_page(staff_client, "about")
    with pytest.raises(IntegrityError), transaction.atomic():
        Revision.objects.create(kind="page", object_id=page["id"], number=1, snapshot={})
