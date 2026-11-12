from django.urls import include, path
from stapel_core.django.sitemap.urls import get_sitemap_urls

urlpatterns = [
    path("cms/", include("stapel_cms.urls")),
    path("cdn/api/", include("stapel_cdn.urls")),
    path("forms/", include("stapel_forms.urls")),
    path("translate/", include("stapel_translate.urls")),
    *get_sitemap_urls(),
]
