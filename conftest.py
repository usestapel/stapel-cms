def pytest_configure(config):
    from django.conf import settings

    if not settings.configured:
        from stapel_cms._codegen_settings import settings_kwargs

        settings.configure(**settings_kwargs())
        import django

        django.setup()

        from stapel_core.comm.schemas import autoload_schemas

        autoload_schemas()


import pytest  # noqa: E402
from stapel_core.testing import emit_outside_atomic_gate  # noqa: E402,F401


def _make_user(username, **extra):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x", **extra
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def staff(db):
    return _make_user("editor", is_staff=True)


@pytest.fixture
def other_staff(db):
    return _make_user("editor2", is_staff=True)


@pytest.fixture
def user(db):
    return _make_user("alice")


@pytest.fixture
def guest(db):
    return _make_user("guest-1", is_anonymous=True)


@pytest.fixture
def client_for():
    def _client(u):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return _client


@pytest.fixture
def staff_client(client_for, staff):
    return client_for(staff)


@pytest.fixture(autouse=True)
def _reset_state():
    from django.core.cache import cache

    from stapel_cms.blocks import reset_block_types

    reset_block_types()
    cache.clear()
    yield
    reset_block_types()
    cache.clear()


@pytest.fixture
def captured_events():
    """Collect cms emits delivered in-process."""
    from stapel_core.comm import action_registry, subscribe_action

    from stapel_cms.services.events import EMITS

    collected = []

    def _handler(event):
        collected.append(event)

    for name in EMITS:
        subscribe_action(name, _handler)
    try:
        yield collected
    finally:
        for name in EMITS:
            handlers = action_registry._subscribers.get(name, [])
            if _handler in handlers:
                handlers.remove(_handler)
