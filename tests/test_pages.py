"""Staff page editing: tree, paths, redirects, optimistic lock, delete rules."""
import pytest

from stapel_cms.models import Page, Redirect, Revision

from .helpers import V1, err, make_page, patch, publish, resolve

pytestmark = pytest.mark.django_db


def test_create_derives_the_path_from_the_tree(staff_client):
    about = make_page(staff_client, "about")
    team = make_page(staff_client, "team", parent=about["id"])
    assert (about["path"], team["path"]) == ("/about", "/about/team")
    assert team["status"] == "draft" and team["version"] == 1


def test_root_page_has_path_slash_and_children_skip_it(staff_client):
    root = make_page(staff_client, "", title="Home")
    child = make_page(staff_client, "news", parent=root["id"])
    assert root["path"] == "/" and child["path"] == "/news"


def test_an_empty_slug_needs_a_top_level_page(staff_client):
    about = make_page(staff_client, "about")
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "", "parent": about["id"],
                                                    "title": "x"}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_slug_invalid"


@pytest.mark.parametrize("slug", ["Bad Slug", "a/b", "-x", "x--y", "a_b", "x" * 101])
def test_bad_slugs_are_refused(staff_client, slug):
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": slug, "title": "x"}, format="json")
    assert resp.status_code == 400


def test_unicode_slugs_are_allowed(staff_client):
    assert make_page(staff_client, "über-uns")["path"] == "/über-uns"


def test_path_is_unique_per_site_and_locale(staff_client):
    make_page(staff_client, "about")
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "about", "title": "x"}, format="json")
    assert resp.status_code == 409 and err(resp) == "error.409.cms_path_taken"
    assert make_page(staff_client, "about", locale="de")["path"] == "/about"


def test_blog_prefix_is_reserved(staff_client):
    blog = make_page(staff_client, "blog")
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "parent": blog["id"],
                                                    "title": "x"}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_path_reserved"


def test_depth_is_capped(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "PAGE_MAX_DEPTH": 2}
    a = make_page(staff_client, "a")
    b = make_page(staff_client, "b", parent=a["id"])
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "c", "parent": b["id"],
                                                    "title": "x"}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_tree_too_deep"


def test_parent_must_share_site_and_locale(staff_client):
    de = make_page(staff_client, "ueber", locale="de")
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "parent": de["id"],
                                                    "title": "x"}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_parent_invalid"


def test_a_page_cannot_move_under_its_own_descendant(staff_client):
    a = make_page(staff_client, "a")
    b = make_page(staff_client, "b", parent=a["id"])
    resp = patch(staff_client, "page", a, parent=b["id"])
    assert resp.status_code == 400 and err(resp) == "error.400.cms_parent_invalid"


def test_unknown_template_site_and_locale(staff_client):
    for body, key in [({"template": "nope"}, "error.400.cms_template_unknown"),
                      ({"site": "other"}, "error.400.cms_site_unknown"),
                      ({"locale": "fr"}, "error.400.cms_locale_unknown")]:
        resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "x", **body},
                                 format="json")
        assert resp.status_code == 400 and err(resp) == key, body


def test_unknown_block_type_names_the_type(staff_client):
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "x",
                                                    "blocks": [{"type": "marquee", "id": "m", "data": {}}]},
                             format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_block_type_unknown"
    assert resp.json()["params"]["type"] == "marquee"


def test_repeated_block_ids_are_refused(staff_client):
    block = {"type": "form", "id": "same", "data": {"form_id": "abc"}}
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "x",
                                                    "blocks": [block, block]}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_blocks_invalid"


def test_too_many_blocks(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MAX_BLOCKS": 2}
    blocks = [{"type": "form", "id": f"f{i}", "data": {"form_id": "abc"}} for i in range(3)]
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "x",
                                                    "blocks": blocks}, format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_blocks_too_large"


def test_patch_bumps_the_version_and_appends_a_revision(staff_client):
    page = make_page(staff_client, "about")
    resp = patch(staff_client, "page", page, title="About us")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2 and resp.json()["title"] == "About us"
    assert Revision.objects.filter(kind="page", object_id=page["id"]).count() == 2


def test_a_stale_version_is_a_409_with_the_current_one(staff_client):
    page = make_page(staff_client, "about")
    assert patch(staff_client, "page", page, title="First").status_code == 200
    resp = patch(staff_client, "page", page, title="Second")
    assert resp.status_code == 409 and err(resp) == "error.409.cms_version_conflict"
    assert resp.json()["params"]["current"] == 2
    assert Page.objects.get(pk=page["id"]).title == "First"


