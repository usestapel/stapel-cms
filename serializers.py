"""Serializers for the stapel-cms API.

The class names are the codegen contract: drf-spectacular names each
component after its serializer minus the ``Serializer`` suffix, and the
React pair generates its client from those names. Every CharField declares
a ``max_length``. Blocks are typed by the block registry, not here: the
wire carries ``{type, id, data}`` and ``GET staff/block-types/`` publishes
the per-type schemas.
"""
import datetime

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from stapel_core.media.drf import StapelImageSerializer
from stapel_core.django.api.errors import StapelValidationError

from . import models as m
from .errors import ERR_400_OBJECT_EXPECTED

UTC = datetime.timezone.utc

FREE_OBJECT = {"type": "object", "additionalProperties": True}


@extend_schema_field(FREE_OBJECT)
class ObjectField(serializers.JSONField):
    """A JSON object whose shape another contract owns (a block's data, a snapshot)."""

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise StapelValidationError(ERR_400_OBJECT_EXPECTED)
        return super().to_internal_value(data)


def _dt(**kwargs):
    return serializers.DateTimeField(default_timezone=UTC, **kwargs)


def _site():
    return serializers.CharField(max_length=m.SITE_MAX_LENGTH, allow_blank=True, default="")


def _locale():
    return serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)


# ── Shared ─────────────────────────────────────────────────────────────────


class BlockSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=48)
    id = serializers.CharField(max_length=64)
    data = ObjectField()


class SeoSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=m.SEO_TITLE_MAX_LENGTH, allow_blank=True)
    description = serializers.CharField(max_length=m.SEO_DESCRIPTION_MAX_LENGTH, allow_blank=True)
    canonical_url = serializers.CharField(max_length=m.URL_MAX_LENGTH, allow_null=True)
    og_image = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_null=True)
    og_image_url = serializers.CharField(
        max_length=2048, allow_null=True,
        help_text="Absolute URL of og_image's default rendition when the media service described it; "
                  "null otherwise (render from the ref).")
    noindex = serializers.BooleanField()


class AlternateSerializer(serializers.Serializer):
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)


class BreadcrumbSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True)
    path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)


class TagRefSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH)
    name = serializers.CharField(max_length=m.TAG_NAME_MAX_LENGTH)


class CmsImageSerializer(StapelImageSerializer):
    """A described media ref: stapel-core's ``StapelImage`` shape plus the ``ref`` it describes."""

    ref = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH)


# ── Public ─────────────────────────────────────────────────────────────────


class PublicPageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    template = serializers.CharField(max_length=m.TEMPLATE_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True)
    blocks = BlockSerializer(many=True)
    seo = SeoSerializer()
    published_at = _dt(allow_null=True)
    updated_at = _dt(allow_null=True)
    alternates = AlternateSerializer(many=True)
    breadcrumbs = BreadcrumbSerializer(many=True)
    media = CmsImageSerializer(
        many=True, help_text="Described images of the media refs above (og_image, blocks), when the media "
                             "service answered; a ref missing here renders from the ref alone.")


class PublicPostSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH)
    path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True)
    excerpt = serializers.CharField(max_length=m.EXCERPT_MAX_LENGTH, allow_blank=True)
    cover = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_null=True)
    tags = TagRefSerializer(many=True)
    author_id = serializers.CharField(max_length=m.USER_ID_MAX_LENGTH, allow_null=True)
    reading_time_minutes = serializers.IntegerField(min_value=1)
    published_at = _dt(allow_null=True)


class PublicPostSerializer(PublicPostSummarySerializer):
    blocks = BlockSerializer(many=True)
    seo = SeoSerializer()
    updated_at = _dt(allow_null=True)
    alternates = AlternateSerializer(many=True)
    media = CmsImageSerializer(
        many=True, help_text="Described images of the media refs above (cover, og_image, blocks), when the "
                             "media service answered; a ref missing here renders from the ref alone.")


class RedirectTargetSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    permanent = serializers.BooleanField()


