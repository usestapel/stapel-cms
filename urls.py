"""Root URLconf for stapel-cms — v1 canon mount (api-versioning.md §2).

The host project mounts this module root:

    path("cms/", include("stapel_cms.urls"))   # -> /cms/api/v1/...
"""
from django.urls import include, path

from stapel_cms.urls_v1 import GATE_REGISTRY  # noqa: F401  (re-export)

urlpatterns = [
    path("api/v1/", include("stapel_cms.urls_v1")),
]
