"""The public read side: what an anonymous visitor sees, by site, locale and path.

Everything here reads published snapshots (``serving_revision``), never the
working copy — except :func:`preview`, which a signed token unlocks.
"""
from __future__ import annotations

from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone

from ..errors import ERR_404_NOT_FOUND
from ..models import Kind, Menu, Page, Post, Redirect, Tag
from . import CmsError, paths
from .content import public_path, serving_revision, snapshot


def live_q(now=None) -> Q:
    now = now or timezone.now()
    return Q(live_revision__isnull=False) | Q(scheduled_revision__isnull=False, publish_at__lte=now)


def locale_chain(locale: str | None) -> list[str]:
    from ..conf import cms_settings

    default = str(cms_settings.DEFAULT_LOCALE)
    requested = str(locale or default).strip().lower()
    fallbacks = (cms_settings.LOCALE_FALLBACKS or {}).get(requested, [])
    chain = [requested, *fallbacks, default]
    return list(dict.fromkeys(chain))


def _seo(snap: dict) -> dict:
    return {
        "title": snap.get("seo_title") or snap.get("title") or "",
        "description": snap.get("seo_description") or "",
        "canonical_url": snap.get("canonical_url") or None,
        "og_image": snap.get("og_image") or None,
        "noindex": bool(snap.get("noindex")),
    }


def _alternates(model, obj) -> list[dict]:
    rows = (model.objects.filter(site=obj.site, translation_group=obj.translation_group)
            .filter(live_q()).only("locale", "path" if model is Page else "slug").order_by("locale"))
    return [{"locale": row.locale, "path": public_path(row)} for row in rows]


def _breadcrumbs(page: Page) -> list[dict]:
    crumbs = []
    ancestor = page.parent
    while ancestor is not None:
        revision = serving_revision(ancestor)
        if revision is not None:
            crumbs.append({"title": (revision.snapshot or {}).get("title", ""), "path": ancestor.path})
        ancestor = ancestor.parent
    return list(reversed(crumbs))


def page_view(page: Page, snap: dict, *, preview: bool = False) -> dict:
    return {
        "id": page.pk,
        "locale": page.locale,
        "path": page.path,
        "template": snap.get("template") or "default",
        "title": snap.get("title", ""),
        "blocks": snap.get("blocks") or [],
        "seo": {**_seo(snap), "noindex": True} if preview else _seo(snap),
        "published_at": page.published_at,
        "updated_at": page.last_published_at or page.publish_at or page.updated_at,
        "alternates": [] if preview else _alternates(Page, page),
        "breadcrumbs": _breadcrumbs(page),
    }


def _tags(post: Post) -> list[dict]:
    return [{"slug": t.slug, "name": t.name} for t in post.tags.all().order_by("name")]


def post_summary(post: Post, snap: dict) -> dict:
    return {
        "id": post.pk,
        "locale": post.locale,
        "slug": post.slug,
        "path": paths.post_path(post.slug),
        "title": snap.get("title", ""),
        "excerpt": snap.get("excerpt", ""),
        "cover": snap.get("cover") or None,
        "tags": _tags(post),
        "author_id": post.author_id or None,
        "reading_time_minutes": int(snap.get("reading_time_minutes") or 1),
        "published_at": post.published_at,
    }


def post_view(post: Post, snap: dict, *, preview: bool = False) -> dict:
    return {
        **post_summary(post, snap),
        "blocks": snap.get("blocks") or [],
        "seo": {**_seo(snap), "noindex": True} if preview else _seo(snap),
        "updated_at": post.last_published_at or post.publish_at or post.updated_at,
        "alternates": [] if preview else _alternates(Post, post),
    }


def _live(model, now=None):
    return (model.objects.filter(live_q(now))
            .select_related("live_revision", "scheduled_revision"))


def _post_slug(path: str) -> str | None:
    from ..conf import cms_settings

    if not cms_settings.BLOG_ENABLED:
        return None
    prefix = paths.blog_prefix().rstrip("/") + "/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix):]
    return rest if rest and "/" not in rest else None


def resolve(site: str, locale: str | None, raw_path: str) -> dict:
    """``{kind, locale, page|post|redirect}`` for a path, or a 404 refusal."""
    path = paths.normalize_path(raw_path)
    now = timezone.now()
    slug = _post_slug(path)
    for loc in locale_chain(locale):
        page = _live(Page, now).filter(site=site, locale=loc, path=path).select_related("parent").first()
        if page is not None:
            snap = serving_revision(page, now).snapshot or {}
            return {"kind": Kind.PAGE, "locale": loc, "page": page_view(page, snap), "post": None,
                    "redirect": None, "last_modified": page.last_published_at or page.publish_at}
        if slug is not None:
            post = _live(Post, now).filter(site=site, locale=loc, slug=slug).first()
            if post is not None:
                snap = serving_revision(post, now).snapshot or {}
                return {"kind": Kind.POST, "locale": loc, "page": None, "post": post_view(post, snap),
                        "redirect": None, "last_modified": post.last_published_at or post.publish_at}
        redirect = Redirect.objects.filter(site=site, locale=loc, old_path=path).first()
        if redirect is not None:
            return {"kind": "redirect", "locale": loc, "page": None, "post": None,
                    "redirect": {"to": redirect.new_path, "permanent": redirect.permanent},
                    "last_modified": redirect.created_at}
    raise CmsError(404, ERR_404_NOT_FOUND)


