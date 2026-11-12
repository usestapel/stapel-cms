"""RSS 2.0 / Atom feed of a site's latest published posts (Django's feedgenerator)."""
from __future__ import annotations

from django.utils import feedgenerator

from .. import sitekeys
from . import public

FORMATS = {
    "rss": (feedgenerator.Rss201rev2Feed, "application/rss+xml; charset=utf-8"),
    "atom": (feedgenerator.Atom1Feed, "application/atom+xml; charset=utf-8"),
}


def render(site: str, locale: str | None, fmt: str = "rss", origin: str | None = None) -> tuple[str, str]:
    """``(content_type, body)`` of the feed."""
    from ..conf import cms_settings

    feed_class, content_type = FORMATS.get(fmt, FORMATS["rss"])
    base = (origin if origin is not None else sitekeys.origin(site)).rstrip("/")
    blog = public.paths.blog_prefix()
    posts = list(public.posts_queryset(site, locale).order_by("-published_at", "-id")[: int(cms_settings.FEED_ITEMS)])
    items = public.post_summaries(posts)
    feed = feed_class(
        title=site or "Blog",
        link=f"{base}{blog}",
        description="",
        language=public.locale_chain(locale)[0],
        feed_url=None,
    )
    for item in items:
        feed.add_item(
            title=item["title"],
            link=f"{base}{item['path']}",
            description=item["excerpt"],
            unique_id=f"{base}{item['path']}",
            pubdate=item["published_at"],
            categories=[t["name"] for t in item["tags"]],
        )
    return content_type, feed.writeString("utf-8")


__all__ = ["FORMATS", "render"]
