"""Staff tags, menus and redirects."""
import pytest

from stapel_cms.models import MenuItem, Redirect

from .helpers import V1, err, make_page, make_post, publish, resolve

pytestmark = pytest.mark.django_db


def test_tags_crud_and_uniqueness(staff_client):
    tag = staff_client.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "News"},
                            format="json")
    assert tag.status_code == 201
    dup = staff_client.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "x"}, format="json")
    assert dup.status_code == 409 and err(dup) == "error.409.cms_slug_taken"
    renamed = staff_client.patch(f"{V1}/staff/tags/{tag.json()['id']}/", {"name": "Updates"}, format="json")
    assert renamed.json()["name"] == "Updates"
    assert staff_client.get(f"{V1}/staff/tags/").json()["count"] == 1
    assert staff_client.delete(f"{V1}/staff/tags/{tag.json()['id']}/").status_code == 204


def test_post_tags_must_belong_to_the_same_scope(staff_client):
    de = staff_client.post(f"{V1}/staff/tags/", {"locale": "de", "slug": "news", "name": "N"},
                           format="json").json()
    resp = staff_client.post(f"{V1}/staff/posts/", {"locale": "en", "slug": "x", "title": "x",
                                                    "tags": [de["id"]]}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_tag_unknown"


def test_post_slug_unique_and_slug_change_redirects(staff_client, api_client):
    post = make_post(staff_client, "hello")
    dup = staff_client.post(f"{V1}/staff/posts/", {"locale": "en", "slug": "hello", "title": "x"}, format="json")
    assert dup.status_code == 409
    post = publish(staff_client, "post", post["id"])
    resp = staff_client.patch(f"{V1}/staff/posts/{post['id']}/", {"version": post["version"], "slug": "hi"},
                              format="json")
    assert resp.status_code == 200 and resp.json()["path"] == "/blog/hi"
    assert resolve(api_client, "/blog/hello").json()["redirect"]["to"] == "/blog/hi"


def test_menu_replace_is_atomic_and_validated(staff_client):
    page = make_page(staff_client, "about")
    menu = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "footer", "items": [
        {"label": "About", "target_type": "page", "page": page["id"]}]}, format="json").json()
    bad = staff_client.put(f"{V1}/staff/menus/{menu['id']}/", {"items": [
        {"label": "ok", "target_type": "url", "url": "/ok"},
        {"label": "bad", "target_type": "page", "page": 999999}]}, format="json")
    assert bad.status_code == 400 and err(bad) == "error.400.cms_menu_invalid"
    assert list(MenuItem.objects.values_list("label", flat=True)) == ["About"]
    good = staff_client.put(f"{V1}/staff/menus/{menu['id']}/", {"title": "Footer", "items": [
        {"label": "Top", "target_type": "url", "url": "/top", "children": [
            {"label": "Child", "target_type": "url", "url": "/child"}]}]}, format="json")
    assert good.status_code == 200
    assert good.json()["items"][0]["children"][0]["label"] == "Child"
    assert staff_client.get(f"{V1}/staff/menus/").json()["items"][0]["title"] == "Footer"


def test_menu_depth_and_size_caps(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MENU_MAX_DEPTH": 2, "MENU_MAX_ITEMS": 3}
    deep = {"label": "a", "target_type": "url", "url": "/a", "children": [
        {"label": "b", "target_type": "url", "url": "/b", "children": [
            {"label": "c", "target_type": "url", "url": "/c"}]}]}
    resp = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "h", "items": [deep]}, format="json")
    assert resp.status_code == 400
    wide = [{"label": str(i), "target_type": "url", "url": "/x"} for i in range(4)]
    resp = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "h", "items": wide}, format="json")
    assert resp.status_code == 400
    assert staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "h", "items": wide[:3]},
                             format="json").status_code == 201
    dup = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "h"}, format="json")
    assert dup.status_code == 409


def test_menu_change_is_announced(staff_client, captured_events):
    menu = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "header"}, format="json").json()
    staff_client.delete(f"{V1}/staff/menus/{menu['id']}/")
    assert [e.payload["key"] for e in captured_events if e.event_type == "cms.menu.changed"] == ["header", "header"]


def test_manual_redirects(staff_client, api_client):
    resp = staff_client.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/old/",
                                                        "new_path": "https://example.com/new", "permanent": False},
                             format="json")
    assert resp.status_code == 201 and resp.json()["old_path"] == "/old" and resp.json()["source"] == "manual"
    assert resolve(api_client, "/old").json()["redirect"] == {"to": "https://example.com/new", "permanent": False}
    for target in ("javascript:alert(1)", "//evil.example", "/old"):
        bad = staff_client.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/old",
                                                           "new_path": target}, format="json")
        assert bad.status_code == 400, target
    rid = resp.json()["id"]
    assert staff_client.get(f"{V1}/staff/redirects/").json()["count"] == 1
    assert staff_client.delete(f"{V1}/staff/redirects/{rid}/").status_code == 204
    assert resolve(api_client, "/old").status_code == 404


def test_publishing_a_page_at_a_redirected_path_wins(staff_client, api_client):
    staff_client.post(f"{V1}/staff/redirects/", {"locale": "en", "old_path": "/about", "new_path": "/company"},
                      format="json")
    page = make_page(staff_client, "about")
    assert resolve(api_client, "/about").json()["kind"] == "redirect"
    publish(staff_client, "page", page["id"])
    assert resolve(api_client, "/about").json()["kind"] == "page"
    assert not Redirect.objects.filter(old_path="/about").exists()
