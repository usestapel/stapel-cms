"""The anonymous read side: resolve, locales, caching, preview, blog, menus, sites."""
import datetime as dt

import pytest
from django.core import signing
from django.utils import timezone

from stapel_cms.models import Post

from .helpers import V1, err, make_page, make_post, patch, publish, resolve

pytestmark = pytest.mark.django_db


def _live_page(staff_client, slug="about", **kw):
    page = make_page(staff_client, slug, **kw)
    return publish(staff_client, "page", page["id"])


def test_resolve_a_page_with_seo_breadcrumbs_and_blocks(staff_client, api_client):
    parent = _live_page(staff_client, "about", title="About")
    make_page(staff_client, "team", parent=parent["id"], title="Team", seo_description="The people",
              og_image="page/team1")
    team = staff_client.get(f"{V1}/staff/pages/").json()["items"][0]
    publish(staff_client, "page", team["id"])
    body = resolve(api_client, "about/team/").json()
    page = body["page"]
    assert body["kind"] == "page" and body["locale"] == "en"
    assert page["breadcrumbs"] == [{"title": "About", "path": "/about"}]
    assert page["seo"] == {"title": "Team", "description": "The people", "canonical_url": None,
                           "og_image": "page/team1", "og_image_url": None, "noindex": False}
    assert page["blocks"][0]["type"] == "rich_text"


def test_unknown_path_is_404(api_client):
    resp = resolve(api_client, "/nowhere")
    assert resp.status_code == 404 and err(resp) == "error.404.cms_not_found"


def test_locale_fallback_and_alternates(staff_client, api_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "LOCALES": ["en", "de", "de-at"],
                           "LOCALE_FALLBACKS": {"de-at": ["de"]}}
    en = _live_page(staff_client, "about", title="About")
    de = staff_client.post(f"{V1}/staff/pages/{en['id']}/variants/", {"locale": "de"}, format="json").json()
    patch(staff_client, "page", de, title="Ueber uns")
    publish(staff_client, "page", de["id"])
    at = resolve(api_client, "/about", locale="de-at").json()
    assert at["locale"] == "de" and at["page"]["title"] == "Ueber uns"
    assert at["page"]["alternates"] == [{"locale": "de", "path": "/about"}, {"locale": "en", "path": "/about"}]
    only_en = _live_page(staff_client, "contacts")
    assert resolve(api_client, "/contacts", locale="de").json()["locale"] == "en"
    assert only_en["translation_group"] != en["translation_group"]


def test_etag_and_last_modified_answer_304(staff_client, api_client):
    _live_page(staff_client, "about")
    first = resolve(api_client, "/about")
    etag, last_modified = first["ETag"], first["Last-Modified"]
    assert first["Cache-Control"].startswith("public, max-age=")
    again = api_client.get(f"{V1}/public/resolve/", {"path": "/about"}, HTTP_IF_NONE_MATCH=etag)
    assert again.status_code == 304 and again["ETag"] == etag
    since = api_client.get(f"{V1}/public/resolve/", {"path": "/about"}, HTTP_IF_MODIFIED_SINCE=last_modified)
    assert since.status_code == 304
    stale = api_client.get(f"{V1}/public/resolve/", {"path": "/about"}, HTTP_IF_NONE_MATCH='"other"')
    assert stale.status_code == 200


def test_publish_invalidates_the_cached_body(staff_client, api_client):
    page = _live_page(staff_client, "about", title="Old")
    old = resolve(api_client, "/about")
    assert old.json()["page"]["title"] == "Old"
    from stapel_cms.models import Page

    Page.objects.filter(pk=page["id"]).update(title="Sneaky")
    assert resolve(api_client, "/about")["ETag"] == old["ETag"], "the second read must come from the cache"
    page = staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()
    patch(staff_client, "page", page, title="New")
    publish(staff_client, "page", page["id"])
    new = resolve(api_client, "/about")
    assert new.json()["page"]["title"] == "New" and new["ETag"] != old["ETag"]


def test_preview_token_shows_the_working_copy(staff_client, api_client):
    page = make_page(staff_client, "secret", title="Draft title")
    minted = staff_client.post(f"{V1}/staff/pages/{page['id']}/preview-token/").json()
    resp = api_client.get(f"{V1}/public/preview/", {"token": minted["token"]})
    assert resp.status_code == 200 and resp["Cache-Control"] == "private, no-store"
    assert resp.json()["page"]["title"] == "Draft title" and resp.json()["page"]["seo"]["noindex"] is True
    assert resolve(api_client, "/secret").status_code == 404


def test_preview_token_forged_or_expired(staff_client, api_client, settings):
    page = make_page(staff_client, "secret")
    forged = signing.TimestampSigner(salt="other").sign_object({"k": "page", "i": page["id"]})
    resp = api_client.get(f"{V1}/public/preview/", {"token": forged})
    assert resp.status_code == 404 and err(resp) == "error.404.cms_preview_invalid"
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "PREVIEW_TOKEN_TTL_SECONDS": -1}
    token = staff_client.post(f"{V1}/staff/pages/{page['id']}/preview-token/").json()["token"]
    assert api_client.get(f"{V1}/public/preview/", {"token": token}).status_code == 404


def test_preview_url_template(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "PREVIEW_URL_TEMPLATE": "https://example.com/p?t={token}"}
    page = make_page(staff_client, "x")
    minted = staff_client.post(f"{V1}/staff/pages/{page['id']}/preview-token/").json()
    assert minted["url"] == f"https://example.com/p?t={minted['token']}"


