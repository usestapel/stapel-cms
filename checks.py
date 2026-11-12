"""Django system checks for stapel-cms.

- E001  a ``BLOCK_TYPES`` entry is not a pydantic model (or a bad type name).
- E002  ``STAFF_AUTHZ`` is not one of ``staff`` / ``model_perms``.
- E003  locales: ``LOCALES`` empty, ``DEFAULT_LOCALE`` not in it, or a
        ``LOCALE_FALLBACKS`` entry naming a locale that is not enabled.
- E004  ``PAGE_TEMPLATES`` is empty (no page could be created).
- E005  an ``EMBED_HOSTS`` entry is not a bare host name.
- W001  ``MACHINE_TRANSLATE`` names a Function not reachable here.
- W002  the cache is per-process (locmem): a publish invalidates only the
        process that served it until ``CACHE_TTL_SECONDS`` passes.
- W003  more than one locale and cms feeds stapel-core's sitemap, but
        ``STAPEL_SITEMAP["URL_TEMPLATE"]`` has no ``{locale}``: variant paths
        carry no locale, so every variant of a page maps to one URL.
"""
import re

from django.core import checks

_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$")


@checks.register(checks.Tags.compatibility)
def check_block_types(app_configs, **kwargs):
    from .blocks import BLOCK_TYPE_RE, block_model, get_block_types

    findings = []
    for name in sorted(get_block_types()):
        if not BLOCK_TYPE_RE.match(name):
            findings.append(checks.Error(
                f"STAPEL_CMS['BLOCK_TYPES'] name {name!r} must match {BLOCK_TYPE_RE.pattern}.",
                id="stapel_cms.E001"))
            continue
        try:
            block_model(name)
        except Exception as exc:  # ImportError, TypeError — all mean the same to a deployer
            findings.append(checks.Error(
                f"STAPEL_CMS['BLOCK_TYPES'][{name!r}] does not resolve to a pydantic model: {exc}",
                hint="Name a pydantic.BaseModel subclass (stapel_cms.blocks.BlockData), or None to remove.",
                id="stapel_cms.E001"))
    return findings


@checks.register(checks.Tags.compatibility)
def check_settings(app_configs, **kwargs):
    from .conf import STAFF_AUTHZ_CHOICES, cms_settings

    findings = []
    if cms_settings.STAFF_AUTHZ not in STAFF_AUTHZ_CHOICES:
        findings.append(checks.Error(
            f"STAPEL_CMS['STAFF_AUTHZ'] is {cms_settings.STAFF_AUTHZ!r}; expected one of {STAFF_AUTHZ_CHOICES}.",
            id="stapel_cms.E002"))
    locales = [str(x) for x in (cms_settings.LOCALES or [])]
    if not locales or cms_settings.DEFAULT_LOCALE not in locales:
        findings.append(checks.Error(
            "STAPEL_CMS['LOCALES'] must be non-empty and contain DEFAULT_LOCALE "
            f"({cms_settings.DEFAULT_LOCALE!r}).", id="stapel_cms.E003"))
    for key, chain in (cms_settings.LOCALE_FALLBACKS or {}).items():
        unknown = [loc for loc in [key, *(chain or [])] if loc not in locales]
        if unknown:
            findings.append(checks.Error(
                f"STAPEL_CMS['LOCALE_FALLBACKS'][{key!r}] names locales not in LOCALES: {unknown}.",
                id="stapel_cms.E003"))
    if not list(cms_settings.PAGE_TEMPLATES or []):
        findings.append(checks.Error("STAPEL_CMS['PAGE_TEMPLATES'] is empty: no page can be created.",
                                     id="stapel_cms.E004"))
    bad_hosts = [h for h in (cms_settings.EMBED_HOSTS or []) if not _HOST_RE.match(str(h))]
    if bad_hosts:
        findings.append(checks.Error(
            f"STAPEL_CMS['EMBED_HOSTS'] entries must be bare lowercase host names: {bad_hosts}.",
            hint="Write 'www.youtube.com', not 'https://www.youtube.com/'.", id="stapel_cms.E005"))
    return findings


@checks.register(checks.Tags.compatibility)
def check_integrations(app_configs, **kwargs):
    from django.conf import settings
    from stapel_core.comm import function_unreachable_reason

    from .conf import cms_settings

    findings = []
    translate = str(cms_settings.MACHINE_TRANSLATE or "")
    if translate:
        reason = function_unreachable_reason(translate)
        if reason:
            findings.append(checks.Warning(
                f"STAPEL_CMS['MACHINE_TRANSLATE'] names {translate!r}, not reachable here ({reason}); "
                "variant requests with machine_translate answer 503.", id="stapel_cms.W001"))
    alias = cms_settings.CACHE_ALIAS or "default"
    backend = str((getattr(settings, "CACHES", {}) or {}).get(alias, {}).get("BACKEND", ""))
    if backend.endswith("LocMemCache") and not settings.DEBUG:
        findings.append(checks.Warning(
            f"The cms cache alias {alias!r} is per-process (LocMemCache): a publish invalidates only the "
            f"process that handled it; others serve the old body for up to CACHE_TTL_SECONDS.",
            hint="Point STAPEL_CMS['CACHE_ALIAS'] at a shared cache (redis) in production.",
            id="stapel_cms.W002"))
    findings += _sitemap_findings(cms_settings)
    return findings


def _sitemap_findings(cms_settings) -> list:
    from .services.sitemaps import PROVIDER, aggregator

    locales = list(cms_settings.LOCALES or [])
    module = aggregator()
    if len(locales) < 2 or module is None or PROVIDER not in module.sitemap_providers().values():
        return []
    from stapel_core.django.sitemap.conf import sitemap_settings

    template = str(sitemap_settings.URL_TEMPLATE or "")
    if "{locale}" in template:
        return []
    return [checks.Warning(
        f"STAPEL_CMS['LOCALES'] has {len(locales)} locales but STAPEL_SITEMAP['URL_TEMPLATE'] is {template!r}: "
        "cms variant paths carry no locale, so every language version of a page becomes the same sitemap URL "
        "(duplicates are dropped, hreflang alternates point at one address).",
        hint="If the frontend prefixes locales, set STAPEL_SITEMAP['URL_TEMPLATE'] = '{origin}/{locale}{path}'; "
             "if each locale lives on its own site, silence stapel_cms.W003.",
        id="stapel_cms.W003")]
