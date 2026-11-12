"""The form block against the real stapel-forms ``forms.form.exists``."""
import pytest

from .helpers import V1, err, make_page, patch, publish, transition, in_future
from .siblings import requires

pytestmark = pytest.mark.django_db


def _form_block(form_id, bid="f"):
    return {"type": "form", "id": bid, "data": {"form_id": form_id, "title": "Write to us"}}


def _create(client, blocks):
    return client.post(f"{V1}/staff/pages/", {"locale": "en", "slug": "contact", "title": "Contact",
                                              "blocks": blocks}, format="json")


@requires("stapel_forms")
def test_a_published_form_saves_and_publishes_without_warnings(staff_client):
    from .neighbours import make_form

    form_id = make_form(published=True)
    resp = _create(staff_client, [_form_block(form_id)])
    assert resp.status_code == 201 and resp.json()["warnings"] == []
    published = transition(staff_client, "page", resp.json()["id"], "published")
    assert published.status_code == 200 and published.json()["warnings"] == []


@requires("stapel_forms")
def test_an_unknown_form_is_a_field_level_refusal(staff_client):
    from .neighbours import delete_form, make_form

    resp = _create(staff_client, [{"type": "hero", "id": "h", "data": {"heading": "Hi"}}, _form_block("nosuchform")])
    assert resp.status_code == 400 and err(resp) == "error.400.cms_form_unknown"
    assert resp.json()["params"] == {"field": "blocks.1.data.form_id", "form_id": "nosuchform"}
    gone = make_form(published=True)
    delete_form(gone)
    assert err(_create(staff_client, [_form_block(gone)])) == "error.400.cms_form_unknown"


@requires("stapel_forms")
def test_an_unpublished_form_is_a_draft_warning_and_a_publish_refusal(staff_client):
    from stapel_forms.models import Form

    from .neighbours import make_form

    form_id = make_form(published=False)
    resp = _create(staff_client, [_form_block(form_id)])
    assert resp.status_code == 201
    assert resp.json()["warnings"] == [{"code": "form_unpublished", "field": "blocks.0.data.form_id",
                                        "params": {"form_id": form_id}}]
    page = resp.json()
    for to, extra in (("published", {}), ("scheduled", {"publish_at": in_future().isoformat()})):
        refused = staff_client.post(f"{V1}/staff/pages/{page['id']}/transition/", {"to": to, **extra},
                                    format="json")
        assert refused.status_code == 409 and err(refused) == "error.409.cms_form_unpublished"
        assert refused.json()["params"] == {"field": "blocks.0.data.form_id", "form_id": form_id}
    assert staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()["status"] == "draft"
    form = Form.objects.get(public_id=form_id)
    from stapel_forms.models import FormVersion

    form.active_version = FormVersion.objects.create(form=form, version=1, schema={"fields": []})
    form.state = "open"
    form.save()
    assert publish(staff_client, "page", page["id"])["warnings"] == []


@requires("stapel_forms")
def test_an_edit_that_adds_an_unknown_form_is_refused(staff_client):
    page = make_page(staff_client, "about")
    resp = patch(staff_client, "page", page, blocks=[_form_block("missing")])
    assert resp.status_code == 400 and err(resp) == "error.400.cms_form_unknown"
    assert staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()["version"] == page["version"]


@requires("stapel_forms")
def test_forms_down_is_shape_only_with_a_warning_never_a_500(staff_client, monkeypatch):
    import stapel_forms.functions as forms_functions
    from stapel_core.comm.registry import function_registry

    def down(payload):
        raise RuntimeError("database is gone")

    monkeypatch.setitem(function_registry._providers, "forms.form.exists", down)
    assert forms_functions is not None
    resp = _create(staff_client, [_form_block("anything")])
    assert resp.status_code == 201
    assert resp.json()["warnings"] == [{"code": "form_unverified", "field": "blocks.0.data.form_id",
                                        "params": {"form_id": "anything"}}]
    published = transition(staff_client, "page", resp.json()["id"], "published")
    assert published.status_code == 200 and published.json()["warnings"][0]["code"] == "form_unverified"


def test_forms_not_installed_is_shape_only_with_a_warning(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "FORM_EXISTS_FUNCTION": "nobody.forms.exists"}
    resp = _create(staff_client, [_form_block("anything")])
    assert resp.status_code == 201 and resp.json()["warnings"][0]["code"] == "form_unverified"
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "FORM_EXISTS_FUNCTION": ""}
    page = make_page(staff_client, "other", blocks=[_form_block("anything")])
    assert page["warnings"] == []


def test_reads_carry_no_warnings(staff_client, settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "FORM_EXISTS_FUNCTION": "nobody.forms.exists"}
    page = _create(staff_client, [_form_block("anything")]).json()
    assert staff_client.get(f"{V1}/staff/pages/{page['id']}/").json()["warnings"] == []
