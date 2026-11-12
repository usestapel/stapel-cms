"""cms as a provider of stapel-core's sitemap aggregator, through core's own view."""
import xml.etree.ElementTree as ET

import pytest
from stapel_core.comm import call

from stapel_cms import checks as cms_checks
from stapel_cms import sitekeys
from stapel_cms.services import sitemaps

from .helpers import V1, make_page, make_post, patch, publish, transition
from .siblings import installed

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(not installed("stapel_core.django.sitemap"), reason="core without the sitemap aggregator"),
]

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "xhtml": "http://www.w3.org/1999/xhtml"}
ORIGIN = "https://cms.example"


@pytest.fixture(autouse=True)
def _origin(settings):
    settings.STAPEL_SITEMAP = {"ORIGIN": ORIGIN, "URL_TEMPLATE": "{origin}/{locale}{path}"}


def _urls(client):
    index = client.get("/sitemap.xml")
    assert index.status_code == 200 and index["Content-Type"].startswith("application/xml")
    root = ET.fromstring(index.content)
    assert root.tag == f"{{{NS['sm']}}}sitemapindex"
    out = {}
    for loc in root.findall("sm:sitemap/sm:loc", NS):
        page = client.get(loc.text.replace(ORIGIN, ""))
        assert page.status_code == 200
        urlset = ET.fromstring(page.content)
        assert urlset.tag == f"{{{NS['sm']}}}urlset"
        for url in urlset.findall("sm:url", NS):
            assert [child.tag.split("}")[1] for child in url][:1] == ["loc"]
            alternates = {link.get("hreflang"): link.get("href") for link in url.findall("xhtml:link", NS)}
            assert all(link.get("rel") == "alternate" for link in url.findall("xhtml:link", NS))
            out[url.find("sm:loc", NS).text] = {"lastmod": url.findtext("sm:lastmod", None, NS),
                                                "alternates": alternates}
    return out


def test_cms_is_a_registered_provider():
    from stapel_core.django.sitemap import sitemap_providers

    assert sitemap_providers()["cms"] == "cms.sitemap_entries"


def test_sitemap_xml_lists_published_indexable_content_with_hreflang(client, staff_client):
    about = publish(staff_client, "page", make_page(staff_client, "about")["id"])
    de = staff_client.post(f"{V1}/staff/pages/{about['id']}/variants/", {"locale": "de"}, format="json").json()
    publish(staff_client, "page", de["id"])
    hidden = make_page(staff_client, "hidden")
    patch(staff_client, "page", hidden, noindex=True)
    publish(staff_client, "page", hidden["id"])
    make_page(staff_client, "draft")
    publish(staff_client, "post", make_post(staff_client, "hello")["id"])

    urls = _urls(client)
    assert sorted(urls) == [f"{ORIGIN}/de/about", f"{ORIGIN}/en/about", f"{ORIGIN}/en/blog/hello"]
    pair = {"de": f"{ORIGIN}/de/about", "en": f"{ORIGIN}/en/about"}
    assert urls[f"{ORIGIN}/en/about"]["alternates"] == pair
    assert urls[f"{ORIGIN}/de/about"]["alternates"] == pair
    assert urls[f"{ORIGIN}/en/blog/hello"]["alternates"] == {}
    assert all(u["lastmod"] and u["lastmod"].endswith("+00:00") for u in urls.values())


def test_a_noindex_variant_is_not_an_alternate(staff_client):
    about = publish(staff_client, "page", make_page(staff_client, "about")["id"])
    de = staff_client.post(f"{V1}/staff/pages/{about['id']}/variants/", {"locale": "de"}, format="json").json()
    patch(staff_client, "page", de, noindex=True)
    publish(staff_client, "page", de["id"])
    out = call("cms.sitemap_entries", {"site": "", "locale": None, "cursor": None, "limit": 10})
    assert [(e["path"], e["locale"], e["alternates"]) for e in out["entries"]] == [("/about", "en", [])]


def test_publish_unpublish_and_move_drop_the_cached_set(client, staff_client):
    first = publish(staff_client, "page", make_page(staff_client, "first")["id"])
    assert list(_urls(client)) == [f"{ORIGIN}/en/first"]
    second = publish(staff_client, "page", make_page(staff_client, "second")["id"])
    assert sorted(_urls(client)) == [f"{ORIGIN}/en/first", f"{ORIGIN}/en/second"]
    assert patch(staff_client, "page", second, slug="moved").status_code == 200
    assert sorted(_urls(client)) == [f"{ORIGIN}/en/first", f"{ORIGIN}/en/moved"]
    assert transition(staff_client, "page", first["id"], "archived").status_code == 200
    assert sorted(_urls(client)) == [f"{ORIGIN}/en/moved"]


