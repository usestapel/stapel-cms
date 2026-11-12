"""Manual redirects (the automatic ones are written by ``paths``)."""
from __future__ import annotations

from stapel_core.comm import mutate_and_emit

from ..errors import ERR_400_REDIRECT_INVALID, ERR_404_NOT_FOUND
from ..models import Redirect, RedirectSource
from . import CmsError, cache, paths
from .content import check_scope, user_id


def create(user, data: dict) -> Redirect:
    site, locale = data.get("site", ""), data["locale"]
    check_scope(site, locale)
    old_path = paths.normalize_path(data["old_path"])
    new_path = paths.clean_redirect_target(data["new_path"])
    if old_path == new_path:
        raise CmsError(400, ERR_400_REDIRECT_INVALID)
    with mutate_and_emit() as emit:
        redirect = paths.add_redirect(site, locale, old_path, new_path, RedirectSource.MANUAL, emit, user_id(user))
        if redirect is None:
            raise CmsError(400, ERR_400_REDIRECT_INVALID)
        if "permanent" in data and redirect.permanent != bool(data["permanent"]):
            redirect.permanent = bool(data["permanent"])
            redirect.save(update_fields=["permanent"])
        cache.bump_after_commit(site)
    return redirect


def delete(redirect_id) -> None:
    redirect = Redirect.objects.filter(pk=redirect_id).first()
    if redirect is None:
        raise CmsError(404, ERR_404_NOT_FOUND)
    cache.bump(redirect.site)
    redirect.delete()


__all__ = ["create", "delete"]
