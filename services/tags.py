"""Blog tags: per site and locale, slug-keyed."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from ..errors import ERR_404_NOT_FOUND, ERR_409_SLUG_TAKEN
from ..models import Tag
from . import CmsError, cache, paths
from .content import check_scope


def get(tag_id) -> Tag:
    tag = Tag.objects.filter(pk=tag_id).first()
    if tag is None:
        raise CmsError(404, ERR_404_NOT_FOUND)
    return tag


def create(data: dict) -> Tag:
    site, locale = data.get("site", ""), data["locale"]
    check_scope(site, locale)
    tag = Tag(site=site, locale=locale, slug=paths.clean_slug(data["slug"]), name=data["name"])
    try:
        with transaction.atomic():
            tag.save()
    except IntegrityError:
        raise CmsError(409, ERR_409_SLUG_TAKEN) from None
    return tag


def update(tag_id, data: dict) -> Tag:
    tag = get(tag_id)
    if "slug" in data:
        tag.slug = paths.clean_slug(data["slug"])
    if "name" in data:
        tag.name = data["name"]
    try:
        with transaction.atomic():
            tag.save()
            cache.bump_after_commit(tag.site)
    except IntegrityError:
        raise CmsError(409, ERR_409_SLUG_TAKEN) from None
    return tag


def delete(tag_id) -> None:
    tag = get(tag_id)
    with transaction.atomic():
        cache.bump_after_commit(tag.site)
        tag.delete()


__all__ = ["create", "delete", "get", "update"]
