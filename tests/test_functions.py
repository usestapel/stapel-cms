"""comm Functions under schema validation."""
import pytest
from stapel_core.comm import call

from .helpers import make_page, make_post, patch, publish

pytestmark = pytest.mark.django_db


def test_sitemap_entries_pages_then_posts_without_noindex(staff_client):
    publish(staff_client, "page", make_page(staff_client, "about")["id"])
    hidden = make_page(staff_client, "hidden")
    patch(staff_client, "page", hidden, noindex=True)
    publish(staff_client, "page", hidden["id"])
    make_page(staff_client, "draft")
    publish(staff_client, "post", make_post(staff_client, "hello")["id"])
    out = call("cms.sitemap_entries", {"site": ""})
    assert [(e["kind"], e["path"]) for e in out["entries"]] == [("page", "/about"), ("post", "/blog/hello")]
    assert out["cursor"] is None and out["entries"][0]["alternates"] == []


def test_sitemap_entries_page_by_cursor(staff_client):
    for slug in ("a", "b", "c"):
        publish(staff_client, "page", make_page(staff_client, slug)["id"])
    first = call("cms.sitemap_entries", {"site": "", "limit": 2})
    rest = call("cms.sitemap_entries", {"site": "", "limit": 2, "cursor": first["cursor"]})
    assert [e["path"] for e in first["entries"] + rest["entries"]] == ["/a", "/b", "/c"]
    assert rest["cursor"] is None


def test_resolve_path(staff_client):
    page = publish(staff_client, "page", make_page(staff_client, "about", title="About")["id"])
    assert call("cms.resolve_path", {"site": "", "path": "/about"}) == {
        "found": True, "kind": "page", "id": page["id"], "locale": "en", "title": "About", "path": "/about"}
    assert call("cms.resolve_path", {"path": "/nope"})["found"] is False


def test_feed_function(staff_client):
    publish(staff_client, "post", make_post(staff_client, "hello", title="Hello")["id"])
    out = call("cms.feed", {"site": "", "type": "atom"})
    assert out["content_type"].startswith("application/atom+xml") and "Hello" in out["body"]
