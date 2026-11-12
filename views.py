"""DRF views for stapel-cms — thin over ``services``.

Public views admit anyone (``ANONYMOUS_ALLOWED``), take the site from the
request host and answer conditional requests (ETag / Last-Modified, 304).
Staff views refuse guests (``ANONYMOUS_DENIED``) and pass
:class:`CmsStaffPermission` (``STAFF_AUTHZ``).
"""
from __future__ import annotations

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.http import http_date, parse_http_date_safe
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions
from stapel_core.django.api.errors import StapelErrorResponse, StapelResponse
from stapel_core.django.api.permissions import ANONYMOUS_ALLOWED, ANONYMOUS_DENIED, IsStaffUser
from stapel_core.django.api.views import StapelAPIView
from stapel_core.flows import flow_step

from . import sitekeys
from .flows import AUTHOR, BLOG, READ, SITE
from .models import Kind, Menu, Page, Post, Redirect, Status, Tag
from .pagination import PostAnchorPagination, StaffAnchorPagination
from .presenters import get_public_presenter, get_staff_presenter
from .serializers import (
    BlockTypeListSerializer,
    PostArchiveResponseSerializer,
    PreviewTokenResponseSerializer,
    PublicMenuSerializer,
    PublicPostPageSerializer,
    PublicPostSerializer,
    PublicPostSummarySerializer,
    PublicTagListSerializer,
    ResolveResponseSerializer,
    RevisionPageSerializer,
    RevisionSerializer,
    StaffMenuCreateRequestSerializer,
    StaffMenuPageSerializer,
    StaffMenuReplaceRequestSerializer,
    StaffMenuSerializer,
    StaffPageCreateRequestSerializer,
    StaffPagePageSerializer,
    StaffPageSerializer,
    StaffPageUpdateRequestSerializer,
    StaffPostCreateRequestSerializer,
    StaffPostPageSerializer,
    StaffPostSerializer,
    StaffPostUpdateRequestSerializer,
    StaffRedirectCreateRequestSerializer,
    StaffRedirectPageSerializer,
    StaffRedirectSerializer,
    StaffTagCreateRequestSerializer,
    StaffTagPageSerializer,
    StaffTagSerializer,
    StaffTagUpdateRequestSerializer,
    TransitionRequestSerializer,
    VariantRequestSerializer,
)
from .services import CmsError, cache, content, feed, menus, preview, public, redirects, tags

PUBLIC_TAGS = ["CMS public"]
STAFF_TAGS = ["CMS staff"]

LOCALE_PARAMETER = OpenApiParameter(
    "locale", str, OpenApiParameter.QUERY, required=False,
    description="Requested locale; the fallback chain ends at DEFAULT_LOCALE.",
)
SITE_FILTER = OpenApiParameter("site", str, OpenApiParameter.QUERY, required=False, description="Site key.")
LOCALE_FILTER = OpenApiParameter("locale", str, OpenApiParameter.QUERY, required=False, description="Locale.")
STATUS_FILTER = OpenApiParameter(
    "status", str, OpenApiParameter.QUERY, required=False, many=True,
    enum=[value for value, _ in Status.choices], description="Filter by status (repeatable).",
)
Q_FILTER = OpenApiParameter("q", str, OpenApiParameter.QUERY, required=False, description="Title contains.")
PARENT_FILTER = OpenApiParameter(
    "parent", str, OpenApiParameter.QUERY, required=False, description="Parent page id, or 'root' for top level.",
)


def _anchor_parameters(paginator):
    return [
        OpenApiParameter("anchor", str, OpenApiParameter.QUERY, required=False,
                         description="Opaque anchor from next_anchor/prev_anchor (exclusive)."),
        OpenApiParameter("limit", int, OpenApiParameter.QUERY, required=False,
                         description=f"Page size, default {paginator.page_size}, max {paginator.max_page_size}."),
        OpenApiParameter("direction", str, OpenApiParameter.QUERY, required=False,
                         enum=["next", "prev"], description="Walk direction from the anchor."),
    ]


def _plain(data) -> dict:
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


class _CmsView(StapelAPIView):
    """Renders a service refusal as the fleet error envelope."""

    def handle_exception(self, exc):
        if isinstance(exc, CmsError):
            return StapelErrorResponse(exc.status, exc.key, exc.params)
        return super().handle_exception(exc)


