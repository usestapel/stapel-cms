"""Machine translation against the real stapel-translate ``translate.text``.

The provider is faked at stapel-translate's own ``LLM_PROVIDER`` seam (what a
host swaps); everything between cms and that seam — the Function, its
schema, its bounds, its batching and its errors — is the real package.
"""
import json
import re

import pytest

from stapel_cms.models import Page
from stapel_cms.services import translate as cms_translate
from stapel_cms.services.translate import split_text

from .helpers import V1, err, make_page
from .siblings import requires

pytestmark = pytest.mark.django_db

PROMPTS: list[str] = []
FAIL_AFTER: list[int] = []


class MockProvider:
    """Tags each text with the target language; fails once FAIL_AFTER calls are spent."""

    def complete(self, prompt):
        if FAIL_AFTER and len(PROMPTS) >= FAIL_AFTER[0]:
            from stapel_translate.providers import TranslationProviderError

            raise TranslationProviderError("provider down")
        PROMPTS.append(prompt)
        texts = json.loads(re.search(r"\[.*\]", prompt, re.DOTALL).group(0))
        target = re.search(r"\(([a-z-]+)\)\.\n", prompt).group(1)
        return json.dumps([f"[{target}] {t}" for t in texts], ensure_ascii=False)


@pytest.fixture
def real_translate(settings):
    from stapel_translate.providers import BaseTranslationProvider

    provider = type("Provider", (MockProvider, BaseTranslationProvider), {})
    globals()["Provider"] = provider
    settings.STAPEL_TRANSLATE = {"LLM_PROVIDER": f"{__name__}.Provider", "LANGUAGES": ["en", "de"]}
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE": "translate.text"}
    PROMPTS.clear()
    FAIL_AFTER.clear()
    yield
    FAIL_AFTER.clear()


def _variant(client, page_id):
    return client.post(f"{V1}/staff/pages/{page_id}/variants/", {"locale": "de", "machine_translate": True},
                       format="json")


def _text(text, *marks):
    return {"type": "text", "text": text, "marks": list(marks)}


RICH = {"type": "doc", "content": [
    {"type": "heading", "attrs": {"level": 2}, "content": [_text("Our story")]},
    {"type": "paragraph", "content": [
        _text("We bake "), _text("fresh bread", {"type": "bold"}), _text(" daily. Run "),
        _text("make bake", {"type": "code"}), _text(" or "),
        _text("call us", {"type": "link", "attrs": {"href": "https://example.com/call", "new_tab": False}}),
    ]},
    {"type": "codeBlock", "attrs": {"language": "python"}, "content": [_text("print('hi')")]},
    {"type": "image", "attrs": {"media": "image/abc123", "alt": "A loaf", "title": "Bread"}},
]}

PAGE_BLOCKS = [
    {"type": "hero", "id": "h", "data": {"heading": "Welcome", "subheading": "Since 1990", "media": "image/hero1",
                                        "cta": {"label": "Order", "href": "https://example.com/order"}}},
    {"type": "rich_text", "id": "r", "data": {"doc": RICH}},
    {"type": "faq", "id": "f", "data": {"title": "Questions", "items": [
        {"question": "Open on Sunday?", "answer": {"type": "doc", "content": [
            {"type": "paragraph", "content": [_text("Yes, until noon.")]}]}}]}},
    {"type": "gallery", "id": "g", "data": {"items": [{"media": "image/g1", "alt": "Oven", "caption": "Our oven"}]}},
    {"type": "embed", "id": "e", "data": {"url": "https://www.youtube.com/embed/x", "title": "Video"}},
    {"type": "form", "id": "fm", "data": {"form_id": "contact", "title": "Write to us"}},
    {"type": "listing_rail", "id": "l", "data": {"source": "listings", "query": {"title": "keep me"}}},
]


