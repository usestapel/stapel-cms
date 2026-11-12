"""v1 URL set — paths here are relative to the ``api/v1/`` mount contributed
by the root ``urls.py`` (api-versioning.md §2). Plain paths, no router.

``BLOG_ENABLED=False`` unmounts every post, tag and feed route.
"""
from typing import NamedTuple

from django.urls import path

from . import views as v
from .conf import cms_settings

ID = "<int:obj_id>"

CORE_PATTERNS = [
    path("public/resolve/", v.ResolveView.as_view(), name="cms-public-resolve"),
    path("public/menus/<str:key>/", v.PublicMenuView.as_view(), name="cms-public-menu"),
    path("public/preview/", v.PreviewView.as_view(), name="cms-public-preview"),
    path("staff/block-types/", v.BlockTypesView.as_view(), name="cms-staff-block-types"),
    path("staff/pages/", v.StaffPageListView.as_view(), name="cms-staff-pages"),
    path(f"staff/pages/{ID}/", v.StaffPageDetailView.as_view(), name="cms-staff-page"),
    path(f"staff/pages/{ID}/transition/", v.StaffPageTransitionView.as_view(), name="cms-staff-page-transition"),
    path(f"staff/pages/{ID}/revisions/", v.StaffPageRevisionsView.as_view(), name="cms-staff-page-revisions"),
    path(f"staff/pages/{ID}/revisions/<int:number>/restore/", v.StaffPageRestoreView.as_view(),
         name="cms-staff-page-restore"),
    path(f"staff/pages/{ID}/preview-token/", v.StaffPagePreviewTokenView.as_view(),
         name="cms-staff-page-preview-token"),
    path(f"staff/pages/{ID}/variants/", v.StaffPageVariantView.as_view(), name="cms-staff-page-variants"),
    path("staff/menus/", v.StaffMenuListView.as_view(), name="cms-staff-menus"),
    path("staff/menus/<int:menu_id>/", v.StaffMenuDetailView.as_view(), name="cms-staff-menu"),
    path("staff/redirects/", v.StaffRedirectListView.as_view(), name="cms-staff-redirects"),
    path("staff/redirects/<int:redirect_id>/", v.StaffRedirectDetailView.as_view(), name="cms-staff-redirect"),
]

BLOG_PATTERNS = [
    path("public/posts/", v.PublicPostListView.as_view(), name="cms-public-posts"),
    path("public/posts/<str:slug>/", v.PublicPostDetailView.as_view(), name="cms-public-post"),
    path("public/post-archive/", v.PostArchiveView.as_view(), name="cms-public-post-archive"),
    path("public/tags/", v.PublicTagListView.as_view(), name="cms-public-tags"),
    path("public/feed/", v.FeedView.as_view(), name="cms-public-feed"),
    path("staff/posts/", v.StaffPostListView.as_view(), name="cms-staff-posts"),
    path(f"staff/posts/{ID}/", v.StaffPostDetailView.as_view(), name="cms-staff-post"),
    path(f"staff/posts/{ID}/transition/", v.StaffPostTransitionView.as_view(), name="cms-staff-post-transition"),
    path(f"staff/posts/{ID}/revisions/", v.StaffPostRevisionsView.as_view(), name="cms-staff-post-revisions"),
    path(f"staff/posts/{ID}/revisions/<int:number>/restore/", v.StaffPostRestoreView.as_view(),
         name="cms-staff-post-restore"),
    path(f"staff/posts/{ID}/preview-token/", v.StaffPostPreviewTokenView.as_view(),
         name="cms-staff-post-preview-token"),
    path(f"staff/posts/{ID}/variants/", v.StaffPostVariantView.as_view(), name="cms-staff-post-variants"),
    path("staff/tags/", v.StaffTagListView.as_view(), name="cms-staff-tags"),
    path("staff/tags/<int:tag_id>/", v.StaffTagDetailView.as_view(), name="cms-staff-tag"),
]


class GateEntry(NamedTuple):
    """One gated URL block: which flags gate which url patterns."""

    name: str
    flags: tuple
    patterns: tuple


GATE_REGISTRY: dict = {
    "cms.core": GateEntry("cms.core", (), tuple(CORE_PATTERNS)),
    "cms.blog": GateEntry("cms.blog", ("BLOG_ENABLED",), tuple(BLOG_PATTERNS)),
}

urlpatterns = list(CORE_PATTERNS)
if cms_settings.BLOG_ENABLED:
    urlpatterns += BLOG_PATTERNS
