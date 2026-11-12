from django.urls import include, path

urlpatterns = [
    path("cms/", include("stapel_cms.urls")),
]

try:
    from stapel_core.django.sitemap.urls import get_sitemap_urls
except ImportError:  # a core without the sitemap aggregator
    pass
else:
    urlpatterns += get_sitemap_urls()
