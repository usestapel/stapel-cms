"""The block registry: built-ins, MERGE over settings, runtime door, schemas."""
import pytest

from stapel_cms.blocks import (
    BUILTIN_BLOCK_TYPES,
    BlockError,
    get_block_types,
    register_block_type,
    validate_blocks,
)

from .helpers import V1, doc

VALID = {
    "rich_text": {"doc": doc("x")},
    "hero": {"heading": "Hi", "subheading": "s", "media": "page/h1", "cta": {"label": "Go", "href": "/go"},
             "align": "center"},
    "faq": {"items": [{"question": "Q?", "answer": doc("A.")}]},
    "gallery": {"layout": "carousel", "items": [{"media": "page/g1", "alt": "one"}]},
    "embed": {"url": "https://www.youtube.com/embed/abc", "title": "Video"},
    "form": {"form_id": "contact-us"},
    "listing_rail": {"source": "listings", "query": {"category": "cars", "sort": "-created"}, "limit": 6},
}


def test_every_builtin_has_a_valid_example():
    assert set(VALID) == set(BUILTIN_BLOCK_TYPES)


@pytest.mark.parametrize("btype", sorted(VALID))
def test_builtin_blocks_validate(btype):
    out = validate_blocks([{"type": btype, "id": "b", "data": VALID[btype]}])
    assert out[0]["type"] == btype


@pytest.mark.parametrize("btype,data", [
    ("hero", {"heading": ""}),
    ("hero", {"heading": "x", "media": "not a ref"}),
    ("faq", {"items": []}),
    ("gallery", {"items": [{"media": "page/x", "alt": "a", "onload": "x"}]}),
    ("form", {"form_id": "bad id!"}),
    ("listing_rail", {"source": "listings", "query": {"q": "x" * 3000}}),
    ("listing_rail", {"source": "listings", "limit": 100}),
])
def test_builtin_blocks_refuse_bad_data(btype, data):
    with pytest.raises(BlockError):
        validate_blocks([{"type": btype, "id": "b", "data": data}])


def test_settings_merge_adds_and_removes(settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "BLOCK_TYPES": {
        "pricing_table": "stapel_cms.tests.custom_blocks.PricingTable", "listing_rail": None}}
    types = get_block_types()
    assert "pricing_table" in types and "listing_rail" not in types and "hero" in types
    assert validate_blocks([{"type": "pricing_table", "id": "p", "data": {"plans": ["basic"]}}])
    with pytest.raises(BlockError) as info:
        validate_blocks([{"type": "listing_rail", "id": "l", "data": VALID["listing_rail"]}])
    assert info.value.key == "error.400.cms_block_type_unknown"


def test_runtime_registration():
    from .custom_blocks import PricingTable

    register_block_type("pricing_table", PricingTable)
    assert validate_blocks([{"type": "pricing_table", "id": "p", "data": {"plans": ["a"]}}])
    register_block_type("hero", None)
    assert "hero" not in get_block_types()
    with pytest.raises(ValueError):
        register_block_type("Bad-Name", PricingTable)


def test_block_envelope_is_strict():
    for raw in ([{"type": "form", "id": "f", "data": {"form_id": "x"}, "html": "<b>"}],
                [{"type": "form", "data": {"form_id": "x"}}], "not a list"):
        with pytest.raises(BlockError):
            validate_blocks(raw)


@pytest.mark.django_db
def test_block_types_endpoint_publishes_schemas(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "BLOCK_TYPES": {
        "pricing_table": "stapel_cms.tests.custom_blocks.PricingTable"}}
    items = staff_client.get(f"{V1}/staff/block-types/").json()["items"]
    by_type = {i["type"]: i["schema"] for i in items}
    assert set(by_type) == set(BUILTIN_BLOCK_TYPES) | {"pricing_table"}
    assert by_type["hero"]["additionalProperties"] is False
    assert "plans" in by_type["pricing_table"]["properties"]
