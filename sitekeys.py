"""Which site a row or a request belongs to — the stapel-core site registry.

A site key is the registry entry's brand key, else its host; ``""`` is the
only key of a single-host deployment (empty registry). The public read takes
the key from the request (``site_for_request``: an unmatched host falls back
to the primary site, as the registry defines); the staff API names it.
"""
from __future__ import annotations


def _registry():
    from stapel_core.django.sites import site_registry

    return site_registry()


def key_of(site) -> str:
    if site is None:
        return ""
    return site.brand.key if site.brand else site.host


def site_keys() -> tuple[str, ...]:
    """Every valid site key; ``("",)`` on a single-host deployment."""
    registry = _registry()
    if not registry:
        return ("",)
    return tuple(key_of(site) for site in registry.sites)


def is_known(key: str) -> bool:
    return key in site_keys()


def for_request(request) -> str:
    from stapel_core.django.sites import site_for_request

    return key_of(site_for_request(request))


def default_key() -> str:
    """The primary site's key (code with no request in hand)."""
    registry = _registry()
    return key_of(registry.primary()) if registry else ""


def origin(key: str) -> str:
    """``https://<host>`` of a site, or ``SITE_ORIGIN`` when there is no registry."""
    from .conf import cms_settings

    registry = _registry()
    for site in registry.sites if registry else ():
        if key_of(site) == key:
            return f"https://{site.host}"
    return str(cms_settings.SITE_ORIGIN or "").rstrip("/")


__all__ = ["default_key", "for_request", "is_known", "key_of", "origin", "site_keys"]