def test_moving_a_published_subtree_leaves_redirects(staff_client, api_client, captured_events):
    about = make_page(staff_client, "about")
    team = make_page(staff_client, "team", parent=about["id"])
    publish(staff_client, "page", about["id"])
    publish(staff_client, "page", team["id"])
    about = staff_client.get(f"{V1}/staff/pages/{about['id']}/").json()
    assert patch(staff_client, "page", about, slug="company").status_code == 200
    assert Page.objects.get(pk=team["id"]).path == "/company/team"
    pairs = set(Redirect.objects.values_list("old_path", "new_path"))
    assert pairs == {("/about", "/company"), ("/about/team", "/company/team")}
    body = resolve(api_client, "/about/team").json()
    assert body["kind"] == "redirect" and body["redirect"] == {"to": "/company/team", "permanent": True}
    assert resolve(api_client, "/company/team").json()["kind"] == "page"
    assert {e.payload["old_path"] for e in captured_events if e.event_type == "cms.redirect.created"} == {
        "/about", "/about/team"}


def test_a_draft_that_moves_leaves_no_redirect(staff_client):
    page = make_page(staff_client, "about")
    assert patch(staff_client, "page", page, slug="company").status_code == 200
    assert not Redirect.objects.exists()


def test_redirect_chains_collapse_and_never_loop(staff_client):
    page = make_page(staff_client, "a")
    publish(staff_client, "page", page["id"])
    for slug in ("b", "c", "a"):
        page = staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()
        assert patch(staff_client, "page", page, slug=slug).status_code == 200
    rows = set(Redirect.objects.values_list("old_path", "new_path"))
    assert rows == {("/b", "/a"), ("/c", "/a")}


def test_delete_only_what_was_never_published(staff_client):
    draft = make_page(staff_client, "draft")
    live = make_page(staff_client, "live")
    publish(staff_client, "page", live["id"])
    assert staff_client.delete(f"{V1}/staff/pages/{draft['id']}/").status_code == 204
    resp = staff_client.delete(f"{V1}/staff/pages/{live['id']}/")
    assert resp.status_code == 409 and err(resp) == "error.409.cms_delete_published"
    assert not Revision.objects.filter(kind="page", object_id=draft["id"]).exists()


def test_a_page_with_children_cannot_be_deleted(staff_client):
    a = make_page(staff_client, "a")
    make_page(staff_client, "b", parent=a["id"])
    assert staff_client.delete(f"{V1}/staff/pages/{a['id']}/").status_code == 400


def test_list_filters_and_pages(staff_client):
    for i in range(3):
        make_page(staff_client, f"p{i}")
    make_page(staff_client, "de", locale="de")
    resp = staff_client.get(f"{V1}/staff/pages/", {"locale": "en", "limit": 2})
    body = resp.json()
    assert body["count"] == 2 and body["has_next"] is True
    rest = staff_client.get(f"{V1}/staff/pages/", {"locale": "en", "anchor": body["next_anchor"]}).json()
    assert [p["path"] for p in rest["items"]] == ["/p0"]
    assert staff_client.get(f"{V1}/staff/pages/", {"q": "P1"}).json()["items"][0]["path"] == "/p1"
    assert staff_client.get(f"{V1}/staff/pages/", {"parent": "root", "locale": "de"}).json()["count"] == 1
    assert staff_client.get(f"{V1}/staff/pages/", {"anchor": "garbage"}).status_code == 200


def test_staff_endpoints_refuse_everyone_else(api_client, client_for, user, guest):
    assert api_client.get(f"{V1}/staff/pages/").status_code in (401, 403)
    assert client_for(user).get(f"{V1}/staff/pages/").status_code == 403
    assert client_for(guest).get(f"{V1}/staff/pages/").status_code == 403


def test_model_perms_mode_asks_the_mandate(client_for, staff, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "STAFF_AUTHZ": "model_perms"}
    client = client_for(staff)
    assert client.get(f"{V1}/staff/pages/").status_code == 403
    from django.contrib.auth.models import Permission

    staff.user_permissions.add(Permission.objects.get(codename="view_page"))
    staff = type(staff).objects.get(pk=staff.pk)
    assert client_for(staff).get(f"{V1}/staff/pages/").status_code == 200
    assert client_for(staff).post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "x"},
                                  format="json").status_code == 403
