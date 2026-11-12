"""Public-read cache: one generation token per site, replaced on every publish.

Every cached body's key carries the site's current token, so replacing the
token invalidates the whole site at once. Entries
also expire after ``CACHE_TTL_SECONDS``, which bounds staleness when the
cache is per-process.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from django.db import transaction


def _cache():
    from django.core.cache import caches

    from ..conf import cms_settings

    return caches[cms_settings.CACHE_ALIAS or "default"]


def _gen_key(site: str) -> str:
    return f"cms:gen:{site or '-'}"


def generation(site: str) -> str:
    cache = _cache()
    token = cache.get(_gen_key(site))
    if token is None:
        token = uuid.uuid4().hex
        cache.add(_gen_key(site), token, timeout=None)
        token = cache.get(_gen_key(site)) or token
    return token


def bump(site: str) -> None:
    _cache().set(_gen_key(site), uuid.uuid4().hex, timeout=None)


def bump_after_commit(site: str) -> None:
    """Replace the token now and again after commit.

    The first replacement makes the writer's own later reads fresh; the second
    discards anything a concurrent reader cached from the pre-commit state
    under the intermediate token.
    """
    bump(site)
    transaction.on_commit(lambda: bump(site))


def body_key(site: str, name: str, params: dict) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:32]
    return f"cms:body:{generation(site)}:{site or '-'}:{name}:{digest}"


def get(key: str):
    return _cache().get(key)


def put(key: str, value) -> None:
    from ..conf import cms_settings

    _cache().set(key, value, timeout=int(cms_settings.CACHE_TTL_SECONDS))


def etag_of(body) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    return '"' + hashlib.sha256(raw).hexdigest()[:40] + '"'


__all__ = ["body_key", "bump", "bump_after_commit", "etag_of", "generation", "get", "put"]
