"""cdn reference tracking: what content uses is claimed, what it dropped is released."""
import pytest

from stapel_cms.models import Page

from .fakes import FakeFunction
from .helpers import make_page, patch

pytestmark = pytest.mark.django_db


@pytest.fixture
def cdn(settings):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MEDIA_REFS_FUNCTION": "test.refs_sync"}
    fake = FakeFunction("test.refs_sync", {"added": 0, "removed": 0, "errors": []}).install()
    yield fake
    fake.uninstall()


def _hero(media):
    return [{"type": "hero", "id": "h", "data": {"heading": "Hi", "media": media}}]


def test_refs_follow_the_content(staff_client, cdn, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        page = make_page(staff_client, "about", blocks=_hero("page/one"), og_image="page/og")
    assert cdn.calls[-1]["new_hashes"] == ["page/og", "page/one"] and cdn.calls[-1]["entity_type"] == "page"
    assert Page.objects.get(pk=page["id"]).media_refs == ["page/og", "page/one"]
    with django_capture_on_commit_callbacks(execute=True):
        patch(staff_client, "page", page, blocks=_hero("page/two"))
    assert cdn.calls[-1]["old_hashes"] == ["page/og", "page/one"]
    assert cdn.calls[-1]["new_hashes"] == ["page/og", "page/two"]


def test_an_unreachable_cdn_is_retried_on_the_next_save(staff_client, settings,
                                                         django_capture_on_commit_callbacks):
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "MEDIA_REFS_FUNCTION": "nobody.refs_sync"}
    with django_capture_on_commit_callbacks(execute=True):
        page = make_page(staff_client, "about", blocks=_hero("page/one"))
    assert Page.objects.get(pk=page["id"]).media_refs == []
