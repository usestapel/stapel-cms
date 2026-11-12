"""System checks: each fires on its defect and is silent on the default."""
import pytest
from django.core import checks

from stapel_cms import checks as cms_checks

pytestmark = pytest.mark.django_db


def _ids(findings):
    return {f.id for f in findings}


def test_defaults_are_clean_of_errors():
    errors = [f for f in checks.run_checks() if f.level >= checks.ERROR and f.id.startswith("stapel_cms")]
    assert errors == []


@pytest.mark.parametrize("override,check,finding", [
    ({"BLOCK_TYPES": {"x": "stapel_cms.tests.custom_blocks.NotAModel"}}, "check_block_types", "stapel_cms.E001"),
    ({"BLOCK_TYPES": {"x": "no.such.Model"}}, "check_block_types", "stapel_cms.E001"),
    ({"BLOCK_TYPES": {"Bad": "stapel_cms.blocks.HeroBlock"}}, "check_block_types", "stapel_cms.E001"),
    ({"STAFF_AUTHZ": "everyone"}, "check_settings", "stapel_cms.E002"),
    ({"LOCALES": ["de"]}, "check_settings", "stapel_cms.E003"),
    ({"LOCALE_FALLBACKS": {"en": ["fr"]}}, "check_settings", "stapel_cms.E003"),
    ({"PAGE_TEMPLATES": []}, "check_settings", "stapel_cms.E004"),
    ({"EMBED_HOSTS": ["https://www.youtube.com/"]}, "check_settings", "stapel_cms.E005"),
    ({"MACHINE_TRANSLATE": "nobody.translates"}, "check_integrations", "stapel_cms.W001"),
])
def test_each_check_fires(settings, override, check, finding):
    assert finding not in _ids(getattr(cms_checks, check)(None))
    settings.STAPEL_CMS = {**settings.STAPEL_CMS, **override}
    assert finding in _ids(getattr(cms_checks, check)(None))


def test_locmem_cache_warns_outside_debug(settings):
    assert "stapel_cms.W002" in _ids(cms_checks.check_integrations(None))
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                                   "LOCATION": "redis://localhost:6379"}}
    assert "stapel_cms.W002" not in _ids(cms_checks.check_integrations(None))


def test_with_a_site_registry(settings):
    settings.STAPEL_SITES = {"sites": [{"host": "shop.example", "brand": {"key": "acme", "name": "Acme"}}]}
    errors = [f for f in checks.run_checks() if f.level >= checks.ERROR and f.id.startswith("stapel_cms")]
    assert errors == []
