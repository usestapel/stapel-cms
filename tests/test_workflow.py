"""Publish workflow: the FSM table, snapshot isolation, scheduling, revisions."""
import datetime as dt
from itertools import product

import pytest
from django.utils import timezone

from stapel_cms import fsm
from stapel_cms.models import Page, Revision, Status
from stapel_cms.services import content

from .helpers import V1, err, in_future, make_page, make_post, patch, publish, resolve, transition

pytestmark = pytest.mark.django_db


def _to_status(staff_client, status):
    """A fresh page sitting in ``status``."""
    page = make_page(staff_client, f"p-{status}")
    if status == Status.PUBLISHED:
        publish(staff_client, "page", page["id"])
    elif status == Status.SCHEDULED:
        assert transition(staff_client, "page", page["id"], "scheduled", in_future()).status_code == 200
    elif status == Status.ARCHIVED:
        assert transition(staff_client, "page", page["id"], "archived").status_code == 200
    assert Page.objects.get(pk=page["id"]).status == status
    return page


@pytest.mark.parametrize("from_status,to_status", list(product(fsm.TARGETS, fsm.TARGETS)))
def test_fsm_table_every_edge(staff_client, from_status, to_status):
    """Inversion: every illegal edge is a 409, every legal one is a 200."""
    page = _to_status(staff_client, from_status)
    resp = transition(staff_client, "page", page["id"], to_status,
                      in_future() if to_status == Status.SCHEDULED else None)
    if fsm.allowed(from_status, to_status):
        assert resp.status_code == 200, resp.content
    else:
        assert resp.status_code == 409 and err(resp) == "error.409.cms_transition_invalid"
        assert resp.json()["params"] == {"from": from_status, "to": to_status}


def test_the_table_is_not_trivially_open():
    illegal = [(a, b) for a, b in product(fsm.TARGETS, fsm.TARGETS) if not fsm.allowed(a, b)]
    assert (Status.ARCHIVED, Status.PUBLISHED) in illegal and (Status.DRAFT, Status.DRAFT) in illegal


def test_a_draft_is_invisible_and_publishing_makes_it_visible(staff_client, api_client, captured_events):
    page = make_page(staff_client, "about", title="About")
    assert resolve(api_client, "/about").status_code == 404
    body = publish(staff_client, "page", page["id"])
    assert body["status"] == "published" and body["live_revision"] == 2
    got = resolve(api_client, "/about").json()
    assert got["kind"] == "page" and got["page"]["title"] == "About"
    (fact,) = [e for e in captured_events if e.event_type == "cms.page.published"]
    assert fact.payload["path"] == "/about" and fact.payload["first"] is True and fact.payload["revision"] == 2


def test_editing_a_published_page_changes_nothing_public_until_republished(staff_client, api_client):
    page = make_page(staff_client, "about", title="Old")
    page = publish(staff_client, "page", page["id"])
    edited = patch(staff_client, "page", page, title="New").json()
    assert edited["has_unpublished_changes"] is True
    assert resolve(api_client, "/about").json()["page"]["title"] == "Old"
    republished = publish(staff_client, "page", page["id"])
    assert republished["has_unpublished_changes"] is False
    assert resolve(api_client, "/about").json()["page"]["title"] == "New"


def test_schedule_serves_at_the_time_without_the_beat_and_the_beat_announces(staff_client, api_client,
                                                                              captured_events):
    page = make_page(staff_client, "launch", title="Launch")
    when = in_future(10)
    body = transition(staff_client, "page", page["id"], "scheduled", when).json()
    assert body["status"] == "scheduled" and body["scheduled_revision"] == 2
    assert resolve(api_client, "/launch").status_code == 404
    Page.objects.filter(pk=page["id"]).update(publish_at=timezone.now() - dt.timedelta(seconds=1))
    from django.core.cache import cache

    cache.clear()
    assert resolve(api_client, "/launch").json()["page"]["title"] == "Launch"
    assert not [e for e in captured_events if e.event_type == "cms.page.published"]
    assert content.promote_due() == 1
    row = Page.objects.get(pk=page["id"])
    assert row.status == "published" and row.live_revision.number == 2 and row.scheduled_revision is None
    assert [e.payload["page_id"] for e in captured_events if e.event_type == "cms.page.published"] == [
        str(page["id"])]
    assert content.promote_due() == 0


