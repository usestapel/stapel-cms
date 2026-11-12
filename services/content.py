"""Pages and posts: create, edit, publish workflow, revisions, variants.

One implementation serves both kinds; :data:`SPECS` names what differs.
Structural fields (slug, parent, tags) apply on save; content fields are
revisioned and reach the public only through a published snapshot.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone
from stapel_core.comm import mutate_and_emit

from .. import fsm
from ..blocks import BlockError, validate_blocks, word_count
from ..errors import (
    ERR_400_LOCALE_UNKNOWN,
    ERR_400_PARENT_INVALID,
    ERR_400_PUBLISH_AT_INVALID,
    ERR_400_SITE_UNKNOWN,
    ERR_400_TAG_UNKNOWN,
    ERR_400_TEMPLATE_UNKNOWN,
    ERR_400_URL_UNSAFE,
    ERR_404_NOT_FOUND,
    ERR_404_REVISION_NOT_FOUND,
    ERR_409_DELETE_PUBLISHED,
    ERR_409_SLUG_TAKEN,
    ERR_409_TRANSITION_INVALID,
    ERR_409_VARIANT_EXISTS,
    ERR_409_VERSION_CONFLICT,
)
from ..models import Kind, Page, Post, Revision, Status, Tag
from ..safety import is_media_ref, is_safe_url
from . import CmsError, cache, events, forms, media, paths, sitemaps

SEO_FIELDS = ("seo_title", "seo_description", "canonical_url", "og_image", "noindex")


@dataclass(frozen=True)
class KindSpec:
    kind: str
    model: type
    content_fields: tuple


PAGE = KindSpec(Kind.PAGE, Page, ("title", "template", "blocks", *SEO_FIELDS))
POST = KindSpec(Kind.POST, Post, ("title", "excerpt", "cover", "blocks", *SEO_FIELDS))
SPECS = {Kind.PAGE: PAGE, Kind.POST: POST}


# ── Helpers ────────────────────────────────────────────────────────────────


def user_id(user) -> str:
    return "" if user is None or getattr(user, "pk", None) is None else str(user.pk)


def check_scope(site: str, locale: str) -> None:
    from .. import sitekeys
    from ..conf import cms_settings

    if not sitekeys.is_known(site):
        raise CmsError(400, ERR_400_SITE_UNKNOWN)
    if locale not in list(cms_settings.LOCALES or []):
        raise CmsError(400, ERR_400_LOCALE_UNKNOWN)


def reading_time(blocks) -> int:
    from ..conf import cms_settings

    wpm = max(1, int(cms_settings.WORDS_PER_MINUTE))
    return max(1, math.ceil(word_count(blocks) / wpm))


def public_path(obj) -> str:
    return obj.path if isinstance(obj, Page) else paths.post_path(obj.slug)


def snapshot(obj) -> dict:
    spec = PAGE if isinstance(obj, Page) else POST
    snap = {name: getattr(obj, name) for name in spec.content_fields}
    snap["slug"] = obj.slug
    snap["path"] = public_path(obj)
    if isinstance(obj, Post):
        snap["reading_time_minutes"] = reading_time(obj.blocks)
        snap["tags"] = sorted(obj.tags.values_list("slug", flat=True)) if obj.pk else []
    return snap


def apply_snapshot(obj, snap: dict) -> None:
    spec = PAGE if isinstance(obj, Page) else POST
    for name in spec.content_fields:
        if name in snap:
            setattr(obj, name, snap[name])


def serving_revision(obj, now=None):
    """The revision the public sees right now, or ``None``."""
    now = now or timezone.now()
    if obj.scheduled_revision_id and obj.publish_at and obj.publish_at <= now:
        return obj.scheduled_revision
    return obj.live_revision


def has_unpublished_changes(obj) -> bool:
    live = obj.live_revision
    if live is None:
        return True
    current = snapshot(obj)
    return any(current.get(k) != (live.snapshot or {}).get(k) for k in current if k != "path")


def _append_revision(obj, kind: str, user, note: str) -> Revision:
    from ..conf import cms_settings

    last = Revision.objects.filter(kind=kind, object_id=obj.pk).aggregate(n=Max("number"))["n"] or 0
    revision = Revision.objects.create(
        kind=kind, object_id=obj.pk, number=last + 1, snapshot=snapshot(obj), note=note[:200],
        created_by_id=user_id(user),
    )
    keep = max(1, int(cms_settings.REVISIONS_KEEP))
    protected = {obj.live_revision_id, obj.scheduled_revision_id, revision.pk} - {None}
    stale = list(
        Revision.objects.filter(kind=kind, object_id=obj.pk).exclude(pk__in=protected)
        .order_by("-number").values_list("pk", flat=True)[max(0, keep - len(protected)):]
    )
    if stale:
        Revision.objects.filter(pk__in=stale).delete()
    return revision


def _clean_common(spec: KindSpec, obj, data: dict) -> None:
    from ..conf import cms_settings

    for name in spec.content_fields:
        if name in data:
            setattr(obj, name, data[name])
    if "blocks" in data:
        try:
            obj.blocks = validate_blocks(data["blocks"])
        except BlockError as exc:
            raise CmsError(400, exc.key, exc.params) from None
    if "template" in data and obj.template not in list(cms_settings.PAGE_TEMPLATES or []):
        raise CmsError(400, ERR_400_TEMPLATE_UNKNOWN)
    if obj.canonical_url and not is_safe_url(obj.canonical_url):
        raise CmsError(400, ERR_400_URL_UNSAFE)
    for ref_field in ("og_image", "cover"):
        value = getattr(obj, ref_field, "")
        if value and not is_media_ref(value):
            raise CmsError(400, ERR_400_URL_UNSAFE)


def _tags_for(obj, slugs_or_ids) -> list:
    ids = [int(v) for v in slugs_or_ids]
    tags = list(Tag.objects.filter(site=obj.site, locale=obj.locale, pk__in=ids))
    if len(tags) != len(set(ids)):
        raise CmsError(400, ERR_400_TAG_UNKNOWN)
    return tags


def _parent(obj, parent_id):
    if parent_id is None:
        return None
    parent = Page.objects.filter(pk=parent_id).first()
    if parent is None or parent.site != obj.site or parent.locale != obj.locale:
        raise CmsError(400, ERR_400_PARENT_INVALID)
    return parent


def _public_changed(site: str) -> None:
    """What the public sees on ``site`` changed: drop its read cache and sitemaps."""
    cache.bump_after_commit(site)
    sitemaps.invalidate_after_commit(site)


def _with_warnings(obj, warnings: list[dict]):
    """Attach non-blocking findings of this request for the staff response."""
    obj.cms_warnings = warnings
    return obj


def get(kind: str, obj_id) -> object:
    obj = SPECS[kind].model.objects.select_related("live_revision", "scheduled_revision").filter(pk=obj_id).first()
    if obj is None:
        raise CmsError(404, ERR_404_NOT_FOUND)
    return obj


def _locked(kind: str, obj_id):
    obj = (SPECS[kind].model.objects.select_for_update().filter(pk=obj_id).first())
    if obj is None:
        raise CmsError(404, ERR_404_NOT_FOUND)
    return obj


# ── Create / update / delete ───────────────────────────────────────────────


def create(kind: str, user, data: dict):
    spec = SPECS[kind]
    warnings = forms.check_save(data.get("blocks"))
    obj = spec.model(site=data.get("site", ""), locale=data["locale"])
    check_scope(obj.site, obj.locale)
    _clean_common(spec, obj, data)
    obj.author_id = obj.updated_by_id = user_id(user)
    with mutate_and_emit():
        if isinstance(obj, Page):
            obj.slug = paths.clean_slug(data.get("slug", ""), allow_empty=data.get("parent") is None)
            obj.parent = _parent(obj, data.get("parent"))
            obj.path = paths.check_page_placement(obj, obj.parent, obj.slug)
            paths.ensure_free(obj.site, obj.locale, obj.path)
        else:
            obj.slug = paths.clean_slug(data.get("slug"))
            if Post.objects.filter(site=obj.site, locale=obj.locale, slug=obj.slug).exists():
                raise CmsError(409, ERR_409_SLUG_TAKEN)
            obj.reading_time_minutes = reading_time(obj.blocks)
            if data.get("published_at"):
                obj.published_at = data["published_at"]
        if data.get("translation_group"):
            obj.translation_group = data["translation_group"]
        obj.save()
        if isinstance(obj, Post) and data.get("tags") is not None:
            obj.tags.set(_tags_for(obj, data["tags"]))
        _append_revision(obj, kind, user, "created")
    media.sync_after_commit(obj, kind)
    return _with_warnings(get(kind, obj.pk), warnings)


def update(kind: str, obj_id, user, data: dict):
    spec = SPECS[kind]
    warnings = forms.check_save(data["blocks"]) if "blocks" in data else []
    with mutate_and_emit() as emit:
        obj = _locked(kind, obj_id)
        expected = data.get("version")
        if expected is not None and int(expected) != obj.version:
            raise CmsError(409, ERR_409_VERSION_CONFLICT, {"current": obj.version})
        old_version, old_path = obj.version, public_path(obj)
        _clean_common(spec, obj, data)
        if isinstance(obj, Page):
            parent = _parent(obj, data["parent"]) if "parent" in data else obj.parent
            slug = paths.clean_slug(data["slug"], allow_empty=parent is None) if "slug" in data else obj.slug
            if (parent.pk if parent else None) != obj.parent_id or slug != obj.slug:
                new_path = paths.check_page_placement(obj, parent, slug)
                paths.ensure_free(obj.site, obj.locale, new_path, exclude_pk=obj.pk)
                paths.move_subtree(obj, old_path, new_path, emit)
                obj.parent, obj.slug, obj.path = parent, slug, new_path
        else:
            if "slug" in data:
                slug = paths.clean_slug(data["slug"])
                if Post.objects.filter(site=obj.site, locale=obj.locale, slug=slug).exclude(pk=obj.pk).exists():
                    raise CmsError(409, ERR_409_SLUG_TAKEN)
                obj.slug = slug
            if "published_at" in data and data["published_at"] is not None:
                obj.published_at = data["published_at"]
            if data.get("tags") is not None:
                obj.tags.set(_tags_for(obj, data["tags"]))
            obj.reading_time_minutes = reading_time(obj.blocks)
        new_path = public_path(obj)
        if new_path != old_path and obj.published_at is not None:
            paths.add_redirect(obj.site, obj.locale, old_path, new_path, "auto", emit)
        # The guard that holds on any database: the row moves only from the
        # version this editor read.
        if not spec.model.objects.filter(pk=obj.pk, version=old_version).update(version=F("version") + 1):
            raise CmsError(409, ERR_409_VERSION_CONFLICT, {"current": old_version + 1})
        obj.version = old_version + 1
        obj.updated_by_id = user_id(user)
        obj.save()
        _append_revision(obj, kind, user, "saved")
        if new_path != old_path and serving_revision(obj) is not None:
            _public_changed(obj.site)
    media.sync_after_commit(obj, kind)
    return _with_warnings(get(kind, obj.pk), warnings)


def delete(kind: str, obj_id) -> None:
    with transaction.atomic():
        obj = _locked(kind, obj_id)
        if obj.published_at is not None or obj.live_revision_id:
            raise CmsError(409, ERR_409_DELETE_PUBLISHED)
        if isinstance(obj, Page) and obj.children.exists():
            raise CmsError(400, ERR_400_PARENT_INVALID)
        obj.blocks, obj.og_image = [], ""
        if isinstance(obj, Post):
            obj.cover = ""
        obj.live_revision = obj.scheduled_revision = None
        media.sync_after_commit(obj, kind)
        Revision.objects.filter(kind=kind, object_id=obj.pk).delete()
        obj.delete()


# ── Workflow ───────────────────────────────────────────────────────────────


def transition(kind: str, obj_id, user, to: str, publish_at=None):
    warnings = forms.check_publish(get(kind, obj_id).blocks) if to in (fsm.PUBLISHED, fsm.SCHEDULED) else []
    with mutate_and_emit() as emit:
        obj = _locked(kind, obj_id)
        from_status = obj.status
        if not fsm.allowed(from_status, to):
            raise CmsError(409, ERR_409_TRANSITION_INVALID, {"from": from_status, "to": to})
        now = timezone.now()
        if to == fsm.PUBLISHED:
            _publish(obj, kind, user, emit, now, note="published")
        elif to == fsm.SCHEDULED:
            if publish_at is None or publish_at <= now:
                raise CmsError(400, ERR_400_PUBLISH_AT_INVALID)
            obj.scheduled_revision = _append_revision(obj, kind, user, "scheduled")
            obj.publish_at = publish_at
            obj.status = Status.SCHEDULED
            if isinstance(obj, Post) and obj.published_at is None:
                obj.published_at = publish_at
            obj.save()
            _public_changed(obj.site)
        elif to == fsm.DRAFT:
            if from_status == fsm.SCHEDULED:
                obj.scheduled_revision, obj.publish_at = None, None
                if obj.live_revision_id:
                    obj.status = Status.PUBLISHED
                else:
                    obj.status = Status.DRAFT
                    obj.published_at = None
            else:
                obj.status, obj.archived_at = Status.DRAFT, None
            obj.save()
            _public_changed(obj.site)
        elif to == fsm.ARCHIVED:
            was_public = serving_revision(obj, now) is not None
            obj.live_revision = obj.scheduled_revision = None
            obj.publish_at = None
            obj.status, obj.archived_at = Status.ARCHIVED, now
            obj.save()
            if was_public:
                events.emit_unpublished(emit, obj, kind, public_path(obj))
                _public_changed(obj.site)
    media.sync_after_commit(obj, kind)
    return _with_warnings(get(kind, obj.pk), warnings)


def _publish(obj, kind, user, emit, now, *, note: str, revision=None) -> None:
    revision = revision or _append_revision(obj, kind, user, note)
    first = obj.last_published_at is None
    obj.live_revision = revision
    obj.scheduled_revision, obj.publish_at = None, None
    if obj.published_at is None:
        obj.published_at = now
    obj.last_published_at = now
    obj.status, obj.archived_at = Status.PUBLISHED, None
    obj.save()
    path = public_path(obj)
    paths.drop_redirect_at(obj.site, obj.locale, path)
    events.emit_published(emit, obj, kind, path, revision, first)  # emit-check: ok — emit is the caller's mutate_and_emit() emitter
    _public_changed(obj.site)


def promote_due(now=None) -> int:
    """Scheduled snapshots whose time has come go live. Returns how many."""
    now = now or timezone.now()
    promoted = 0
    for kind, spec in SPECS.items():
        due = list(spec.model.objects.filter(scheduled_revision__isnull=False, publish_at__lte=now)
                   .values_list("pk", flat=True)[:500])
        for pk in due:
            with mutate_and_emit() as emit:
                obj = spec.model.objects.select_for_update().filter(
                    pk=pk, scheduled_revision__isnull=False, publish_at__lte=now).first()
                if obj is None:
                    continue
                revision = obj.scheduled_revision
                _publish(obj, kind, None, emit, obj.publish_at, note="", revision=revision)
                promoted += 1
    return promoted


# ── Revisions ──────────────────────────────────────────────────────────────


def revisions(kind: str, obj_id):
    get(kind, obj_id)
    return Revision.objects.filter(kind=kind, object_id=obj_id)


def restore(kind: str, obj_id, number: int, user):
    with transaction.atomic():
        obj = _locked(kind, obj_id)
        revision = Revision.objects.filter(kind=kind, object_id=obj.pk, number=number).first()
        if revision is None:
            raise CmsError(404, ERR_404_REVISION_NOT_FOUND)
        apply_snapshot(obj, revision.snapshot or {})
        if isinstance(obj, Post):
            obj.reading_time_minutes = reading_time(obj.blocks)
        spec = SPECS[kind]
        spec.model.objects.filter(pk=obj.pk).update(version=F("version") + 1)
        obj.version += 1
        obj.updated_by_id = user_id(user)
        obj.save()
        _append_revision(obj, kind, user, f"restored from #{number}")
    media.sync_after_commit(obj, kind)
    return get(kind, obj.pk)


# ── Locale variants ────────────────────────────────────────────────────────


def create_variant(kind: str, obj_id, user, locale: str, machine_translate: bool):
    from .translate import translate_fields

    source = get(kind, obj_id)
    check_scope(source.site, locale)
    spec = SPECS[kind]
    if spec.model.objects.filter(translation_group=source.translation_group, locale=locale).exists():
        raise CmsError(409, ERR_409_VARIANT_EXISTS)
    fields = {name: getattr(source, name) for name in spec.content_fields}
    if machine_translate:
        fields = translate_fields(fields, source.locale, locale)
    data = {**fields, "site": source.site, "locale": locale, "slug": source.slug,
            "translation_group": source.translation_group}
    if isinstance(source, Page):
        parent = None
        if source.parent is not None:
            parent = Page.objects.filter(translation_group=source.parent.translation_group, locale=locale).first()
        data["parent"] = parent.pk if parent else None
    else:
        slugs = list(source.tags.values_list("slug", flat=True))
        data["tags"] = list(Tag.objects.filter(site=source.site, locale=locale, slug__in=slugs)
                            .values_list("pk", flat=True))
    return create(kind, user, data)


__all__ = [
    "PAGE", "POST", "SPECS", "apply_snapshot", "check_scope", "create", "create_variant", "delete", "get",
    "has_unpublished_changes", "promote_due", "public_path", "reading_time", "restore", "revisions",
    "serving_revision", "snapshot", "transition", "update", "user_id",
]
