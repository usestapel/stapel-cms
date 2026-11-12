"""Menus: a tree of items replaced atomically by the staff editor."""
from __future__ import annotations

import re

from django.db import IntegrityError
from stapel_core.comm import mutate_and_emit

from ..errors import ERR_400_MENU_INVALID, ERR_404_NOT_FOUND, ERR_409_SLUG_TAKEN
from ..models import Menu, MenuItem, Page, Post, TargetType
from ..safety import is_safe_url
from . import CmsError, cache, events
from .content import check_scope, public_path, serving_revision

ROUTE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{0,99}$")
KEY_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


def _invalid(detail: str) -> CmsError:
    return CmsError(400, ERR_400_MENU_INVALID, {"detail": detail})


def _limits():
    from ..conf import cms_settings

    return int(cms_settings.MENU_MAX_DEPTH), int(cms_settings.MENU_MAX_ITEMS)


def _plan(menu: Menu, items, depth: int, counter: list) -> list[tuple]:
    """Validate a raw tree; return [(fields, children_plan)]."""
    max_depth, max_items = _limits()
    if depth > max_depth:
        raise _invalid(f"nested deeper than {max_depth}")
    plan = []
    for item in items or []:
        counter[0] += 1
        if counter[0] > max_items:
            raise _invalid(f"more than {max_items} items")
        target = item.get("target_type")
        fields = {"label": item["label"], "target_type": target, "new_tab": bool(item.get("new_tab", False)),
                  "page": None, "post": None, "url": "", "route": "", "route_params": {}}
        if target == TargetType.PAGE:
            fields["page"] = Page.objects.filter(pk=item.get("page"), site=menu.site, locale=menu.locale).first()
            if fields["page"] is None:
                raise _invalid("page target is not a page of this site and locale")
        elif target == TargetType.POST:
            fields["post"] = Post.objects.filter(pk=item.get("post"), site=menu.site, locale=menu.locale).first()
            if fields["post"] is None:
                raise _invalid("post target is not a post of this site and locale")
        elif target == TargetType.URL:
            if not is_safe_url(str(item.get("url") or "")):
                raise _invalid("url is not a safe link")
            fields["url"] = item["url"]
        elif target == TargetType.ROUTE:
            if not ROUTE_RE.match(str(item.get("route") or "")):
                raise _invalid("route must be a route name")
            params = item.get("route_params") or {}
            if not all(isinstance(k, str) and isinstance(v, (str, int)) for k, v in params.items()):
                raise _invalid("route_params are string or integer values")
            fields["route"], fields["route_params"] = item["route"], params
        else:
            raise _invalid("unknown target_type")
        plan.append((fields, _plan(menu, item.get("children") or [], depth + 1, counter)))
    return plan


def _write(menu: Menu, plan, parent=None) -> None:
    for position, (fields, children) in enumerate(plan):
        row = MenuItem.objects.create(menu=menu, parent=parent, position=position, **fields)
        _write(menu, children, row)


def create(data: dict) -> Menu:
    site, locale = data.get("site", ""), data["locale"]
    check_scope(site, locale)
    key = str(data["key"]).strip().lower()
    if not KEY_RE.match(key):
        raise _invalid("key must be a slug")
    menu = Menu(site=site, locale=locale, key=key, title=data.get("title", ""))
    plan = _plan(menu, data.get("items") or [], 1, [0])
    try:
        with mutate_and_emit() as emit:
            menu.save()
            _write(menu, plan)
            events.emit_menu_changed(emit, menu)
            cache.bump_after_commit(menu.site)
    except IntegrityError:
        raise CmsError(409, ERR_409_SLUG_TAKEN) from None
    return menu


def get(menu_id) -> Menu:
    menu = Menu.objects.filter(pk=menu_id).first()
    if menu is None:
        raise CmsError(404, ERR_404_NOT_FOUND)
    return menu


def replace(menu_id, data: dict) -> Menu:
    with mutate_and_emit() as emit:
        menu = Menu.objects.select_for_update().filter(pk=menu_id).first()
        if menu is None:
            raise CmsError(404, ERR_404_NOT_FOUND)
        plan = _plan(menu, data.get("items") or [], 1, [0])
        if "title" in data:
            menu.title = data["title"]
        menu.items.all().delete()
        _write(menu, plan)
        menu.save()
        events.emit_menu_changed(emit, menu)
        cache.bump_after_commit(menu.site)
    return menu


def delete(menu_id) -> None:
    with mutate_and_emit() as emit:
        menu = get(menu_id)
        events.emit_menu_changed(emit, menu)
        cache.bump_after_commit(menu.site)
        menu.delete()


def staff_tree(menu: Menu) -> list[dict]:
    rows = list(menu.items.all().order_by("position", "id"))
    by_parent: dict = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def build(parent_id):
        return [{
            "id": row.pk, "label": row.label, "target_type": row.target_type, "page": row.page_id,
            "post": row.post_id, "url": row.url or None, "route": row.route or None,
            "route_params": row.route_params or {}, "new_tab": row.new_tab, "children": build(row.pk),
        } for row in by_parent.get(parent_id, [])]

    return build(None)


def public_tree(menu: Menu) -> list[dict]:
    rows = list(menu.items.select_related("page", "post", "page__live_revision", "page__scheduled_revision",
                                          "post__live_revision", "post__scheduled_revision")
                .order_by("position", "id"))
    by_parent: dict = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def href(row):
        if row.target_type in (TargetType.PAGE, TargetType.POST):
            target = row.page if row.target_type == TargetType.PAGE else row.post
            if target is None or serving_revision(target) is None:
                return False
            return public_path(target)
        if row.target_type == TargetType.URL:
            return row.url
        return None

    def build(parent_id):
        out = []
        for row in by_parent.get(parent_id, []):
            link = href(row)
            if link is False:
                continue
            out.append({
                "label": row.label, "target_type": row.target_type, "href": link,
                "route": row.route or None, "route_params": row.route_params or {},
                "new_tab": row.new_tab, "children": build(row.pk),
            })
        return out

    return build(None)


__all__ = ["create", "delete", "get", "public_tree", "replace", "staff_tree"]
