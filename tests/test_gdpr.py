"""Erasure pseudonymizes authorship and keeps the content; merge re-parents it."""
import pytest
from stapel_core.gdpr import gdpr_registry, registered_gdpr_owners

from stapel_cms.actions import handle_user_merged
from stapel_cms.gdpr import CmsGDPRProvider, erase_subject
from stapel_cms.models import Page, Post, Revision

from .helpers import V1, make_page, make_post, publish

pytestmark = pytest.mark.django_db


def test_owner_and_provider_are_registered():
    assert registered_gdpr_owners()["cms"] == ("account",)
    assert any(p.section == "cms" for p in gdpr_registry.providers)


def test_export_lists_what_the_person_authored(staff_client, staff):
    make_page(staff_client, "about", title="About")
    make_post(staff_client, "hello")
    out = CmsGDPRProvider().export(str(staff.pk))
    assert [p["path"] for p in out["pages_authored"]] == ["/about"]
    assert [p["slug"] for p in out["posts_authored"]] == ["hello"]
    assert len(out["revisions"]) == 2


def test_erase_keeps_content_and_pseudonymizes(staff_client, staff, api_client):
    page = make_page(staff_client, "about")
    publish(staff_client, "page", page["id"])
    staff_client.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/x", "new_path": "/about"},
                      format="json")
    counts = erase_subject("account", str(staff.pk))
    assert counts["page_authors"] == 1 and counts["revisions"] == 2 and counts["redirects"] == 1
    row = Page.objects.get(pk=page["id"])
    assert row.author_id.startswith("erased:") and row.updated_by_id == row.author_id
    assert not Revision.objects.filter(created_by_id=str(staff.pk)).exists()
    assert api_client.get(f"{V1}/public/resolve/", {"path": "/about"}).status_code == 200
    again = erase_subject("account", str(staff.pk))
    assert not any(again.values())
    assert erase_subject("workspace", "w1") is None


def test_merge_moves_authorship(staff_client, staff, captured_events):
    make_post(staff_client, "hello")

    class _Event:
        event_id = "e1"
        payload = {"from_user_id": str(staff.pk), "into_user_id": "survivor"}

    handle_user_merged(_Event())
    assert Post.objects.get().author_id == "survivor"
    handle_user_merged(_Event())
    assert Post.objects.get().author_id == "survivor"
