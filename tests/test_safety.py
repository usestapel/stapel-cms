"""Untrusted content: the payload table every link and document passes.

The rich-text document is a typed tree, so "sanitising" means refusing: an
unknown node, an attribute outside the model, or a link outside the safe
prefixes is a 400, and plain text is stored as characters.
"""
import pytest

from stapel_cms.blocks import BlockError, validate_blocks
from stapel_cms.safety import embed_host_allowed, is_safe_url

from .helpers import V1, doc, err, make_page

UNSAFE_URLS = [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "&#106;avascript:alert(1)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "vbscript:msgbox(1)",
    "//evil.example/x",
    "\\\\evil.example",
    "https://user@evil.example/",
    "https://",
    "/ok\"onmouseover=\"alert(1)",
    "",
]
SAFE_URLS = ["https://example.com/a?b=c#d", "http://example.com", "/about/team", "#faq", "mailto:hi@example.com",
             "tel:+15550100"]


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_unsafe_urls_are_refused(url):
    assert not is_safe_url(url)


@pytest.mark.parametrize("url", SAFE_URLS)
def test_safe_urls_pass(url):
    """Inversion: the rule is not refusing everything."""
    assert is_safe_url(url)


def _rich(document):
    return [{"type": "rich_text", "id": "x", "data": {"doc": document}}]


def _link(href):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": "click", "marks": [{"type": "link", "attrs": {"href": href}}]}]}]}


@pytest.mark.parametrize("href", UNSAFE_URLS)
def test_link_marks_refuse_unsafe_hrefs(href):
    with pytest.raises(BlockError):
        validate_blocks(_rich(_link(href)))


def _deep(levels):
    node = {"type": "paragraph", "content": []}
    for _ in range(levels):
        node = {"type": "blockquote", "content": [node]}
    return {"type": "doc", "content": [node]}


HOSTILE_DOCUMENTS = {
    "script node": {"type": "doc", "content": [{"type": "script", "text": "alert(1)"}]},
    "html node": {"type": "doc", "content": [{"type": "html", "html": "<img src=x onerror=alert(1)>"}]},
    "iframe node": {"type": "doc", "content": [{"type": "iframe", "attrs": {"src": "https://evil.example"}}]},
    "style attribute": {"type": "doc", "content": [
        {"type": "paragraph", "attrs": {"style": "background:url(javascript:alert(1))"}, "content": []}]},
    "event handler attribute": {"type": "doc", "content": [
        {"type": "heading", "attrs": {"level": 2, "onclick": "alert(1)"}, "content": []}]},
    "class attribute on a text node": {"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": "x", "class": "x"}]}]},
    "unknown mark": {"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": "x", "marks": [{"type": "script"}]}]}]},
    "link with an extra attribute": {"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": "x", "marks": [{"type": "link", "attrs": {"href": "/a", "onclick": "x"}}]}]}]},
    "image with a raw url": {"type": "doc", "content": [
        {"type": "image", "attrs": {"media": "javascript:alert(1)", "alt": ""}}]},
    "nested too deep": _deep(13),
}


@pytest.mark.parametrize("name", sorted(HOSTILE_DOCUMENTS))
def test_hostile_documents_are_refused(name):
    with pytest.raises(BlockError) as info:
        validate_blocks(_rich(HOSTILE_DOCUMENTS[name]))
    assert info.value.key == "error.400.cms_blocks_invalid"


def test_depth_bound_is_the_limit_not_lower():
    """Inversion of the depth case: just under the limit passes."""
    assert validate_blocks(_rich(_deep(9)))


def test_script_text_is_plain_text():
    """A <script> typed into a paragraph is characters, stored verbatim and never parsed."""
    out = validate_blocks(_rich(doc("<script>alert(1)</script>")))
    assert out[0]["data"]["doc"]["content"][0]["content"][0]["text"] == "<script>alert(1)</script>"


def test_a_well_formed_document_passes():
    document = {"type": "doc", "content": [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Title"}]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "bold", "marks": [{"type": "bold"}]}, {"type": "hardBreak"},
            {"type": "text", "text": "link", "marks": [{"type": "link", "attrs": {"href": "https://example.com",
                                                                                   "new_tab": True}}]}]},
        {"type": "bulletList", "content": [{"type": "listItem", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "one"}]}]}]},
        {"type": "orderedList", "attrs": {"start": 3}, "content": [{"type": "listItem", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "three"}]}]}]},
        {"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "q"}]}]},
        {"type": "codeBlock", "attrs": {"language": "python"}, "content": [{"type": "text", "text": "x = 1"}]},
        {"type": "horizontalRule"},
        {"type": "image", "attrs": {"media": "page/abc123", "alt": "A picture"}},
    ]}
    assert validate_blocks(_rich(document))[0]["data"]["doc"]["content"][-1]["attrs"]["media"] == "page/abc123"


@pytest.mark.parametrize("url,ok", [
    ("https://www.youtube.com/embed/x", True),
    ("https://player.vimeo.com/video/1", True),
    ("http://www.youtube.com/embed/x", False),
    ("https://www.youtube.com.evil.example/embed", False),
    ("https://evil.example/?u=https://www.youtube.com", False),
    ("https://www.youtube.com:8443/embed/x", False),
    ("https://user@www.youtube.com/embed/x", False),
    ("javascript:alert(1)//www.youtube.com", False),
])
def test_embed_host_allowlist(url, ok):
    from stapel_cms.conf import DEFAULT_EMBED_HOSTS

    assert embed_host_allowed(url, DEFAULT_EMBED_HOSTS) is ok


def test_embed_block_refuses_a_foreign_host():
    with pytest.raises(BlockError):
        validate_blocks([{"type": "embed", "id": "e", "data": {"url": "https://evil.example/x", "title": "x"}}])


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [
    ("canonical_url", "javascript:alert(1)"),
    ("og_image", "javascript:alert(1)"),
])
def test_seo_links_are_checked(staff_client, field, value):
    resp = staff_client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "x", "title": "X", field: value},
                             format="json")
    assert resp.status_code == 400
    assert err(resp) == "error.400.cms_url_unsafe"


@pytest.mark.django_db
def test_hero_cta_refuses_javascript(staff_client):
    resp = staff_client.post(f"{V1}/staff/pages/", {
        "locale": "en", "slug": "x", "title": "X",
        "blocks": [{"type": "hero", "id": "h", "data": {"heading": "Hi", "cta": {
            "label": "Go", "href": "javascript:alert(document.cookie)"}}}]}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_menu_url_refuses_javascript(staff_client):
    make_page(staff_client, "about")
    resp = staff_client.post(f"{V1}/staff/menus/", {"locale": "en", "key": "header", "items": [
        {"label": "x", "target_type": "url", "url": "javascript:alert(1)"}]}, format="json")
    assert resp.status_code == 400