def test_scheduling_needs_a_future_time(staff_client):
    page = make_page(staff_client, "x")
    resp = transition(staff_client, "page", page["id"], "scheduled", timezone.now() - dt.timedelta(minutes=1))
    assert resp.status_code == 400 and err(resp) == "error.400.cms_publish_at_invalid"
    resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/transition/", {"to": "scheduled"}, format="json")
    assert resp.status_code == 400


def test_scheduled_edits_of_a_live_page_keep_the_live_one_serving(staff_client, api_client):
    page = publish(staff_client, "page", make_page(staff_client, "about", title="V1")["id"])
    page = patch(staff_client, "page", page, title="V2").json()
    transition(staff_client, "page", page["id"], "scheduled", in_future())
    assert resolve(api_client, "/about").json()["page"]["title"] == "V1"
    cancelled = transition(staff_client, "page", page["id"], "draft").json()
    assert cancelled["status"] == "published" and cancelled["scheduled_revision"] is None


def test_cancelling_a_first_schedule_returns_to_draft(staff_client):
    post = make_post(staff_client, "soon")
    transition(staff_client, "post", post["id"], "scheduled", in_future())
    body = transition(staff_client, "post", post["id"], "draft").json()
    assert body["status"] == "draft" and body["published_at"] is None


def test_archive_unpublishes_and_announces(staff_client, api_client, captured_events):
    page = publish(staff_client, "page", make_page(staff_client, "about")["id"])
    assert resolve(api_client, "/about").status_code == 200
    body = transition(staff_client, "page", page["id"], "archived").json()
    assert body["status"] == "archived" and body["live_revision"] is None
    assert resolve(api_client, "/about").status_code == 404
    assert [e.payload["path"] for e in captured_events if e.event_type == "cms.page.unpublished"] == ["/about"]
    reopened = transition(staff_client, "page", page["id"], "draft").json()
    assert reopened["status"] == "draft"


def test_republish_is_not_first(staff_client, captured_events):
    page = make_page(staff_client, "about")
    publish(staff_client, "page", page["id"])
    publish(staff_client, "page", page["id"])
    firsts = [e.payload["first"] for e in captured_events if e.event_type == "cms.page.published"]
    assert firsts == [True, False]


def test_revisions_list_and_restore(staff_client, api_client):
    page = make_page(staff_client, "about", title="One")
    page = patch(staff_client, "page", page, title="Two").json()
    page = patch(staff_client, "page", page, title="Three").json()
    listing = staff_client.get(f"{V1}/staff/pages/{page['id']}/revisions/").json()
    assert [r["number"] for r in listing["items"]] == [3, 2, 1]
    assert listing["items"][-1]["snapshot"]["title"] == "One"
    restored = staff_client.post(f"{V1}/staff/pages/{page['id']}/revisions/1/restore/").json()
    assert restored["title"] == "One" and restored["version"] == 4 and restored["status"] == "draft"
    assert resolve(api_client, "/about").status_code == 404
    resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/revisions/99/restore/")
    assert resp.status_code == 404 and err(resp) == "error.404.cms_revision_not_found"


def test_revisions_are_pruned_but_never_the_live_one(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "REVISIONS_KEEP": 3}
    page = make_page(staff_client, "about", title="t0")
    page = publish(staff_client, "page", page["id"])
    live = Page.objects.get(pk=page["id"]).live_revision_id
    for i in range(6):
        page = patch(staff_client, "page", page, title=f"t{i + 1}").json()
    numbers = set(Revision.objects.filter(kind="page", object_id=page["id"]).values_list("pk", flat=True))
    assert len(numbers) == 3 and live in numbers


def test_posts_follow_the_same_workflow(staff_client, api_client):
    post = make_post(staff_client, "hello", title="Hello")
    assert api_client.get(f"{V1}/public/posts/hello/").status_code == 404
    body = publish(staff_client, "post", post["id"])
    assert body["published_at"] is not None
    got = api_client.get(f"{V1}/public/posts/hello/").json()
    assert got["title"] == "Hello" and got["path"] == "/blog/hello"
    assert resolve(api_client, "/blog/hello").json()["kind"] == "post"