def _live_post(staff_client, slug, published_at=None, **kw):
    post = make_post(staff_client, slug, **kw)
    body = publish(staff_client, "post", post["id"])
    if published_at is not None:
        Post.objects.filter(pk=post["id"]).update(published_at=published_at)
    return body


def test_blog_list_pages_newest_first(staff_client, api_client):
    base = timezone.now() - dt.timedelta(days=10)
    for i in range(5):
        _live_post(staff_client, f"p{i}", base + dt.timedelta(days=i))
    make_post(staff_client, "draft")
    first = api_client.get(f"{V1}/public/posts/", {"limit": 2}).json()
    assert [p["slug"] for p in first["items"]] == ["p4", "p3"] and first["has_next"]
    second = api_client.get(f"{V1}/public/posts/", {"limit": 2, "anchor": first["next_anchor"]}).json()
    assert [p["slug"] for p in second["items"]] == ["p2", "p1"]
    back = api_client.get(f"{V1}/public/posts/", {"limit": 2, "anchor": second["prev_anchor"],
                                                  "direction": "prev"}).json()
    assert [p["slug"] for p in back["items"]] == ["p4", "p3"]


def test_tag_and_date_archives(staff_client, api_client):
    tag = staff_client.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "News"},
                            format="json").json()
    _live_post(staff_client, "jan", dt.datetime(2026, 1, 5, tzinfo=dt.timezone.utc), tags=[tag["id"]])
    _live_post(staff_client, "feb", dt.datetime(2026, 2, 5, tzinfo=dt.timezone.utc))
    tagged = api_client.get(f"{V1}/public/posts/", {"tag": "news"}).json()
    assert [p["slug"] for p in tagged["items"]] == ["jan"] and tagged["items"][0]["tags"][0]["name"] == "News"
    month = api_client.get(f"{V1}/public/posts/", {"year": 2026, "month": 2}).json()
    assert [p["slug"] for p in month["items"]] == ["feb"]
    archive = api_client.get(f"{V1}/public/post-archive/").json()
    assert archive["months"] == [{"year": 2026, "month": 2, "count": 1}, {"year": 2026, "month": 1, "count": 1}]
    assert api_client.get(f"{V1}/public/tags/").json()["items"] == [{"slug": "news", "name": "News", "count": 1}]


def test_reading_time_is_derived(staff_client, api_client):
    words = " ".join(["word"] * 450)
    _live_post(staff_client, "long", blocks=[{"type": "rich_text", "id": "b", "data": {"doc": {
        "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": words}]}]}}}])
    assert api_client.get(f"{V1}/public/posts/long/").json()["reading_time_minutes"] == 3


@pytest.mark.parametrize("fmt,marker", [("rss", "<rss"), ("atom", "<feed")])
def test_feed(staff_client, api_client, fmt, marker):
    _live_post(staff_client, "hello", title="Hello world")
    resp = api_client.get(f"{V1}/public/feed/", {"type": fmt})
    text = resp.content.decode()
    assert resp.status_code == 200 and marker in text and "Hello world" in text and "/blog/hello" in text


def test_menu_resolves_targets_and_drops_unpublished(staff_client, api_client):
    live = _live_page(staff_client, "about")
    draft = make_page(staff_client, "draft")
    menu = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "header", "title": "Header", "items": [
        {"label": "About", "target_type": "page", "page": live["id"], "children": [
            {"label": "Docs", "target_type": "url", "url": "https://example.com/docs", "new_tab": True}]},
        {"label": "Hidden", "target_type": "page", "page": draft["id"]},
        {"label": "Account", "target_type": "route", "route": "account.root", "route_params": {"tab": "orders"}},
    ]}, format="json")
    assert menu.status_code == 201, menu.content
    body = api_client.get(f"{V1}/public/menus/header/").json()
    assert [i["label"] for i in body["items"]] == ["About", "Account"]
    assert body["items"][0]["href"] == "/about" and body["items"][0]["children"][0]["new_tab"] is True
    assert body["items"][1] == {"label": "Account", "target_type": "route", "href": None, "route": "account.root",
                                "route_params": {"tab": "orders"}, "new_tab": False, "children": []}
    assert api_client.get(f"{V1}/public/menus/footer/").status_code == 404


SITES = {"sites": [
    {"host": "shop.example", "primary": True, "brand": {"key": "acme", "name": "Acme"}},
    {"host": "nord.example", "brand": {"key": "nord", "name": "Nord"}},
]}


def test_content_is_site_scoped(staff_client, api_client, settings):
    settings.STAPEL_SITES = SITES
    page = make_page(staff_client, "about", site="nord", title="Nord about")
    publish(staff_client, "page", page["id"])
    assert api_client.get(f"{V1}/public/resolve/", {"path": "/about"}, HTTP_HOST="nord.example").status_code == 200
    assert api_client.get(f"{V1}/public/resolve/", {"path": "/about"}, HTTP_HOST="shop.example").status_code == 404
    resp = staff_client.post(f"{V1}/staff/pages/", {"site": "", "locale": "en", "slug": "x", "title": "x"},
                             format="json")
    assert resp.status_code == 400 and err(resp) == "error.400.cms_site_unknown"


def test_blog_disabled_unmounts_the_blog(settings):
    import importlib

    from django.urls import clear_url_caches

    from stapel_cms import urls_v1

    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "BLOG_ENABLED": False}
    try:
        names = {p.name for p in importlib.reload(urls_v1).urlpatterns}
        assert "cms-public-posts" not in names and "cms-public-resolve" in names
    finally:
        settings.STAPEL_CMS = {**settings.STAPEL_CMS, "BLOG_ENABLED": True}
        importlib.reload(urls_v1)
        clear_url_caches()