def preview(kind: str, obj_id: int) -> dict:
    model = Page if kind == Kind.PAGE else Post
    obj = model.objects.filter(pk=obj_id).first()
    if obj is None:
        from ..errors import ERR_404_PREVIEW_INVALID

        raise CmsError(404, ERR_404_PREVIEW_INVALID)
    snap = snapshot(obj)
    if kind == Kind.PAGE:
        return {"kind": kind, "locale": obj.locale, "page": page_view(obj, snap, preview=True), "post": None,
                "redirect": None, "last_modified": obj.updated_at}
    return {"kind": kind, "locale": obj.locale, "page": None, "post": post_view(obj, snap, preview=True),
            "redirect": None, "last_modified": obj.updated_at}


def post_detail(site: str, locale: str | None, slug: str) -> dict:
    now = timezone.now()
    for loc in locale_chain(locale):
        post = _live(Post, now).filter(site=site, locale=loc, slug=str(slug).lower()).first()
        if post is not None:
            return post_view(post, serving_revision(post, now).snapshot or {})
    raise CmsError(404, ERR_404_NOT_FOUND)


def _default_locale(locale):
    from ..conf import cms_settings

    return str(locale or cms_settings.DEFAULT_LOCALE).strip().lower()


def posts_queryset(site: str, locale: str | None, *, tag: str | None = None, year=None, month=None):
    qs = _live(Post).filter(site=site, locale=_default_locale(locale), published_at__isnull=False)
    if tag:
        qs = qs.filter(tags__slug=str(tag).lower())
    if year:
        qs = qs.filter(published_at__year=int(year))
        if month:
            qs = qs.filter(published_at__month=int(month))
    return qs.prefetch_related("tags")


def post_summaries(posts) -> list[dict]:
    now = timezone.now()
    return [post_summary(p, serving_revision(p, now).snapshot or {}) for p in posts]


def archive(site: str, locale: str | None) -> list[dict]:
    rows = (posts_queryset(site, locale).order_by()
            .annotate(y=ExtractYear("published_at"), m=ExtractMonth("published_at"))
            .values("y", "m").annotate(count=Count("id", distinct=True)).order_by("-y", "-m"))
    return [{"year": r["y"], "month": r["m"], "count": r["count"]} for r in rows]


def tags(site: str, locale: str | None) -> list[dict]:
    live_ids = list(posts_queryset(site, locale).values_list("pk", flat=True))
    rows = (Tag.objects.filter(site=site, locale=_default_locale(locale))
            .annotate(count=Count("posts", filter=Q(posts__in=live_ids), distinct=True))
            .filter(count__gt=0).order_by("name"))
    return [{"slug": t.slug, "name": t.name, "count": t.count} for t in rows]


def menu(site: str, locale: str | None, key: str) -> dict:
    from .menus import public_tree

    for loc in locale_chain(locale):
        row = Menu.objects.filter(site=site, locale=loc, key=str(key).lower()).first()
        if row is not None:
            return {"key": row.key, "title": row.title, "locale": loc, "items": public_tree(row),
                    "last_modified": row.updated_at}
    raise CmsError(404, ERR_404_NOT_FOUND)


def _sitemap_alternates(model, site: str, objs: list, now) -> dict:
    """``{translation_group: [{locale, path}]}`` of indexable live variants, for groups of two or more."""
    groups = {obj.translation_group for obj in objs}
    if not groups:
        return {}
    by_group: dict = {}
    for row in _live(model, now).filter(site=site, translation_group__in=groups).order_by("locale"):
        if (serving_revision(row, now).snapshot or {}).get("noindex"):
            continue
        by_group.setdefault(row.translation_group, []).append({"locale": row.locale, "path": public_path(row)})
    return {group: alts for group, alts in by_group.items() if len(alts) > 1}


def sitemap_entries(site: str, locale: str | None, cursor: str | None, limit: int) -> dict:
    """One batch of stapel-core's sitemap provider contract for ``site``.

    Published, indexable pages then posts (posts only with the blog on),
    keyset-paged by the cursor ``"<kind>:<last id>"``; ``cursor: None`` in the
    answer means done. Each entry is ``{path, locale, lastmod, kind}`` plus
    ``alternates``: every indexable live variant of its translation group,
    itself included, when the group has two or more; else ``[]``.
    """
    from ..conf import cms_settings

    kinds = [(Kind.PAGE, Page)] + ([(Kind.POST, Post)] if cms_settings.BLOG_ENABLED else [])
    kind, _, last = str(cursor or "").partition(":")
    last_id = int(last) if last.isdigit() else 0
    if kind not in {name for name, _ in kinds}:
        kind, last_id = Kind.PAGE, 0
    out: list[dict] = []
    now = timezone.now()
    started = False
    for current, model in kinds:
        started = started or current == kind
        if not started:
            continue
        qs = _live(model, now).filter(site=site).order_by("id")
        if locale:
            qs = qs.filter(locale=locale)
        if current == kind:
            qs = qs.filter(id__gt=last_id)
        picked, full = [], False
        for obj in qs.iterator(chunk_size=200):
            if (serving_revision(obj, now).snapshot or {}).get("noindex"):
                continue
            picked.append(obj)
            if len(out) + len(picked) >= limit:
                full = True
                break
        alternates = _sitemap_alternates(model, site, picked, now)
        for obj in picked:
            entry = {
                "path": public_path(obj), "locale": obj.locale, "kind": current,
                "lastmod": (obj.last_published_at or obj.publish_at or obj.updated_at).isoformat(),
                "alternates": alternates.get(obj.translation_group, []),
            }
            out.append(entry)
        if full:
            return {"entries": out, "cursor": f"{current}:{picked[-1].pk}"}
    return {"entries": out, "cursor": None}


__all__ = [
    "archive", "live_q", "locale_chain", "menu", "page_view", "post_detail", "post_summaries", "post_view",
    "posts_queryset", "preview", "resolve", "sitemap_entries", "tags",
]