def test_without_invalidation_the_set_stays_cached(client, staff_client, monkeypatch):
    """Inversion control: the freshness above is cms's invalidation, not a cache miss."""
    publish(staff_client, "page", make_page(staff_client, "first")["id"])
    assert list(_urls(client)) == [f"{ORIGIN}/en/first"]
    monkeypatch.setattr(sitemaps, "invalidate", lambda site: None)
    publish(staff_client, "page", make_page(staff_client, "second")["id"])
    assert list(_urls(client)) == [f"{ORIGIN}/en/first"]


def test_the_answer_is_the_provider_contract(staff_client):
    for slug in ("a", "b", "c"):
        publish(staff_client, "page", make_page(staff_client, slug)["id"])
    publish(staff_client, "post", make_post(staff_client, "p")["id"])
    seen, cursor, calls = [], None, 0
    while True:
        out = call("cms.sitemap_entries", {"site": "", "locale": None, "cursor": cursor, "limit": 2})
        calls += 1
        assert set(out) == {"entries", "cursor"} and len(out["entries"]) <= 2
        for entry in out["entries"]:
            assert entry["path"].startswith("/") and entry["locale"] == "en"
            assert set(entry) == {"path", "locale", "lastmod", "kind", "alternates"}
        seen += [e["path"] for e in out["entries"]]
        cursor = out["cursor"]
        if cursor is None:
            break
    assert seen == ["/a", "/b", "/c", "/blog/p"] and calls == 3  # the third batch is empty


@pytest.mark.parametrize("limit,expected", [(0, 500), (None, 500), (10**9, 5000), (3, 3)])
def test_limit_is_bounded(monkeypatch, limit, expected):
    """The Function schema refuses out-of-range limits on the wire; the clamp is the last line."""
    from stapel_cms.functions import sitemap_entries
    from stapel_cms.services import public

    seen = {}
    monkeypatch.setattr(public, "sitemap_entries",
                        lambda site, locale, cursor, n: seen.update(n=n) or {"entries": [], "cursor": None})
    sitemap_entries({"site": "", "limit": limit})
    assert seen["n"] == expected


def test_a_foreign_cursor_starts_over(staff_client):
    publish(staff_client, "page", make_page(staff_client, "a")["id"])
    assert [e["path"] for e in call("cms.sitemap_entries", {"site": "", "cursor": "junk"})["entries"]] == ["/a"]


def test_blog_off_lists_no_posts(staff_client, settings):
    publish(staff_client, "post", make_post(staff_client, "p")["id"])
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "BLOG_ENABLED": False}
    assert call("cms.sitemap_entries", {"site": ""})["entries"] == []


def test_site_keys_are_core_site_keys(settings):
    from stapel_core.django.sites import site_registry

    settings.STAPEL_SITES = {"sites": [{"host": "shop.example", "brand": {"key": "acme", "name": "Acme"},
                                        "primary": True},
                                       {"host": "plain.example"}]}
    assert sitekeys.site_keys() == tuple(site.key for site in site_registry().sites) == ("acme", "plain.example")


def test_w003_without_locale_in_the_url_template(settings):
    assert "stapel_cms.W003" not in {f.id for f in cms_checks.check_integrations(None)}
    settings.STAPEL_SITEMAP = {"URL_TEMPLATE": "{origin}{path}"}
    assert "stapel_cms.W003" in {f.id for f in cms_checks.check_integrations(None)}
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "LOCALES": ["en"]}
    assert "stapel_cms.W003" not in {f.id for f in cms_checks.check_integrations(None)}
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "LOCALES": ["en", "de"]}
    settings.STAPEL_SITEMAP = {"URL_TEMPLATE": "{origin}{path}", "PROVIDERS": {"cms": None}}
    assert "stapel_cms.W003" not in {f.id for f in cms_checks.check_integrations(None)}


def test_an_older_core_registers_nothing(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "stapel_core.django.sitemap", None)
    assert sitemaps.aggregator() is None
    assert sitemaps.register_provider() is False
    sitemaps.invalidate("")  # a no-op, never an error
    assert "stapel_cms.W003" not in {f.id for f in cms_checks.check_integrations(None)}