class ResolveMetaSerializer(serializers.Serializer):
    """Server facts a renderer needs next to the content."""

    embed_hosts = serializers.ListField(
        child=serializers.CharField(max_length=253),
        help_text="EMBED_HOSTS: the exact hosts an embed block may use (https only); the client-side "
                  "embed allowlist should equal this.")


class ResolveResponseSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["page", "post", "redirect"])
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    page = PublicPageSerializer(allow_null=True)
    post = PublicPostSerializer(allow_null=True)
    redirect = RedirectTargetSerializer(allow_null=True)
    meta = ResolveMetaSerializer()


class _AnchorPage(serializers.Serializer):
    next_anchor = serializers.CharField(max_length=64, allow_null=True)
    prev_anchor = serializers.CharField(max_length=64, allow_null=True)
    has_next = serializers.BooleanField()
    has_prev = serializers.BooleanField()
    count = serializers.IntegerField(min_value=0)


class PublicPostPageSerializer(_AnchorPage):
    items = PublicPostSummarySerializer(many=True)


class ArchiveMonthSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    count = serializers.IntegerField(min_value=0)


class PostArchiveResponseSerializer(serializers.Serializer):
    months = ArchiveMonthSerializer(many=True)


class PublicTagSerializer(TagRefSerializer):
    count = serializers.IntegerField(min_value=0)


class PublicTagListSerializer(serializers.Serializer):
    items = PublicTagSerializer(many=True)


class PublicMenuItemSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=m.MENU_LABEL_MAX_LENGTH)
    target_type = serializers.ChoiceField(choices=m.TargetType.choices)
    href = serializers.CharField(max_length=m.URL_MAX_LENGTH, allow_null=True)
    route = serializers.CharField(max_length=m.ROUTE_MAX_LENGTH, allow_null=True)
    route_params = ObjectField()
    new_tab = serializers.BooleanField()

    def get_fields(self):
        fields = super().get_fields()
        fields["children"] = PublicMenuItemSerializer(many=True)
        return fields


class PublicMenuSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=m.MENU_KEY_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True)
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    items = PublicMenuItemSerializer(many=True)


# ── Staff: pages and posts ─────────────────────────────────────────────────


CONTENT_WARNING_CODES = [("form_unpublished", "form_unpublished"), ("form_unverified", "form_unverified")]


class ContentWarningSerializer(serializers.Serializer):
    """A non-blocking finding of this save or publish (not stored)."""

    code = serializers.ChoiceField(
        choices=CONTENT_WARNING_CODES,
        help_text="form_unpublished: the embedded form exists but is not published (publishing the page "
                  "will be refused); form_unverified: stapel-forms could not be asked, only the shape was checked.")
    field = serializers.CharField(max_length=200, help_text="Path of the field, e.g. blocks.2.data.form_id.")
    params = ObjectField()


class _StaffContentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    site = serializers.CharField(max_length=m.SITE_MAX_LENGTH, allow_blank=True)
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    translation_group = serializers.UUIDField()
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH, allow_blank=True)
    path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH)
    blocks = BlockSerializer(many=True)
    seo_title = serializers.CharField(max_length=m.SEO_TITLE_MAX_LENGTH, allow_blank=True)
    seo_description = serializers.CharField(max_length=m.SEO_DESCRIPTION_MAX_LENGTH, allow_blank=True)
    canonical_url = serializers.CharField(max_length=m.URL_MAX_LENGTH, allow_blank=True)
    og_image = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_blank=True)
    noindex = serializers.BooleanField()
    status = serializers.ChoiceField(choices=m.Status.choices)
    version = serializers.IntegerField(min_value=1)
    publish_at = _dt(allow_null=True)
    published_at = _dt(allow_null=True)
    last_published_at = _dt(allow_null=True)
    archived_at = _dt(allow_null=True)
    author_id = serializers.CharField(max_length=m.USER_ID_MAX_LENGTH, allow_blank=True)
    updated_by_id = serializers.CharField(max_length=m.USER_ID_MAX_LENGTH, allow_blank=True)
    live_revision = serializers.IntegerField(allow_null=True, help_text="Number of the live revision.")
    scheduled_revision = serializers.IntegerField(allow_null=True, help_text="Number of the scheduled revision.")
    has_unpublished_changes = serializers.BooleanField()
    created_at = _dt()
    updated_at = _dt()
    warnings = ContentWarningSerializer(many=True, help_text="Findings of this request only; empty on reads.")