@requires("stapel_translate")
def test_a_real_page_is_translated_node_by_node(staff_client, settings, real_translate):
    page = make_page(staff_client, "about", title="About", seo_description="Who we are", blocks=PAGE_BLOCKS)
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["title"] == "[de] About" and body["seo_description"] == "[de] Who we are"
    blocks = {b["id"]: b["data"] for b in body["blocks"]}
    assert blocks["h"] == {"heading": "[de] Welcome", "subheading": "[de] Since 1990", "media": "image/hero1",
                           "align": "start", "cta": {"label": "[de] Order", "href": "https://example.com/order"}}
    doc = blocks["r"]["doc"]["content"]
    assert doc[0]["content"] == [_text("[de] Our story")]
    assert doc[1]["content"] == [
        _text("[de] We bake "), _text("[de] fresh bread", {"type": "bold"}), _text(" [de] daily. Run "),
        _text("make bake", {"type": "code"}), _text(" [de] or "),
        _text("[de] call us", {"type": "link", "attrs": {"href": "https://example.com/call", "new_tab": False}}),
    ]
    assert doc[2]["content"] == [_text("print('hi')")]
    assert doc[3]["attrs"] == {"media": "image/abc123", "alt": "[de] A loaf", "title": "[de] Bread"}
    assert blocks["f"]["title"] == "[de] Questions"
    assert blocks["f"]["items"][0]["question"] == "[de] Open on Sunday?"
    assert blocks["f"]["items"][0]["answer"]["content"][0]["content"] == [_text("[de] Yes, until noon.")]
    assert blocks["g"]["items"] == [{"media": "image/g1", "alt": "[de] Oven", "caption": "[de] Our oven"}]
    assert blocks["e"] == {"url": "https://www.youtube.com/embed/x", "title": "[de] Video", "aspect_ratio": "16:9"}
    assert blocks["fm"] == {"form_id": "contact", "title": "[de] Write to us"}
    assert blocks["l"]["query"] == {"title": "keep me"} and blocks["l"]["source"] == "listings"
    sent = [t for prompt in PROMPTS for t in json.loads(re.search(r"\[.*\]", prompt, re.DOTALL).group(0))]
    assert "make bake" not in sent and "print('hi')" not in sent and not any("{" in t for t in sent)


@requires("stapel_translate")
def test_a_long_text_node_is_split_at_sentences_and_rejoined(staff_client, real_translate):
    sentence = "This sentence is about bread and it is long enough to matter. "
    long_text = (sentence * 300).strip()
    assert 5000 < len(long_text) <= 20000
    page = make_page(staff_client, "long", blocks=[{"type": "rich_text", "id": "r", "data": {"doc": {
        "type": "doc", "content": [{"type": "paragraph", "content": [_text(long_text)]}]}}}])
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 201, resp.content
    out = resp.json()["blocks"][0]["data"]["doc"]["content"][0]["content"][0]["text"]
    parts = split_text(long_text, 5000)
    assert len(parts) == 4 and all(len(piece) <= 5000 for piece, _ in parts)
    assert out == "".join(f"[de] {piece}{sep}" for piece, sep in parts)
    assert all(piece.endswith(".") for piece, _ in parts)


@requires("stapel_translate")
def test_a_big_page_is_several_calls_in_order_with_a_timeout(staff_client, settings, real_translate,
                                                              monkeypatch):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE_MAX_ITEMS": 3,
                           "MACHINE_TRANSLATE_TIMEOUT_SECONDS": 42}
    from stapel_core import comm

    calls = []
    real_call = comm.call

    def spy(name, payload, **kwargs):
        calls.append((len(payload["texts"]), kwargs.get("timeout")))
        return real_call(name, payload, **kwargs)

    monkeypatch.setattr(comm, "call", spy)
    paragraphs = [f"Paragraph number {i}." for i in range(8)]
    page = make_page(staff_client, "big", title="Big", blocks=[{"type": "rich_text", "id": "r", "data": {"doc": {
        "type": "doc", "content": [{"type": "paragraph", "content": [_text(p)]} for p in paragraphs]}}}])
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 201, resp.content
    assert calls == [(3, 42.0), (3, 42.0), (3, 42.0)]
    texts = [p["content"][0]["text"] for p in resp.json()["blocks"][0]["data"]["doc"]["content"]]
    assert texts == [f"[de] {p}" for p in paragraphs]