class CmsStaffPermission(IsStaffUser):
    """Staff only; with ``STAFF_AUTHZ="model_perms"`` also the @access mandate."""

    METHOD_ACTIONS = {"GET": "view", "HEAD": "view", "OPTIONS": "view", "POST": "add",
                      "PUT": "change", "PATCH": "change", "DELETE": "delete"}

    def has_permission(self, request, view):
        from .conf import cms_settings

        if not super().has_permission(request, view):
            return False
        if getattr(request.user, "is_anonymous", False):
            return False
        if cms_settings.STAFF_AUTHZ != "model_perms":
            return True
        model = getattr(view, "cms_model", None)
        if model is None:
            return True
        action = getattr(view, "cms_action", None) or self.METHOD_ACTIONS.get(request.method, "change")
        return request.user.has_perm(f"cms.{action}_{model}")


class _StaffView(_CmsView):
    permission_classes = [CmsStaffPermission]
    stapel_anonymous_access = ANONYMOUS_DENIED
    cms_model: str | None = None
    cms_action: str | None = None


class _PublicView(_CmsView):
    permission_classes = [permissions.AllowAny]
    stapel_anonymous_access = ANONYMOUS_ALLOWED

    def _site(self, request) -> str:
        return sitekeys.for_request(request)

    def _cached(self, request, name: str, params: dict, compute):
        """``(data, last_modified)`` from the site cache, computing on a miss."""
        site = self._site(request)
        key = cache.body_key(site, name, params)
        hit = cache.get(key)
        if hit is None:
            data, last_modified = compute(site)
            hit = (_plain(data), last_modified.timestamp() if last_modified else None)
            cache.put(key, hit)
        return hit

    def _conditional(self, request, data, last_modified_ts, *, private: bool = False):
        from .conf import cms_settings

        etag = cache.etag_of(data)
        headers = {"ETag": etag}
        if private:
            headers["Cache-Control"] = "private, no-store"
        else:
            headers["Cache-Control"] = f"public, max-age={int(cms_settings.HTTP_MAX_AGE)}"
        if last_modified_ts is not None:
            headers["Last-Modified"] = http_date(int(last_modified_ts))
        inm = request.headers.get("If-None-Match")
        if inm:
            tags_sent = {t.strip().removeprefix("W/") for t in inm.split(",")}
            if "*" in tags_sent or etag in tags_sent:
                return StapelResponse(status=304, headers=headers)
        elif last_modified_ts is not None:
            since = parse_http_date_safe(request.headers.get("If-Modified-Since") or "")
            if since is not None and int(last_modified_ts) <= since:
                return StapelResponse(status=304, headers=headers)
        return StapelResponse(data, headers=headers)


# ── Public ─────────────────────────────────────────────────────────────────


