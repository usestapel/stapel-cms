"""Presenters for stapel-cms — the DTO-building layer (§55).

Views never instantiate a ``dto.py`` dataclass (SWAP002) nor import a
concrete presenter (SWAP001); they resolve one through ``get_presenter`` so
a host can swap the presentation via ``STAPEL_SWAP`` without forking.
"""
from __future__ import annotations

from stapel_core.django.swappable import declare_swap, get_presenter

from .dto import (
    BlockTypeListDTO,
    PostArchiveDTO,
    PreviewTokenDTO,
    PublicMenuDTO,
    PublicPostDTO,
    PublicPostSummaryDTO,
    PublicTagListDTO,
    ResolveDTO,
    RevisionDTO,
    StaffContentDTO,
    StaffMenuDTO,
    StaffRedirectDTO,
    StaffTagDTO,
)

PUBLIC_PRESENTER_KEY = "STAPEL_CMS_PUBLIC_PRESENTER"
STAFF_PRESENTER_KEY = "STAPEL_CMS_STAFF_PRESENTER"
DEFAULT_PUBLIC_PRESENTER = "stapel_cms.presenters.PublicPresenter"
DEFAULT_STAFF_PRESENTER = "stapel_cms.presenters.StaffPresenter"

declare_swap(PUBLIC_PRESENTER_KEY, DEFAULT_PUBLIC_PRESENTER)
declare_swap(STAFF_PRESENTER_KEY, DEFAULT_STAFF_PRESENTER)


class PublicPresenter:
    """Service dicts of the public read side -> DTOs."""

    def resolve(self, data: dict) -> ResolveDTO:
        return ResolveDTO(kind=data["kind"], locale=data["locale"], page=data.get("page"),
                          post=data.get("post"), redirect=data.get("redirect"))

    def post(self, data: dict) -> PublicPostDTO:
        return PublicPostDTO(**data)

    def post_summary(self, data: dict) -> PublicPostSummaryDTO:
        return PublicPostSummaryDTO(**data)

    def archive(self, months: list) -> PostArchiveDTO:
        return PostArchiveDTO(months=months)

    def tags(self, items: list) -> PublicTagListDTO:
        return PublicTagListDTO(items=items)

    def menu(self, data: dict) -> PublicMenuDTO:
        return PublicMenuDTO(key=data["key"], title=data["title"], locale=data["locale"], items=data["items"])


class StaffPresenter:
    """Rows of the staff API -> DTOs."""

    def content(self, obj) -> StaffContentDTO:
        from .models import Post
        from .services.content import has_unpublished_changes, public_path

        extra = {}
        if isinstance(obj, Post):
            extra = {"excerpt": obj.excerpt, "cover": obj.cover, "reading_time_minutes": obj.reading_time_minutes,
                     "tags": [{"id": t.pk, "slug": t.slug, "name": t.name} for t in obj.tags.all().order_by("name")]}
        else:
            extra = {"parent": obj.parent_id, "template": obj.template}
        return StaffContentDTO(
            id=obj.pk, site=obj.site, locale=obj.locale, translation_group=obj.translation_group,
            slug=obj.slug, path=public_path(obj), title=obj.title, blocks=obj.blocks or [],
            seo_title=obj.seo_title, seo_description=obj.seo_description, canonical_url=obj.canonical_url,
            og_image=obj.og_image, noindex=obj.noindex, status=obj.status, version=obj.version,
            publish_at=obj.publish_at, published_at=obj.published_at, last_published_at=obj.last_published_at,
            archived_at=obj.archived_at, author_id=obj.author_id, updated_by_id=obj.updated_by_id,
            live_revision=obj.live_revision.number if obj.live_revision_id else None,
            scheduled_revision=obj.scheduled_revision.number if obj.scheduled_revision_id else None,
            has_unpublished_changes=has_unpublished_changes(obj),
            created_at=obj.created_at, updated_at=obj.updated_at,
            warnings=list(getattr(obj, "cms_warnings", None) or []), **extra,
        )

    def revision(self, revision, obj) -> RevisionDTO:
        return RevisionDTO(
            number=revision.number, note=revision.note, created_by_id=revision.created_by_id,
            created_at=revision.created_at, is_live=revision.pk == obj.live_revision_id,
            is_scheduled=revision.pk == obj.scheduled_revision_id, snapshot=revision.snapshot or {},
        )

    def preview_token(self, data: dict) -> PreviewTokenDTO:
        return PreviewTokenDTO(token=data["token"], expires_at=data["expires_at"], url=data["url"])

    def tag(self, tag) -> StaffTagDTO:
        return StaffTagDTO(id=tag.pk, site=tag.site, locale=tag.locale, slug=tag.slug, name=tag.name,
                           created_at=tag.created_at)

    def menu(self, menu) -> StaffMenuDTO:
        from .services.menus import staff_tree

        return StaffMenuDTO(id=menu.pk, site=menu.site, locale=menu.locale, key=menu.key, title=menu.title,
                            items=staff_tree(menu), updated_at=menu.updated_at)

    def redirect(self, redirect) -> StaffRedirectDTO:
        return StaffRedirectDTO(
            id=redirect.pk, site=redirect.site, locale=redirect.locale, old_path=redirect.old_path,
            new_path=redirect.new_path, permanent=redirect.permanent, source=redirect.source,
            created_by_id=redirect.created_by_id, created_at=redirect.created_at,
        )

    def block_types(self, items: list) -> BlockTypeListDTO:
        return BlockTypeListDTO(items=items)


def get_public_presenter():
    return get_presenter(PUBLIC_PRESENTER_KEY, default=DEFAULT_PUBLIC_PRESENTER)


def get_staff_presenter():
    return get_presenter(STAFF_PRESENTER_KEY, default=DEFAULT_STAFF_PRESENTER)


__all__ = ["PublicPresenter", "StaffPresenter", "get_public_presenter", "get_staff_presenter"]