@requires("stapel_translate")
def test_a_failure_on_a_later_call_creates_nothing(staff_client, settings, real_translate):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE_MAX_ITEMS": 2}
    page = make_page(staff_client, "about", title="About", blocks=[{"type": "rich_text", "id": "r", "data": {
        "doc": {"type": "doc", "content": [{"type": "paragraph", "content": [_text(f"Text {i}.")]}
                                           for i in range(5)]}}}])
    FAIL_AFTER.append(1)
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 503 and err(resp) == "error.503.cms_translation_unavailable"
    assert resp.json()["params"] == {"reason": "provider_failed",
                                     "upstream_error": "error.503.translate.unavailable"}
    assert len(PROMPTS) == 1
    assert not Page.objects.filter(locale="de").exists()


@requires("stapel_translate")
def test_no_provider_configured_is_503_not_configured(staff_client, settings, real_translate):
    settings.STAPEL_TRANSLATE = {"LLM_PROVIDER": "", "LANGUAGES": ["en", "de"]}
    page = make_page(staff_client, "about")
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 503
    assert resp.json()["params"] == {"reason": "not_configured",
                                     "upstream_error": "error.503.translate.unavailable"}
    assert not Page.objects.filter(locale="de").exists()


@requires("stapel_translate")
def test_a_refusal_is_503_refused(staff_client, settings, real_translate):
    settings.STAPEL_TRANSLATE = {**settings.STAPEL_TRANSLATE, "LANGUAGES": ["en"]}
    page = make_page(staff_client, "about")
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 503
    assert resp.json()["params"] == {"reason": "refused",
                                     "upstream_error": "error.400.translate.unsupported_language"}


@requires("stapel_translate")
def test_cms_never_exceeds_the_neighbours_bounds(staff_client, settings, real_translate):
    """Inversion control: with cms's own bounds lifted, the real Function refuses the same page."""
    long_text = ("Bread is good. " * 400).strip()
    page = make_page(staff_client, "long", blocks=[{"type": "rich_text", "id": "r", "data": {"doc": {
        "type": "doc", "content": [{"type": "paragraph", "content": [_text(long_text)]}]}}}])
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE_MAX_TEXT_CHARS": 20000}
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 503
    assert resp.json()["params"] == {"reason": "refused", "upstream_error": "error.400.translate.text_too_long"}


def test_split_text_round_trips_and_bounds():
    assert split_text("short", 10) == [("short", "")]
    for text, limit in [("One. Two! Three? Four.", 9), ("a " * 50, 7), ("x" * 25, 10),
                        ("  Lead. Trail  ", 6), ("Satz eins.\n\nSatz zwei.", 12)]:
        parts = split_text(text, limit)
        assert "".join(piece + sep for piece, sep in parts) == text
        assert all(len(piece) <= limit for piece, _ in parts)
    assert [p for p, _ in split_text("One. Two. Three.", 10)] == ["One. Two.", "Three."]


def test_block_types_publish_the_translatable_marks(staff_client):
    items = {i["type"]: i["schema"] for i in staff_client.get(f"{V1}/staff/block-types/").json()["items"]}
    hero = items["hero"]
    assert hero["properties"]["heading"]["x-cms-translatable"] is True
    assert "x-cms-translatable" not in hero["properties"]["media"]
    assert items["rich_text"]["$defs"]["RichDoc"]["x-cms-richtext"] is True


def test_unreachable_function_is_503_unreachable(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MACHINE_TRANSLATE": "nobody.translates"}
    page = make_page(staff_client, "about")
    resp = _variant(staff_client, page["id"])
    assert resp.status_code == 503 and resp.json()["params"] == {"reason": "unreachable"}
    assert cms_translate.translate_texts([" ", ""], "en", "de") == {}