@extend_schema(tags=PUBLIC_TAGS)
class ResolveView(_PublicView):
    """What lives at a path: a page, a post or a redirect."""

    response_serializer_class = ResolveResponseSerializer

    @extend_schema(
        operation_id="cms_public_resolve",
        parameters=[OpenApiParameter("path", str, OpenApiParameter.QUERY, required=True,
                                     description="The site path, e.g. /about/team."), LOCALE_PARAMETER],
        responses={200: ResolveResponseSerializer, 304: OpenApiResponse(description="Not modified")},
    )
    @flow_step(READ, order=1, note="Ask what lives at the visited path, in the visitor's language")
    def get(self, request):
        path = request.query_params.get("path", "/")
        locale = request.query_params.get("locale")

        def compute(site):
            result = public.resolve(site, locale, path)
            dto = get_public_presenter()().resolve(result)
            return self.get_response_serializer_class()(dto).data, result["last_modified"]

        data, ts = self._cached(request, "resolve", {"path": path, "locale": locale}, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class PublicPostListView(_PublicView):
    """The blog: latest published posts, newest first; by tag or month."""

    response_serializer_class = PublicPostSummarySerializer
    pagination_class = PostAnchorPagination

    @extend_schema(
        operation_id="cms_public_posts_list",
        parameters=[
            LOCALE_PARAMETER,
            OpenApiParameter("tag", str, OpenApiParameter.QUERY, required=False, description="Tag slug."),
            OpenApiParameter("year", int, OpenApiParameter.QUERY, required=False, description="Archive year."),
            OpenApiParameter("month", int, OpenApiParameter.QUERY, required=False, description="Archive month."),
            *_anchor_parameters(PostAnchorPagination),
        ],
        responses={200: PublicPostPageSerializer, 304: OpenApiResponse(description="Not modified")},
    )
    @flow_step(BLOG, order=1, note="Page through the latest posts, optionally by tag or month")
    def get(self, request):
        qp = request.query_params
        params = {k: qp.get(k) for k in ("locale", "tag", "year", "month", "anchor", "limit", "direction")}

        def compute(site):
            year = params["year"] if (params["year"] or "").isdigit() else None
            month = params["month"] if (params["month"] or "").isdigit() else None
            qs = public.posts_queryset(site, params["locale"], tag=params["tag"], year=year, month=month)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(qs, request, view=self)
            presenter = get_public_presenter()()
            items = [presenter.post_summary(row) for row in public.post_summaries(page)]
            data = paginator.page_envelope(self.get_response_serializer_class()(items, many=True).data)
            stamps = [p.last_published_at for p in page if p.last_published_at]
            return data, max(stamps) if stamps else None

        data, ts = self._cached(request, "posts", params, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class PublicPostDetailView(_PublicView):
    response_serializer_class = PublicPostSerializer

    @extend_schema(operation_id="cms_public_posts_retrieve", parameters=[LOCALE_PARAMETER],
                   responses={200: PublicPostSerializer, 304: OpenApiResponse(description="Not modified")})
    @flow_step(BLOG, order=2, note="Open one post")
    def get(self, request, slug):
        locale = request.query_params.get("locale")

        def compute(site):
            data = public.post_detail(site, locale, slug)
            dto = get_public_presenter()().post(data)
            return self.get_response_serializer_class()(dto).data, data["updated_at"]

        data, ts = self._cached(request, "post", {"slug": slug, "locale": locale}, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class PostArchiveView(_PublicView):
    response_serializer_class = PostArchiveResponseSerializer

    @extend_schema(operation_id="cms_public_post_archive", parameters=[LOCALE_PARAMETER],
                   responses={200: PostArchiveResponseSerializer, 304: OpenApiResponse(description="Not modified")})
    @flow_step(BLOG, order=3, note="See which months have posts (the date archive)")
    def get(self, request):
        locale = request.query_params.get("locale")

        def compute(site):
            dto = get_public_presenter()().archive(public.archive(site, locale))
            return self.get_response_serializer_class()(dto).data, None

        data, ts = self._cached(request, "archive", {"locale": locale}, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class PublicTagListView(_PublicView):
    response_serializer_class = PublicTagListSerializer

    @extend_schema(operation_id="cms_public_tags_list", parameters=[LOCALE_PARAMETER],
                   responses={200: PublicTagListSerializer, 304: OpenApiResponse(description="Not modified")})
    @flow_step(BLOG, order=4, note="See the tags that have published posts")
    def get(self, request):
        locale = request.query_params.get("locale")

        def compute(site):
            dto = get_public_presenter()().tags(public.tags(site, locale))
            return self.get_response_serializer_class()(dto).data, None

        data, ts = self._cached(request, "tags", {"locale": locale}, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class PublicMenuView(_PublicView):
    response_serializer_class = PublicMenuSerializer

    @extend_schema(operation_id="cms_public_menus_retrieve", parameters=[LOCALE_PARAMETER],
                   responses={200: PublicMenuSerializer, 304: OpenApiResponse(description="Not modified")})
    @flow_step(READ, order=2, note="Load the header and footer menus")
    def get(self, request, key):
        locale = request.query_params.get("locale")

        def compute(site):
            data = public.menu(site, locale, key)
            dto = get_public_presenter()().menu(data)
            return self.get_response_serializer_class()(dto).data, data["last_modified"]

        data, ts = self._cached(request, "menu", {"key": key, "locale": locale}, compute)
        return self._conditional(request, data, ts)


@extend_schema(tags=PUBLIC_TAGS)
class FeedView(_PublicView):
    """RSS 2.0 or Atom feed of the latest posts."""

    @extend_schema(
        operation_id="cms_public_feed",
        parameters=[LOCALE_PARAMETER, OpenApiParameter("type", str, OpenApiParameter.QUERY, required=False,
                                                       enum=["rss", "atom"], description="Feed type (default rss).")],
        responses={(200, "application/rss+xml"): OpenApiTypes.STR, (200, "application/atom+xml"): OpenApiTypes.STR},
    )
    @flow_step(BLOG, order=5, note="Subscribe to the RSS or Atom feed")
    def get(self, request):
        fmt = request.query_params.get("type") or "rss"
        locale = request.query_params.get("locale")
        site = self._site(request)
        origin = sitekeys.origin(site) or request.build_absolute_uri("/").rstrip("/")
        key = cache.body_key(site, "feed", {"format": fmt, "locale": locale, "origin": origin})
        hit = cache.get(key)
        if hit is None:
            hit = feed.render(site, locale, fmt, origin=origin)
            cache.put(key, hit)
        content_type, body = hit
        response = HttpResponse(body, content_type=content_type)
        response["ETag"] = cache.etag_of(body)
        return response


@extend_schema(tags=PUBLIC_TAGS)
class PreviewView(_PublicView):
    """A draft's working copy, unlocked by a signed preview token."""

    response_serializer_class = ResolveResponseSerializer

    @extend_schema(
        operation_id="cms_public_preview",
        parameters=[OpenApiParameter("token", str, OpenApiParameter.QUERY, required=True,
                                     description="Token from staff preview-token.")],
        responses={200: ResolveResponseSerializer},
    )
    @flow_step(AUTHOR, order=3, note="Open the draft through the signed preview link")
    def get(self, request):
        kind, obj_id = preview.read(request.query_params.get("token", ""))
        result = public.preview(kind, obj_id)
        dto = get_public_presenter()().resolve(result)
        data = _plain(self.get_response_serializer_class()(dto).data)
        return self._conditional(request, data, None, private=True)


# ── Staff: pages and posts ─────────────────────────────────────────────────


def _content_queryset(model, request):
    qp = request.query_params
    qs = model.objects.select_related("live_revision", "scheduled_revision")
    if "site" in qp:
        qs = qs.filter(site=qp.get("site", ""))
    if qp.get("locale"):
        qs = qs.filter(locale=qp["locale"])
    statuses = [s for s in qp.getlist("status") if s in Status.values]
    if statuses:
        qs = qs.filter(status__in=statuses)
    if qp.get("q"):
        qs = qs.filter(title__icontains=qp["q"][:100])
    parent = qp.get("parent")
    if model is Page and parent:
        qs = qs.filter(parent__isnull=True) if parent == "root" else (
            qs.filter(parent_id=int(parent)) if parent.isdigit() else qs.none())
    if model is Post:
        qs = qs.prefetch_related("tags")
    return qs


class _ContentMixin:
    kind: str = ""

    def _one(self, obj, status=200):
        return self.serialized_response(get_staff_presenter()().content(obj), status=status)

    def _list(self, request):
        model = Page if self.kind == Kind.PAGE else Post
        paginator = StaffAnchorPagination()
        page = paginator.paginate_queryset(_content_queryset(model, request), request, view=self)
        presenter = get_staff_presenter()()
        data = self.get_response_serializer_class()([presenter.content(o) for o in page], many=True).data
        return paginator.get_paginated_response(data)

    def _revisions(self, request, obj_id):
        obj = content.get(self.kind, obj_id)
        paginator = StaffAnchorPagination()
        page = paginator.paginate_queryset(content.revisions(self.kind, obj_id), request, view=self)
        presenter = get_staff_presenter()()
        data = RevisionSerializer([presenter.revision(r, obj) for r in page], many=True).data
        return paginator.get_paginated_response(data)


LIST_PARAMS = [SITE_FILTER, LOCALE_FILTER, STATUS_FILTER, Q_FILTER, *_anchor_parameters(StaffAnchorPagination)]


@extend_schema(tags=STAFF_TAGS)
class StaffPageListView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.PAGE, "page"
    request_serializer_class = StaffPageCreateRequestSerializer
    response_serializer_class = StaffPageSerializer

    @extend_schema(operation_id="cms_staff_pages_list", parameters=[*LIST_PARAMS, PARENT_FILTER],
                   responses={200: StaffPagePageSerializer})
    @flow_step(AUTHOR, order=1, note="Browse the pages of a site and locale")
    def get(self, request):
        return self._list(request)

    @extend_schema(operation_id="cms_staff_pages_create", request=StaffPageCreateRequestSerializer,
                   responses={201: StaffPageSerializer})
    @flow_step(AUTHOR, order=2, note="Create a draft page from typed blocks")
    def post(self, request):
        return self._one(content.create(self.kind, request.user, self.validated_request_data(request)), 201)


@extend_schema(tags=STAFF_TAGS)
class StaffPageDetailView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.PAGE, "page"
    request_serializer_class = StaffPageUpdateRequestSerializer
    response_serializer_class = StaffPageSerializer

    @extend_schema(operation_id="cms_staff_pages_retrieve", responses={200: StaffPageSerializer})
    @flow_step(AUTHOR, order=4, note="Open a page's working copy")
    def get(self, request, obj_id):
        return self._one(content.get(self.kind, obj_id))

    @extend_schema(operation_id="cms_staff_pages_update", request=StaffPageUpdateRequestSerializer,
                   responses={200: StaffPageSerializer})
    @flow_step(AUTHOR, order=5, note="Save edits under the optimistic lock; a moved page leaves a redirect")
    def patch(self, request, obj_id):
        data = self.validated_request_data(request, partial=True)
        return self._one(content.update(self.kind, obj_id, request.user, data))

    @extend_schema(operation_id="cms_staff_pages_destroy", responses={204: None})
    @flow_step(AUTHOR, order=6, note="Delete a page that was never published")
    def delete(self, request, obj_id):
        content.delete(self.kind, obj_id)
        return StapelResponse(status=204)


@extend_schema(tags=STAFF_TAGS)
class StaffPageTransitionView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.PAGE, "page", "change"
    request_serializer_class = TransitionRequestSerializer
    response_serializer_class = StaffPageSerializer

    @extend_schema(operation_id="cms_staff_pages_transition", request=TransitionRequestSerializer,
                   responses={200: StaffPageSerializer})
    @flow_step(AUTHOR, order=7, note="Publish now, schedule, cancel the schedule, archive or reopen")
    def post(self, request, obj_id):
        data = self.validated_request_data(request)
        return self._one(content.transition(self.kind, obj_id, request.user, data["to"], data.get("publish_at")))


@extend_schema(tags=STAFF_TAGS)
class StaffPageRevisionsView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.PAGE, "page"
    response_serializer_class = RevisionSerializer

    @extend_schema(operation_id="cms_staff_pages_revisions_list",
                   parameters=_anchor_parameters(StaffAnchorPagination), responses={200: RevisionPageSerializer})
    @flow_step(AUTHOR, order=8, note="Look through the page's revisions")
    def get(self, request, obj_id):
        return self._revisions(request, obj_id)


@extend_schema(tags=STAFF_TAGS)
class StaffPageRestoreView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.PAGE, "page", "change"
    response_serializer_class = StaffPageSerializer

    @extend_schema(operation_id="cms_staff_pages_revisions_restore", request=None,
                   responses={200: StaffPageSerializer})
    @flow_step(AUTHOR, order=9, note="Restore an older revision into the working copy")
    def post(self, request, obj_id, number):
        return self._one(content.restore(self.kind, obj_id, number, request.user))


@extend_schema(tags=STAFF_TAGS)
class StaffPagePreviewTokenView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.PAGE, "page", "view"
    response_serializer_class = PreviewTokenResponseSerializer

    @extend_schema(operation_id="cms_staff_pages_preview_token", request=None,
                   responses={200: PreviewTokenResponseSerializer})
    @flow_step(AUTHOR, order=10, note="Mint a signed preview link for the working copy")
    def post(self, request, obj_id):
        content.get(self.kind, obj_id)
        return self.serialized_response(get_staff_presenter()().preview_token(preview.mint(self.kind, obj_id)))


@extend_schema(tags=STAFF_TAGS)
class StaffPageVariantView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.PAGE, "page", "add"
    request_serializer_class = VariantRequestSerializer
    response_serializer_class = StaffPageSerializer

    @extend_schema(operation_id="cms_staff_pages_variant_create", request=VariantRequestSerializer,
                   responses={201: StaffPageSerializer})
    @flow_step(AUTHOR, order=11, note="Copy the page into another language, optionally machine-translated")
    def post(self, request, obj_id):
        data = self.validated_request_data(request)
        obj = content.create_variant(self.kind, obj_id, request.user, data["locale"],
                                     bool(data.get("machine_translate", False)))
        return self._one(obj, 201)


@extend_schema(tags=STAFF_TAGS)
class StaffPostListView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.POST, "post"
    request_serializer_class = StaffPostCreateRequestSerializer
    response_serializer_class = StaffPostSerializer

    @extend_schema(operation_id="cms_staff_posts_list", parameters=LIST_PARAMS,
                   responses={200: StaffPostPageSerializer})
    @flow_step(AUTHOR, order=12, note="Browse the posts of a site and locale")
    def get(self, request):
        return self._list(request)

    @extend_schema(operation_id="cms_staff_posts_create", request=StaffPostCreateRequestSerializer,
                   responses={201: StaffPostSerializer})
    @flow_step(AUTHOR, order=13, note="Write a draft post")
    def post(self, request):
        return self._one(content.create(self.kind, request.user, self.validated_request_data(request)), 201)


@extend_schema(tags=STAFF_TAGS)
class StaffPostDetailView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.POST, "post"
    request_serializer_class = StaffPostUpdateRequestSerializer
    response_serializer_class = StaffPostSerializer

    @extend_schema(operation_id="cms_staff_posts_retrieve", responses={200: StaffPostSerializer})
    @flow_step(AUTHOR, order=14, note="Open a post's working copy")
    def get(self, request, obj_id):
        return self._one(content.get(self.kind, obj_id))

    @extend_schema(operation_id="cms_staff_posts_update", request=StaffPostUpdateRequestSerializer,
                   responses={200: StaffPostSerializer})
    @flow_step(AUTHOR, order=15, note="Save a post's edits under the optimistic lock")
    def patch(self, request, obj_id):
        data = self.validated_request_data(request, partial=True)
        return self._one(content.update(self.kind, obj_id, request.user, data))

    @extend_schema(operation_id="cms_staff_posts_destroy", responses={204: None})
    @flow_step(AUTHOR, order=16, note="Delete a post that was never published")
    def delete(self, request, obj_id):
        content.delete(self.kind, obj_id)
        return StapelResponse(status=204)


@extend_schema(tags=STAFF_TAGS)
class StaffPostTransitionView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.POST, "post", "change"
    request_serializer_class = TransitionRequestSerializer
    response_serializer_class = StaffPostSerializer

    @extend_schema(operation_id="cms_staff_posts_transition", request=TransitionRequestSerializer,
                   responses={200: StaffPostSerializer})
    @flow_step(AUTHOR, order=17, note="Publish, schedule or archive a post")
    def post(self, request, obj_id):
        data = self.validated_request_data(request)
        return self._one(content.transition(self.kind, obj_id, request.user, data["to"], data.get("publish_at")))


@extend_schema(tags=STAFF_TAGS)
class StaffPostRevisionsView(_ContentMixin, _StaffView):
    kind, cms_model = Kind.POST, "post"
    response_serializer_class = RevisionSerializer

    @extend_schema(operation_id="cms_staff_posts_revisions_list",
                   parameters=_anchor_parameters(StaffAnchorPagination), responses={200: RevisionPageSerializer})
    @flow_step(AUTHOR, order=18, note="Look through the post's revisions")
    def get(self, request, obj_id):
        return self._revisions(request, obj_id)


@extend_schema(tags=STAFF_TAGS)
class StaffPostRestoreView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.POST, "post", "change"
    response_serializer_class = StaffPostSerializer

    @extend_schema(operation_id="cms_staff_posts_revisions_restore", request=None,
                   responses={200: StaffPostSerializer})
    @flow_step(AUTHOR, order=19, note="Restore an older revision of the post")
    def post(self, request, obj_id, number):
        return self._one(content.restore(self.kind, obj_id, number, request.user))


@extend_schema(tags=STAFF_TAGS)
class StaffPostPreviewTokenView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.POST, "post", "view"
    response_serializer_class = PreviewTokenResponseSerializer

    @extend_schema(operation_id="cms_staff_posts_preview_token", request=None,
                   responses={200: PreviewTokenResponseSerializer})
    @flow_step(AUTHOR, order=22, note="Mint a signed preview link for a post")
    def post(self, request, obj_id):
        content.get(self.kind, obj_id)
        return self.serialized_response(get_staff_presenter()().preview_token(preview.mint(self.kind, obj_id)))


@extend_schema(tags=STAFF_TAGS)
class StaffPostVariantView(_ContentMixin, _StaffView):
    kind, cms_model, cms_action = Kind.POST, "post", "add"
    request_serializer_class = VariantRequestSerializer
    response_serializer_class = StaffPostSerializer

    @extend_schema(operation_id="cms_staff_posts_variant_create", request=VariantRequestSerializer,
                   responses={201: StaffPostSerializer})
    @flow_step(AUTHOR, order=23, note="Copy the post into another language")
    def post(self, request, obj_id):
        data = self.validated_request_data(request)
        obj = content.create_variant(self.kind, obj_id, request.user, data["locale"],
                                     bool(data.get("machine_translate", False)))
        return self._one(obj, 201)


# ── Staff: tags, menus, redirects, block types ─────────────────────────────


def _scoped(qs, request):
    qp = request.query_params
    if "site" in qp:
        qs = qs.filter(site=qp.get("site", ""))
    if qp.get("locale"):
        qs = qs.filter(locale=qp["locale"])
    return qs


SCOPE_PARAMS = [SITE_FILTER, LOCALE_FILTER, *_anchor_parameters(StaffAnchorPagination)]


@extend_schema(tags=STAFF_TAGS)
class StaffTagListView(_StaffView):
    cms_model = "tag"
    request_serializer_class = StaffTagCreateRequestSerializer
    response_serializer_class = StaffTagSerializer

    @extend_schema(operation_id="cms_staff_tags_list", parameters=SCOPE_PARAMS,
                   responses={200: StaffTagPageSerializer})
    @flow_step(SITE, order=1, note="Browse the blog tags")
    def get(self, request):
        paginator = StaffAnchorPagination()
        page = paginator.paginate_queryset(_scoped(Tag.objects.all(), request), request, view=self)
        presenter = get_staff_presenter()()
        return paginator.get_paginated_response(
            self.get_response_serializer_class()([presenter.tag(t) for t in page], many=True).data)

    @extend_schema(operation_id="cms_staff_tags_create", request=StaffTagCreateRequestSerializer,
                   responses={201: StaffTagSerializer})
    @flow_step(SITE, order=2, note="Add a tag")
    def post(self, request):
        tag = tags.create(self.validated_request_data(request))
        return self.serialized_response(get_staff_presenter()().tag(tag), status=201)


@extend_schema(tags=STAFF_TAGS)
class StaffTagDetailView(_StaffView):
    cms_model = "tag"
    request_serializer_class = StaffTagUpdateRequestSerializer
    response_serializer_class = StaffTagSerializer

    @extend_schema(operation_id="cms_staff_tags_update", request=StaffTagUpdateRequestSerializer,
                   responses={200: StaffTagSerializer})
    @flow_step(SITE, order=3, note="Rename a tag")
    def patch(self, request, tag_id):
        tag = tags.update(tag_id, self.validated_request_data(request, partial=True))
        return self.serialized_response(get_staff_presenter()().tag(tag))

    @extend_schema(operation_id="cms_staff_tags_destroy", responses={204: None})
    @flow_step(SITE, order=4, note="Remove a tag")
    def delete(self, request, tag_id):
        tags.delete(tag_id)
        return StapelResponse(status=204)


@extend_schema(tags=STAFF_TAGS)
class StaffMenuListView(_StaffView):
    cms_model = "menu"
    request_serializer_class = StaffMenuCreateRequestSerializer
    response_serializer_class = StaffMenuSerializer

    @extend_schema(operation_id="cms_staff_menus_list", parameters=SCOPE_PARAMS,
                   responses={200: StaffMenuPageSerializer})
    @flow_step(SITE, order=5, note="Browse the menus")
    def get(self, request):
        paginator = StaffAnchorPagination()
        page = paginator.paginate_queryset(_scoped(Menu.objects.all(), request), request, view=self)
        presenter = get_staff_presenter()()
        return paginator.get_paginated_response(
            self.get_response_serializer_class()([presenter.menu(m) for m in page], many=True).data)

    @extend_schema(operation_id="cms_staff_menus_create", request=StaffMenuCreateRequestSerializer,
                   responses={201: StaffMenuSerializer})
    @flow_step(SITE, order=6, note="Create a menu (header, footer)")
    def post(self, request):
        menu = menus.create(self.validated_request_data(request))
        return self.serialized_response(get_staff_presenter()().menu(menu), status=201)


@extend_schema(tags=STAFF_TAGS)
class StaffMenuDetailView(_StaffView):
    cms_model = "menu"
    request_serializer_class = StaffMenuReplaceRequestSerializer
    response_serializer_class = StaffMenuSerializer

    @extend_schema(operation_id="cms_staff_menus_retrieve", responses={200: StaffMenuSerializer})
    @flow_step(SITE, order=7, note="Open a menu")
    def get(self, request, menu_id):
        return self.serialized_response(get_staff_presenter()().menu(menus.get(menu_id)))

    @extend_schema(operation_id="cms_staff_menus_replace", request=StaffMenuReplaceRequestSerializer,
                   responses={200: StaffMenuSerializer})
    @flow_step(SITE, order=8, note="Replace the menu's item tree")
    def put(self, request, menu_id):
        menu = menus.replace(menu_id, self.validated_request_data(request))
        return self.serialized_response(get_staff_presenter()().menu(menu))

    @extend_schema(operation_id="cms_staff_menus_destroy", responses={204: None})
    @flow_step(SITE, order=9, note="Delete a menu")
    def delete(self, request, menu_id):
        menus.delete(menu_id)
        return StapelResponse(status=204)


@extend_schema(tags=STAFF_TAGS)
class StaffRedirectListView(_StaffView):
    cms_model = "redirect"
    request_serializer_class = StaffRedirectCreateRequestSerializer
    response_serializer_class = StaffRedirectSerializer

    @extend_schema(operation_id="cms_staff_redirects_list", parameters=SCOPE_PARAMS,
                   responses={200: StaffRedirectPageSerializer})
    @flow_step(SITE, order=11, note="Browse redirects, automatic and manual")
    def get(self, request):
        paginator = StaffAnchorPagination()
        page = paginator.paginate_queryset(_scoped(Redirect.objects.all(), request), request, view=self)
        presenter = get_staff_presenter()()
        return paginator.get_paginated_response(
            self.get_response_serializer_class()([presenter.redirect(r) for r in page], many=True).data)

    @extend_schema(operation_id="cms_staff_redirects_create", request=StaffRedirectCreateRequestSerializer,
                   responses={201: StaffRedirectSerializer})
    @flow_step(SITE, order=12, note="Add a manual redirect")
    def post(self, request):
        redirect = redirects.create(request.user, self.validated_request_data(request))
        return self.serialized_response(get_staff_presenter()().redirect(redirect), status=201)


@extend_schema(tags=STAFF_TAGS)
class StaffRedirectDetailView(_StaffView):
    cms_model = "redirect"

    @extend_schema(operation_id="cms_staff_redirects_destroy", responses={204: None})
    @flow_step(SITE, order=13, note="Remove a redirect")
    def delete(self, request, redirect_id):
        redirects.delete(redirect_id)
        return StapelResponse(status=204)


@extend_schema(tags=STAFF_TAGS)
class BlockTypesView(_StaffView):
    """Every registered block type with its data JSON Schema (for the editor)."""

    response_serializer_class = BlockTypeListSerializer

    @extend_schema(operation_id="cms_staff_block_types", responses={200: BlockTypeListSerializer})
    @flow_step(AUTHOR, order=0, note="Load the block types the editor offers")
    def get(self, request):
        from .blocks import block_type_schemas

        return self.serialized_response(get_staff_presenter()().block_types(block_type_schemas()))
