"""Shared builders for the cms suite (through the staff API, the client's path)."""
from __future__ import annotations

import datetime as dt

from django.utils import timezone

V1 = "/cms/api/v1"


def doc(*paragraphs):
    return {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": p}]} for p in paragraphs]}


def rich(text="Hello world", bid="b1"):
    return {"type": "rich_text", "id": bid, "data": {"doc": doc(text)}}


def make_page(client, slug="about", *, parent=None, title=None, locale="en", site="", blocks=None, **extra):
    body = {"site": site, "locale": locale, "slug": slug, "parent": parent, "title": title or slug.title() or "Home",
            "blocks": blocks if blocks is not None else [rich(f"{slug} text")], **extra}
    resp = client.post(f"{V1}/staff/pages/", body, format="json")
    assert resp.status_code == 201, resp.content
    return resp.json()


def make_post(client, slug="hello", *, title=None, locale="en", site="", tags=None, blocks=None, **extra):
    body = {"site": site, "locale": locale, "slug": slug, "title": title or slug.title(),
            "excerpt": f"About {slug}", "blocks": blocks if blocks is not None else [rich(f"{slug} body")],
            **({"tags": tags} if tags is not None else {}), **extra}
    resp = client.post(f"{V1}/staff/posts/", body, format="json")
    assert resp.status_code == 201, resp.content
    return resp.json()


def transition(client, kind, obj_id, to, publish_at=None):
    body = {"to": to}
    if publish_at is not None:
        body["publish_at"] = publish_at.isoformat()
    return client.post(f"{V1}/staff/{kind}s/{obj_id}/transition/", body, format="json")


def publish(client, kind, obj_id):
    resp = transition(client, kind, obj_id, "published")
    assert resp.status_code == 200, resp.content
    return resp.json()


def patch(client, kind, obj, **fields):
    return client.patch(f"{V1}/staff/{kind}s/{obj['id']}/", {"version": obj["version"], **fields}, format="json")


def resolve(client, path, **params):
    return client.get(f"{V1}/public/resolve/", {"path": path, **params})


def in_future(minutes=30):
    return timezone.now() + dt.timedelta(minutes=minutes)


def err(resp) -> str:
    """The error key of a refusal (the fleet envelope)."""
    return resp.json()["localizable_error"]
