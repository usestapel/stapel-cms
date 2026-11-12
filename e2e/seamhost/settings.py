"""A minimal host for the seam run: cms with the real cdn, forms, translate and core's sitemap.

Not part of the package. Its database and media live in the directory it is
run from: ``make seam`` runs it inside a fresh temporary directory and drives
``e2e/seam_run.py``.
"""
from pathlib import Path

DATA = Path.cwd()
SECRET_KEY = "seam-run-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "django.contrib.contenttypes", "django.contrib.auth", "django.contrib.sessions",
    "django.contrib.admin", "django.contrib.messages", "django.contrib.staticfiles",
    "stapel_core.django.apps.CommonDjangoConfig", "stapel_core.django.users", "stapel_core.django.taskstore",
    "rest_framework", "drf_spectacular",
    "stapel_cdn", "stapel_forms", "stapel_translate", "stapel_cms",
]
AUTH_USER_MODEL = "users.User"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(DATA / "db.sqlite3")}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
ROOT_URLCONF = "seamhost.urls"
STATIC_URL = "/static/"
MEDIA_ROOT = str(DATA / "media")
MEDIA_URL = "/media/"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STAPEL_BUS_BACKEND = "stapel_core.bus.backends.memory.MemoryBus"
STAPEL_COMM = {"OUTBOX_ENABLED": False, "ACTION_TRANSPORT": "inprocess", "VALIDATE_SCHEMAS": True}
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "stapel_core.django.openapi.schemas.PermissionAwareAutoSchema",
    "EXCEPTION_HANDLER": "stapel_core.django.api.errors.stapel_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
}
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                                                 "django.contrib.auth.context_processors.auth",
                                                 "django.contrib.messages.context_processors.messages"]}}]
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware",
              "django.contrib.auth.middleware.AuthenticationMiddleware",
              "django.contrib.messages.middleware.MessageMiddleware"]
STAPEL_CMS = {"LOCALES": ["en", "de"], "MACHINE_TRANSLATE": "translate.text"}
STAPEL_TRANSLATE = {"LLM_PROVIDER": "seamhost.mockllm.TaggingProvider", "LANGUAGES": ["en", "de"]}
STAPEL_CDN = {"ASSET_TYPES": ["cms"]}
STAPEL_SITEMAP = {"ORIGIN": "https://seam.example", "URL_TEMPLATE": "{origin}/{locale}{path}"}
