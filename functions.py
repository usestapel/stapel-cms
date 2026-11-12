"""comm Functions provided by stapel-cms (schemas in ``schemas/functions/``).

- ``cms.sitemap_entries`` — published, indexable pages and posts of a site:
  a provider of stapel-core's sitemap aggregator (registered from
  ``AppConfig.ready()``; contract in ``stapel_core.django.sitemap.build``).
- ``cms.resolve_path`` — what lives at a public path (for search, links).
- ``cms.feed`` — the RSS/Atom feed body of a site's blog.

The Functions cms *calls* (``cdn.refs_sync``, the machine-translation
Function) are named in settings and reached by name only.
"""
from stapel_core.comm import function

SITEMAP_DEFAULT_LIMIT = 500
SITEMAP_MAX_LIMIT = 5000


@function("cms.sitemap_entries")
def sitemap_entries(payload):
    from .services.public import sitemap_entries as entries

    limit = max(1, min(int(payload.get("limit") or SITEMAP_DEFAULT_LIMIT), SITEMAP_MAX_LIMIT))
    locale = str(payload.get("locale") or "").strip().lower() or None
    return entries(str(payload.get("site") or ""), locale, payload.get("cursor"), limit)


@function("cms.resolve_path")
def resolve_path(payload):
    from .services import CmsError
    from .services.public import resolve

    try:
        result = resolve(str(payload.get("site") or ""), payload.get("locale"), str(payload["path"]))
    except CmsError:
        return {"found": False, "kind": None, "id": None, "locale": None, "title": None, "path": None}
    body = result.get("page") or result.get("post")
    if body is None:
        return {"found": True, "kind": "redirect", "id": None, "locale": result["locale"], "title": None,
                "path": result["redirect"]["to"]}
    return {"found": True, "kind": result["kind"], "id": body["id"], "locale": result["locale"],
            "title": body["title"], "path": body["path"]}


@function("cms.feed")
def feed(payload):
    from .services.feed import render

    fmt = payload.get("type") or "rss"
    content_type, body = render(str(payload.get("site") or ""), payload.get("locale"), fmt)
    return {"content_type": content_type, "body": body}
