"""Public answers carry described images next to bare refs, through cdn.describe_many by name."""
import pytest

from .fakes import FakeFunction
from .helpers import V1, make_page, make_post, patch, publish, resolve

pytestmark = pytest.mark.django_db

HERO = "cms/aaa111"
GALLERY = "cms/bbb222"
OG = "cms/ccc333"


def _snapshot(ref, relative=False):
    base = "" if relative else "https://cdn.example"
    return {"mime": "image/webp", "width": 1200, "height": 800, "aspect": 1.5, "square": False,
            "preview_b64": "data:x", "variants": [
                {"tier": 320, "branch": "w", "url": f"{base}/{ref}/320.webp", "width": 320, "height": 213,
                 "watermarked": False},
                {"tier": "original", "branch": None, "url": f"{base}/{ref}/orig.webp", "width": 1200,
                 "height": 800}]}


@pytest.fixture
def describer():
    def answer(payload):
        return {"items": {r: _snapshot(r) for r in payload["refs"] if r != GALLERY},
                "missing": [r for r in payload["refs"] if r == GALLERY]}

    fake = FakeFunction("cdn.describe_many", answer).install()
    yield fake
    fake.uninstall()


def _page(staff_client):
    page = make_page(staff_client, "about", og_image=OG, blocks=[
        {"type": "hero", "id": "h", "data": {"heading": "Hi", "media": HERO}},
        {"type": "gallery", "id": "g", "data": {"items": [{"media": GALLERY}, {"media": HERO}]}}])
    return publish(staff_client, "page", page["id"])


def test_resolve_carries_described_images_and_og_url(client, staff_client, describer):
    _page(staff_client)
    body = resolve(client, "/about").json()["page"]
    assert body["blocks"][0]["data"]["media"] == HERO  # bare refs stay
    assert [m["ref"] for m in body["media"]] == [OG, HERO]  # GALLERY is unknown to the cdn
    hero = body["media"][1]
    assert hero["url"] == f"https://cdn.example/{HERO}/orig.webp" and hero["source"] == "cdn"
    assert hero["variants"][0] == {"tier": "320", "branch": "w", "url": f"https://cdn.example/{HERO}/320.webp",
                                   "width": 320, "height": 213}
    assert body["seo"]["og_image"] == OG and body["seo"]["og_image_url"] == f"https://cdn.example/{OG}/orig.webp"
    assert len(describer.calls) == 1 and sorted(describer.calls[0]["refs"]) == sorted([OG, HERO, GALLERY])
    resolve(client, "/about")
    assert len(describer.calls) == 1  # cached with the page


def test_post_detail_describes_the_cover(client, staff_client, describer):
    post = make_post(staff_client, "hello", cover=HERO)
    publish(staff_client, "post", post["id"])
    body = client.get(f"{V1}/public/posts/hello/").json()
    assert [m["ref"] for m in body["media"]] == [HERO] and body["seo"]["og_image_url"] is None


def test_unreachable_describe_keeps_refs_only(client, staff_client):
    _page(staff_client)
    body = resolve(client, "/about").json()["page"]
    assert body["media"] == [] and body["seo"]["og_image_url"] is None
    assert body["seo"]["og_image"] == OG


def test_a_failing_describe_is_refs_only_never_an_error(client, staff_client):
    def boom(payload):
        raise RuntimeError("cdn down")

    fake = FakeFunction("cdn.describe_many", boom).install()
    try:
        _page(staff_client)
        resp = resolve(client, "/about")
        assert resp.status_code == 200 and resp.json()["page"]["media"] == []
    finally:
        fake.uninstall()


def test_relative_cdn_urls_become_absolute_on_the_site_origin(client, staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "SITE_ORIGIN": "https://www.example.com"}
    fake = FakeFunction("cdn.describe_many",
                        lambda p: {"items": {r: _snapshot(r, relative=True) for r in p["refs"]}, "missing": []})
    fake.install()
    try:
        page = make_page(staff_client, "about", og_image=OG)
        patch(staff_client, "page", page, title="About")
        publish(staff_client, "page", page["id"])
        assert resolve(client, "/about").json()["page"]["seo"]["og_image_url"] == \
            f"https://www.example.com/{OG}/orig.webp"
    finally:
        fake.uninstall()
