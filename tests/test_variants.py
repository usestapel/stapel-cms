"""Locale variants and optional machine translation through a Function."""
import pytest

from .fakes import FakeFunction
from .helpers import V1, err, make_page, make_post, rich

pytestmark = pytest.mark.django_db

TRANSLATOR = "test.translate_text"


@pytest.fixture
def translator(settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE": TRANSLATOR}
    fake = FakeFunction(TRANSLATOR, lambda p: {"texts": [f"[{p['target']}] {t}" for t in p["texts"]]}).install()
    yield fake
    fake.uninstall()


def test_variant_copies_into_the_locale_and_shares_the_group(staff_client):
    parent = make_page(staff_client, "about")
    child = make_page(staff_client, "team", parent=parent["id"])
    de_parent = staff_client.post(f"{V1}/staff/pages/{parent['id']}/variants/", {"locale": "de"},
                                  format="json").json()
    de_child = staff_client.post(f"{V1}/staff/pages/{child['id']}/variants/", {"locale": "de"}, format="json")
    assert de_child.status_code == 201
    body = de_child.json()
    assert body["locale"] == "de" and body["status"] == "draft" and body["parent"] == de_parent["id"]
    assert body["translation_group"] == child["translation_group"] and body["path"] == "/about/team"
    again = staff_client.post(f"{V1}/staff/pages/{child['id']}/variants/", {"locale": "de"}, format="json")
    assert again.status_code == 409 and err(again) == "error.409.cms_variant_exists"


def test_machine_translation_translates_text_leaves_only(staff_client, translator):
    page = make_page(staff_client, "about", title="About", seo_description="Who we are",
                     blocks=[rich("Hello"), {"type": "embed", "id": "e", "data": {
                         "url": "https://www.youtube.com/embed/x", "title": "Video"}},
                         {"type": "listing_rail", "id": "l", "data": {"source": "listings",
                                                                       "query": {"title": "keep me"}}}])
    resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/variants/",
                             {"locale": "de", "machine_translate": True}, format="json")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["title"] == "[de] About" and body["seo_description"] == "[de] Who we are"
    blocks = {b["id"]: b for b in body["blocks"]}
    assert blocks["b1"]["data"]["doc"]["content"][0]["content"][0]["text"] == "[de] Hello"
    assert blocks["e"]["data"]["url"] == "https://www.youtube.com/embed/x"
    assert blocks["e"]["data"]["title"] == "[de] Video"
    assert blocks["l"]["data"]["query"] == {"title": "keep me"}
    assert len(translator.calls) == 1 and translator.calls[0]["source"] == "en"


def test_machine_translation_unavailable_is_503(staff_client, settings):
    page = make_page(staff_client, "about")
    resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/variants/",
                             {"locale": "de", "machine_translate": True}, format="json")
    assert resp.status_code == 503 and err(resp) == "error.503.cms_translation_unavailable"
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE": "nobody.translates"}
    resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/variants/",
                             {"locale": "de", "machine_translate": True}, format="json")
    assert resp.status_code == 503


def test_a_malformed_translation_is_refused(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE": TRANSLATOR}
    fake = FakeFunction(TRANSLATOR, {"texts": ["only one"]}).install()
    try:
        page = make_page(staff_client, "about", title="A", seo_title="B")
        resp = staff_client.post(f"{V1}/staff/pages/{page['id']}/variants/",
                                 {"locale": "de", "machine_translate": True}, format="json")
        assert resp.status_code == 503
    finally:
        fake.uninstall()


def test_post_variant_maps_tags_by_slug(staff_client):
    en_tag = staff_client.post(f"{V1}/staff/tags/", {"locale": "en", "slug": "news", "name": "News"},
                               format="json").json()
    staff_client.post(f"{V1}/staff/tags/", {"locale": "de", "slug": "news", "name": "Neues"}, format="json")
    post = make_post(staff_client, "hello", tags=[en_tag["id"]])
    resp = staff_client.post(f"{V1}/staff/posts/{post['id']}/variants/", {"locale": "de"}, format="json")
    assert resp.status_code == 201 and [t["name"] for t in resp.json()["tags"]] == ["Neues"]
