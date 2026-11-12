from django.urls import include, path
from stapel_core.django.sitemap.urls import get_sitemap_urls

urlpatterns = [path("cms/", include("stapel_cms.urls")), *get_sitemap_urls()]
