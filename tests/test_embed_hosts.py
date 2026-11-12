"""EMBED_HOSTS reaches clients: the resolve answer's meta and the capabilities axis."""
import json
from pathlib import Path

import pytest

from stapel_cms.conf import DEFAULT_EMBED_HOSTS

from .helpers import make_page, publish, resolve

pytestmark = pytest.mark.django_db


def test_resolve_publishes_the_server_allowlist(client, staff_client, settings):
    publish(staff_client, "page", make_page(staff_client, "about")["id"])
    assert resolve(client, "/about").json()["meta"] == {"embed_hosts": DEFAULT_EMBED_HOSTS}
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, "EMBED_HOSTS": ["player.example.com"]}
    from django.core.cache import cache

    cache.clear()
    assert resolve(client, "/about").json()["meta"]["embed_hosts"] == ["player.example.com"]


def test_embed_hosts_is_a_capabilities_axis():
    caps = json.loads((Path(__file__).resolve().parent.parent / "docs" / "capabilities.json").read_text())
    entry = next(a for a in caps["axes"] if a["key"] == "EMBED_HOSTS")
    assert entry["default"] == DEFAULT_EMBED_HOSTS
