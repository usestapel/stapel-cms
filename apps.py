from django.apps import AppConfig


class CmsConfig(AppConfig):
    name = "stapel_cms"
    label = "cms"
    verbose_name = "Public content: pages, blog, menus and SEO"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import actions  # noqa: F401
        from . import checks  # noqa: F401
        from . import errors  # noqa: F401
        from . import flows  # noqa: F401
        from . import functions  # noqa: F401

        from stapel_core.gdpr import gdpr_registry, register_gdpr_owner

        from .gdpr import OWNER, SUBJECT_TYPES, CmsGDPRProvider, erase_subject

        if not any(p.section == OWNER for p in gdpr_registry.providers):
            gdpr_registry.register(CmsGDPRProvider())
        register_gdpr_owner(OWNER, SUBJECT_TYPES, erase_subject)

        from .services.sitemaps import register_provider

        register_provider()
