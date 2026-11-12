"""Single-module Django settings shared by the test suite and contract emission.

One copy, so the harness that emits ``docs/schema.json`` and the tests that
prove it can never drift in INSTALLED_APPS or comm config. The production
``REST_FRAMEWORK`` (exception handler, schema class) is used by both: the
error envelope the tests assert is the one a host serves.
"""
from __future__ import annotations


def settings_kwargs(
    *,
    root_urlconf: str = "stapel_cms.tests.urls",
    contract: bool = False,
    neighbours: bool = False,
) -> dict:
    """``neighbours=True`` (the test suite) also installs whichever neighbour
    modules cms reaches by Function name are importable (stapel-forms,
    stapel-translate), so the seams are proved against the real providers.
    Contract emission never installs them: the contract is cms's alone."""
    rest_framework = {
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_SCHEMA_CLASS": "stapel_core.django.openapi.schemas.PermissionAwareAutoSchema",
        "EXCEPTION_HANDLER": "stapel_core.django.api.errors.stapel_exception_handler",
    }
    if contract:
        rest_framework.update({
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "stapel_core.django.jwt.authentication.JWTCookieAuthentication",
            ],
            "DEFAULT_PERMISSION_CLASSES": [
                "stapel_core.django.api.permissions.IsServiceRequest",
                "stapel_core.django.api.permissions.IsSuperUser",
            ],
            "DEFAULT_RENDERER_CLASSES": [
                "rest_framework.renderers.JSONRenderer",
                "rest_framework.renderers.BrowsableAPIRenderer",
            ],
        })
    return dict(
        SECRET_KEY="test-secret-key-not-for-production",
        DEBUG=False,
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "django.contrib.admin",
            "django.contrib.messages",
            "stapel_core.django.apps.CommonDjangoConfig",
            "stapel_core.django.users",
            "rest_framework",
            "drf_spectacular",
            "stapel_cms",
            *(_neighbour_apps() if neighbours and not contract else []),
        ],
        AUTH_USER_MODEL="users.User",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
        ROOT_URLCONF=root_urlconf,
        ALLOWED_HOSTS=["*"],
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
        STAPEL_BUS_BACKEND="stapel_core.bus.backends.memory.MemoryBus",
        STAPEL_COMM={
            "OUTBOX_ENABLED": False,
            "ACTION_TRANSPORT": "inprocess",
            "VALIDATE_SCHEMAS": True,
        },
        STAPEL_CMS={"LOCALES": ["en", "de"]},
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]},
        }],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        MIGRATION_MODULES={"users": None},
        REST_FRAMEWORK=rest_framework,
    )


def _neighbour_apps() -> list[str]:
    from importlib.util import find_spec

    apps = []
    if find_spec("stapel_translate") is not None:
        apps += ["stapel_core.django.taskstore", "stapel_translate"]
    if find_spec("stapel_forms") is not None:
        apps.append("stapel_forms")
    return apps


#: Forced on drf-spectacular's singleton so a single-module instance derives
#: the same operation ids as a multi-module aggregate.
CODEGEN_SCHEMA_PATH_PREFIX = "/"


def enum_name_overrides() -> dict:
    """Stable enum component names (stapel-schema-lint SCH004)."""
    from stapel_cms.models import RedirectSource, Status, TargetType

    return {
        "CmsStatusEnum": Status,
        "CmsResolveKindEnum": [("page", "page"), ("post", "post"), ("redirect", "redirect")],
        "CmsMenuTargetEnum": TargetType,
        "CmsRedirectSourceEnum": RedirectSource,
    }
