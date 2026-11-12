"""cms as a provider of stapel-core's site-scoped sitemap aggregator.

``cms.sitemap_entries`` answers core's provider contract
(``stapel_core.django.sitemap.build``); this module registers it from
``AppConfig.ready()`` and drops a site's cached sitemap set after any commit
that changes what the public sees (publish, unpublish, a move). On a core
without the aggregator both are no-ops: the Function stays callable by name.
"""
from __future__ import annotations

import importlib
import logging

from django.db import transaction

logger = logging.getLogger(__name__)

PROVIDER = "cms.sitemap_entries"


def aggregator():
    """core's sitemap module, or ``None`` on a core that predates it."""
    try:
        sitemap = importlib.import_module("stapel_core.django.sitemap")
    except ImportError:
        return None
    return sitemap if hasattr(sitemap, "register_sitemap_provider") else None


def register_provider() -> bool:
    module = aggregator()
    if module is None:
        return False
    module.register_sitemap_provider(PROVIDER, name="cms")
    return True


def invalidate(site: str) -> None:
    module = aggregator()
    if module is None:
        return
    try:
        module.invalidate_sitemaps(site)
    except Exception:
        logger.warning("cms: could not drop the cached sitemaps of site %r", site, exc_info=True)


def invalidate_after_commit(site: str) -> None:
    """Drop the set now and again after commit (a crawl between the two caches the old state)."""
    invalidate(site)
    transaction.on_commit(lambda: invalidate(site))


__all__ = ["PROVIDER", "aggregator", "invalidate", "invalidate_after_commit", "register_provider"]
