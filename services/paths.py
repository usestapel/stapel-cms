"""Slugs, page paths, subtree moves and the redirects they leave behind."""
from __future__ import annotations

import re

from django.db import IntegrityError

from ..errors import (
    ERR_400_PARENT_INVALID,
    ERR_400_PATH_RESERVED,
    ERR_400_REDIRECT_INVALID,
    ERR_400_SLUG_INVALID,
    ERR_400_TREE_TOO_DEEP,
    ERR_409_PATH_TAKEN,
)
from ..models import PATH_MAX_LENGTH, SLUG_MAX_LENGTH, Page, Redirect, RedirectSource
from ..safety import is_safe_url
from . import CmsError, events

SLUG_RE = re.compile(r"^[^\W_]+(?:-[^\W_]+)*$", re.UNICODE)


def clean_slug(value, *, allow_empty: bool = False) -> str:
    slug = str(value or "").strip().lower()
    if slug == "" and allow_empty:
        return ""
    if not slug or len(slug) > SLUG_MAX_LENGTH or not SLUG_RE.match(slug):
        raise CmsError(400, ERR_400_SLUG_INVALID)
    return slug


def normalize_path(raw) -> str:
    """``"about//team/"`` -> ``"/about/team"``; ``""`` -> ``"/"``."""
    parts = [p for p in str(raw or "").strip().split("/") if p]
    path = "/" + "/".join(p.lower() for p in parts)
    return path[:PATH_MAX_LENGTH + 1]


def blog_prefix() -> str:
    from ..conf import cms_settings

    return normalize_path(cms_settings.BLOG_PATH_PREFIX or "/blog")


def post_path(slug: str) -> str:
    prefix = blog_prefix()
    return f"{prefix.rstrip('/')}/{slug}"


def page_path(parent, slug: str) -> str:
    if parent is None:
        return "/" + slug if slug else "/"
    return f"{parent.path.rstrip('/')}/{slug}"


def check_page_placement(page: Page, parent, slug: str) -> str:
    """Validate a page's parent and slug; return its new path."""
    from ..conf import cms_settings

    if slug == "" and parent is not None:
        raise CmsError(400, ERR_400_SLUG_INVALID)
    if parent is not None:
        if parent.site != page.site or parent.locale != page.locale:
            raise CmsError(400, ERR_400_PARENT_INVALID)
        ancestor, depth = parent, 1
        while ancestor is not None:
            if page.pk is not None and ancestor.pk == page.pk:
                raise CmsError(400, ERR_400_PARENT_INVALID)
            if ancestor.slug:  # the root page "/" adds no path segment
                depth += 1
            ancestor = ancestor.parent
    else:
        depth = 1
    max_depth = int(cms_settings.PAGE_MAX_DEPTH)
    if depth > max_depth:
        raise CmsError(400, ERR_400_TREE_TOO_DEEP, {"max_depth": max_depth})
    path = page_path(parent, slug)
    if len(path) > PATH_MAX_LENGTH:
        raise CmsError(400, ERR_400_TREE_TOO_DEEP, {"max_depth": max_depth})
    if cms_settings.BLOG_ENABLED and path.startswith(blog_prefix().rstrip("/") + "/"):
        raise CmsError(400, ERR_400_PATH_RESERVED)
    return path


def ensure_free(site: str, locale: str, path: str, exclude_pk=None) -> None:
    qs = Page.objects.filter(site=site, locale=locale, path=path)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise CmsError(409, ERR_409_PATH_TAKEN)


def move_subtree(page: Page, old_path: str, new_path: str, emit) -> int:
    """Re-path ``page``'s descendants after its own path changed; write redirects.

    ``page`` itself is saved by the caller. Returns the number of descendants moved.
    """
    if old_path == new_path:
        return 0
    prefix = old_path.rstrip("/") + "/"
    descendants = list(
        Page.objects.select_for_update()
        .filter(site=page.site, locale=page.locale, path__startswith=prefix)
        .exclude(pk=page.pk)
        .order_by("path")
    )
    moves = [(d, new_path.rstrip("/") + "/" + d.path[len(prefix):]) for d in descendants]
    for _row, target in moves:
        if len(target) > PATH_MAX_LENGTH:
            raise CmsError(400, ERR_400_TREE_TOO_DEEP, {"max_depth": 0})
    moved_ids = [d.pk for d, _ in moves] + [page.pk]
    clash = Page.objects.filter(site=page.site, locale=page.locale, path__in=[t for _, t in moves])
    if clash.exclude(pk__in=moved_ids).exists():
        raise CmsError(409, ERR_409_PATH_TAKEN)
    for row, target in moves:
        old = row.path
        Page.objects.filter(pk=row.pk).update(path=target)
        if row.published_at is not None:
            add_redirect(page.site, page.locale, old, target, RedirectSource.AUTO, emit)
    return len(moves)


def add_redirect(site, locale, old_path, new_path, source, emit, created_by_id: str = ""):
    """Write ``old -> new``, collapsing chains; a no-op for a self-loop."""
    if old_path == new_path:
        return None
    # A path that is a real page again beats any redirect away from it.
    Redirect.objects.filter(site=site, locale=locale, old_path=new_path).delete()
    # A -> old becomes A -> new (chains collapse); a resulting loop is dropped.
    Redirect.objects.filter(site=site, locale=locale, new_path=old_path).update(new_path=new_path)
    Redirect.objects.filter(site=site, locale=locale, old_path=new_path, new_path=new_path).delete()
    try:
        redirect, _ = Redirect.objects.update_or_create(
            site=site, locale=locale, old_path=old_path,
            defaults={"new_path": new_path, "permanent": True, "source": source, "created_by_id": created_by_id},
        )
    except IntegrityError:  # pragma: no cover - the unique row raced in; the update path wins next time
        return None
    events.emit_redirect_created(emit, redirect)  # emit-check: ok — emit is the caller's mutate_and_emit() emitter
    return redirect


def clean_redirect_target(value: str) -> str:
    target = str(value or "").strip()
    if target.lower().startswith("https://"):
        if not is_safe_url(target):
            raise CmsError(400, ERR_400_REDIRECT_INVALID)
        return target
    if not target.startswith("/") or target.startswith("//"):
        raise CmsError(400, ERR_400_REDIRECT_INVALID)
    return normalize_path(target)


def drop_redirect_at(site: str, locale: str, path: str) -> None:
    """A page (or post) now lives at ``path``: no redirect may shadow it."""
    Redirect.objects.filter(site=site, locale=locale, old_path=path).delete()


__all__ = [
    "add_redirect", "blog_prefix", "check_page_placement", "clean_redirect_target", "clean_slug",
    "drop_redirect_at", "ensure_free", "move_subtree", "normalize_path", "page_path", "post_path",
]
