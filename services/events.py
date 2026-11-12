"""Facts stapel-cms emits (always through the caller's ``mutate_and_emit``).

No personal data beyond the staff ``author_id`` of a post rides the bus.
"""
from __future__ import annotations

PAGE_PUBLISHED = "cms.page.published"
PAGE_UNPUBLISHED = "cms.page.unpublished"
POST_PUBLISHED = "cms.post.published"
POST_UNPUBLISHED = "cms.post.unpublished"
MENU_CHANGED = "cms.menu.changed"
REDIRECT_CREATED = "cms.redirect.created"

EMITS = (PAGE_PUBLISHED, PAGE_UNPUBLISHED, POST_PUBLISHED, POST_UNPUBLISHED, MENU_CHANGED, REDIRECT_CREATED)


def emit_published(emit, obj, kind: str, path: str, revision, first: bool) -> None:
    payload = {
        f"{kind}_id": str(obj.pk),
        "site": obj.site,
        "locale": obj.locale,
        "path": path,
        "revision": revision.number,
        "published_at": obj.published_at.isoformat() if obj.published_at else None,
        "first": first,
    }
    if kind == "page":
        payload["translation_group"] = str(obj.translation_group)
        emit(PAGE_PUBLISHED, payload, key=str(obj.pk))
    else:
        payload["tags"] = sorted(obj.tags.values_list("slug", flat=True))
        payload["author_id"] = obj.author_id or None
        emit(POST_PUBLISHED, payload, key=str(obj.pk))


def emit_unpublished(emit, obj, kind: str, path: str) -> None:
    name = PAGE_UNPUBLISHED if kind == "page" else POST_UNPUBLISHED
    emit(name, {f"{kind}_id": str(obj.pk), "site": obj.site, "locale": obj.locale, "path": path}, key=str(obj.pk))


def emit_menu_changed(emit, menu) -> None:
    emit(MENU_CHANGED, {"menu_id": str(menu.pk), "site": menu.site, "locale": menu.locale, "key": menu.key},
         key=str(menu.pk))


def emit_redirect_created(emit, redirect) -> None:
    emit(REDIRECT_CREATED, {
        "site": redirect.site,
        "locale": redirect.locale,
        "old_path": redirect.old_path,
        "new_path": redirect.new_path,
        "source": redirect.source,
    }, key=f"{redirect.site}:{redirect.locale}:{redirect.old_path}")


__all__ = [
    "EMITS", "MENU_CHANGED", "PAGE_PUBLISHED", "PAGE_UNPUBLISHED", "POST_PUBLISHED", "POST_UNPUBLISHED",
    "REDIRECT_CREATED", "emit_menu_changed", "emit_published", "emit_redirect_created", "emit_unpublished",
]