class StaffPageSerializer(_StaffContentSerializer):
    parent = serializers.IntegerField(allow_null=True)
    template = serializers.CharField(max_length=m.TEMPLATE_MAX_LENGTH)


class StaffTagRefSerializer(TagRefSerializer):
    id = serializers.IntegerField()


class StaffPostSerializer(_StaffContentSerializer):
    excerpt = serializers.CharField(max_length=m.EXCERPT_MAX_LENGTH, allow_blank=True)
    cover = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_blank=True)
    reading_time_minutes = serializers.IntegerField(min_value=1)
    tags = StaffTagRefSerializer(many=True)


class _ContentWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH)
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH, allow_blank=True)
    blocks = serializers.ListField(child=ObjectField(), required=False, max_length=1000)
    seo_title = serializers.CharField(max_length=m.SEO_TITLE_MAX_LENGTH, allow_blank=True, required=False)
    seo_description = serializers.CharField(max_length=m.SEO_DESCRIPTION_MAX_LENGTH, allow_blank=True, required=False)
    canonical_url = serializers.CharField(max_length=m.URL_MAX_LENGTH, allow_blank=True, required=False)
    og_image = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_blank=True, required=False)
    noindex = serializers.BooleanField(required=False)


class StaffPageCreateRequestSerializer(_ContentWriteSerializer):
    site = _site()
    locale = _locale()
    parent = serializers.IntegerField(allow_null=True, required=False, default=None)
    template = serializers.CharField(max_length=m.TEMPLATE_MAX_LENGTH, default="default")


class StaffPageUpdateRequestSerializer(_ContentWriteSerializer):
    version = serializers.IntegerField(min_value=1, help_text="The version this editor read (optimistic lock).")
    parent = serializers.IntegerField(allow_null=True, required=False)
    template = serializers.CharField(max_length=m.TEMPLATE_MAX_LENGTH, required=False)


class StaffPostCreateRequestSerializer(_ContentWriteSerializer):
    site = _site()
    locale = _locale()
    excerpt = serializers.CharField(max_length=m.EXCERPT_MAX_LENGTH, allow_blank=True, required=False)
    cover = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.IntegerField(), required=False, max_length=50)
    published_at = _dt(required=False, allow_null=True)


class StaffPostUpdateRequestSerializer(_ContentWriteSerializer):
    version = serializers.IntegerField(min_value=1, help_text="The version this editor read (optimistic lock).")
    excerpt = serializers.CharField(max_length=m.EXCERPT_MAX_LENGTH, allow_blank=True, required=False)
    cover = serializers.CharField(max_length=m.MEDIA_REF_MAX_LENGTH, allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.IntegerField(), required=False, max_length=50)
    published_at = _dt(required=False, allow_null=True)


class StaffPagePageSerializer(_AnchorPage):
    items = StaffPageSerializer(many=True)


class StaffPostPageSerializer(_AnchorPage):
    items = StaffPostSerializer(many=True)


class TransitionRequestSerializer(serializers.Serializer):
    to = serializers.ChoiceField(choices=m.Status.choices)
    publish_at = _dt(required=False, allow_null=True, help_text="Required for 'scheduled'.")


class RevisionSerializer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=m.NOTE_MAX_LENGTH, allow_blank=True)
    created_by_id = serializers.CharField(max_length=m.USER_ID_MAX_LENGTH, allow_blank=True)
    created_at = _dt()
    is_live = serializers.BooleanField()
    is_scheduled = serializers.BooleanField()
    snapshot = ObjectField()


class RevisionPageSerializer(_AnchorPage):
    items = RevisionSerializer(many=True)


class PreviewTokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    expires_at = _dt()
    url = serializers.CharField(max_length=2000, allow_null=True)


class VariantRequestSerializer(serializers.Serializer):
    locale = _locale()
    machine_translate = serializers.BooleanField(default=False)


# ── Staff: tags, menus, redirects, block types ─────────────────────────────


class StaffTagSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    site = serializers.CharField(max_length=m.SITE_MAX_LENGTH, allow_blank=True)
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH)
    name = serializers.CharField(max_length=m.TAG_NAME_MAX_LENGTH)
    created_at = _dt()


class StaffTagCreateRequestSerializer(serializers.Serializer):
    site = _site()
    locale = _locale()
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH)
    name = serializers.CharField(max_length=m.TAG_NAME_MAX_LENGTH)


class StaffTagUpdateRequestSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=m.SLUG_MAX_LENGTH, required=False)
    name = serializers.CharField(max_length=m.TAG_NAME_MAX_LENGTH, required=False)


class StaffTagPageSerializer(_AnchorPage):
    items = StaffTagSerializer(many=True)


class MenuItemInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=m.MENU_LABEL_MAX_LENGTH)
    target_type = serializers.ChoiceField(choices=m.TargetType.choices)
    page = serializers.IntegerField(required=False, allow_null=True)
    post = serializers.IntegerField(required=False, allow_null=True)
    url = serializers.CharField(max_length=m.URL_MAX_LENGTH, required=False, allow_null=True, allow_blank=True)
    route = serializers.CharField(max_length=m.ROUTE_MAX_LENGTH, required=False, allow_null=True, allow_blank=True)
    route_params = ObjectField(required=False)
    new_tab = serializers.BooleanField(required=False, default=False)

    def get_fields(self):
        fields = super().get_fields()
        fields["children"] = MenuItemInputSerializer(many=True, required=False)
        return fields


class StaffMenuItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField(max_length=m.MENU_LABEL_MAX_LENGTH)
    target_type = serializers.ChoiceField(choices=m.TargetType.choices)
    page = serializers.IntegerField(allow_null=True)
    post = serializers.IntegerField(allow_null=True)
    url = serializers.CharField(max_length=m.URL_MAX_LENGTH, allow_null=True)
    route = serializers.CharField(max_length=m.ROUTE_MAX_LENGTH, allow_null=True)
    route_params = ObjectField()
    new_tab = serializers.BooleanField()

    def get_fields(self):
        fields = super().get_fields()
        fields["children"] = StaffMenuItemSerializer(many=True)
        return fields


class StaffMenuSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    site = serializers.CharField(max_length=m.SITE_MAX_LENGTH, allow_blank=True)
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    key = serializers.CharField(max_length=m.MENU_KEY_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True)
    items = StaffMenuItemSerializer(many=True)
    updated_at = _dt()


class StaffMenuCreateRequestSerializer(serializers.Serializer):
    site = _site()
    locale = _locale()
    key = serializers.CharField(max_length=m.MENU_KEY_MAX_LENGTH)
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True, default="")
    items = MenuItemInputSerializer(many=True, required=False)


class StaffMenuReplaceRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=m.TITLE_MAX_LENGTH, allow_blank=True, required=False)
    items = MenuItemInputSerializer(many=True)


class StaffMenuPageSerializer(_AnchorPage):
    items = StaffMenuSerializer(many=True)


class StaffRedirectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    site = serializers.CharField(max_length=m.SITE_MAX_LENGTH, allow_blank=True)
    locale = serializers.CharField(max_length=m.LOCALE_MAX_LENGTH)
    old_path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    new_path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    permanent = serializers.BooleanField()
    source = serializers.ChoiceField(choices=m.RedirectSource.choices)
    created_by_id = serializers.CharField(max_length=m.USER_ID_MAX_LENGTH, allow_blank=True)
    created_at = _dt()


class StaffRedirectCreateRequestSerializer(serializers.Serializer):
    site = _site()
    locale = _locale()
    old_path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    new_path = serializers.CharField(max_length=m.PATH_MAX_LENGTH)
    permanent = serializers.BooleanField(default=True)


class StaffRedirectPageSerializer(_AnchorPage):
    items = StaffRedirectSerializer(many=True)


class BlockTypeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=48)
    schema = ObjectField(help_text="JSON Schema of the block's data (pydantic model_json_schema).")


class BlockTypeListSerializer(serializers.Serializer):
    items = BlockTypeSerializer(many=True)
