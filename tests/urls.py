from django.urls import include, path

urlpatterns = [
    path("cms/", include("stapel_cms.urls")),
]
