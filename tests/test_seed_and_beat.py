"""The seed command and the scheduled-publication pass."""
import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from stapel_cms import beat
from stapel_cms.models import Page

from .helpers import in_future, make_page, transition

pytestmark = pytest.mark.django_db


def test_seed_creates_the_usual_drafts_once():
    out = StringIO()
    call_command("cms_seed", stdout=out)
    paths = set(Page.objects.values_list("path", flat=True))
    assert paths == {"/about", "/contacts", "/terms", "/privacy", "/faq"}
    assert set(Page.objects.values_list("status", flat=True)) == {"draft"}
    assert Page.objects.get(path="/faq").blocks[0]["type"] == "faq"
    assert Page.objects.get(path="/terms").template == "legal"
    out = StringIO()
    call_command("cms_seed", stdout=out)
    assert "nothing to create" in out.getvalue() and Page.objects.count() == 5


def test_seed_in_another_locale():
    call_command("cms_seed", locale="de", stdout=StringIO())
    assert set(Page.objects.values_list("locale", flat=True)) == {"de"}


def test_beat_schedule_and_pass(staff_client):
    schedule = beat.get_cms_beat_schedule()
    assert schedule[beat.PUBLISH_DUE_BEAT_KEY]["task"] == beat.PUBLISH_DUE_TASK_NAME
    assert schedule[beat.PUBLISH_DUE_BEAT_KEY]["schedule"] == 60.0
    page = make_page(staff_client, "soon")
    transition(staff_client, "page", page["id"], "scheduled", in_future())
    assert beat.publish_due() == 0
    Page.objects.filter(pk=page["id"]).update(publish_at=timezone.now() - dt.timedelta(seconds=5))
    out = StringIO()
    call_command("cms_publish_due", stdout=out)
    assert "published 1" in out.getvalue()
    assert Page.objects.get(pk=page["id"]).status == "published"
