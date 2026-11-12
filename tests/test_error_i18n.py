"""Localized error catalogs (``translations/errors.<lang>.json``) + reference.

The convention of stapel-profiles: the en canon is the registry
(``errors.py`` → ``docs/errors.json``); every target language ships a flat
``translations/errors.<lang>.json`` with the shared ``translations/.state.json``
provenance sidecar, and ``docs/errors.<lang>.md`` is the per-language error
reference. :func:`check_translation_catalogs` gates coverage, staleness,
placeholders and byte stability. Core-owned keys are core's to translate and
never copied here.

The strings are kept in :data:`_MACHINE` (``origin: llm``), so the catalog
regenerates deterministically without a live model; the 26 keys of 0.1.0
are the texts the @stapel/cms-react pair authored for its ru/es i18n.
Adding a language: append it to :data:`LANGUAGES`, add its table, regenerate.

Regenerate after adding/changing an error key or a translation:

    STAPEL_REGEN_ERROR_I18N=1 python -m pytest tests/test_error_i18n.py::test_regen

then commit ``translations/`` + ``docs/errors.<lang>.md``. Without the env
var the same module is the CI gate.
"""
import io
import os
import tomllib
from pathlib import Path

import pytest
from django.core.management import call_command
from stapel_core.i18n import (
    check_translation_catalogs,
    source_texts,
    summarize,
    translate_catalog,
)
from stapel_core.i18n.catalogs import load_catalog_file

REPO = Path(__file__).resolve().parent.parent
TRANSLATIONS = REPO / "translations"
DOCS = REPO / "docs"
THIS_PACKAGE = "stapel_cms"
LANGUAGES = ["en", "ru", "es"]
TARGET_LANGUAGES = [lang for lang in LANGUAGES if lang != "en"]

_MACHINE_RU = {
    "error.400.cms_block_type_unknown": "Неизвестный тип блока: {type}",
    "error.400.cms_blocks_invalid": "Блок содержимого заполнен неверно: {detail}",
    "error.400.cms_blocks_too_large": "На странице слишком много содержимого (не больше {max_blocks} блоков и {max_bytes} байт)",
    "error.400.cms_form_unknown": "Формы {form_id} не существует",
    "error.400.cms_locale_unknown": "Этот язык не включён",
    "error.400.cms_menu_invalid": "Меню заполнено неверно: {detail}",
    "error.400.cms_object_expected": "Это поле должно быть объектом",
    "error.400.cms_parent_invalid": "Сюда эту страницу поместить нельзя",
    "error.400.cms_path_reserved": "Этот адрес зарезервирован для блога",
    "error.400.cms_publish_at_invalid": "Выберите время публикации в будущем",
    "error.400.cms_redirect_invalid": "Перенаправление задано неверно",
    "error.400.cms_site_unknown": "Неизвестный сайт",
    "error.400.cms_slug_invalid": "Адрес может содержать только буквы, цифры и дефисы",
    "error.400.cms_tag_unknown": "Неизвестный тег",
    "error.400.cms_template_unknown": "Неизвестный шаблон страницы",
    "error.400.cms_tree_too_deep": "Страницы можно вкладывать не глубже {max_depth} уровней",
    "error.400.cms_url_unsafe": "Такую ссылку использовать нельзя",
    "error.404.cms_not_found": "Страница не найдена",
    "error.404.cms_preview_invalid": "Ссылка на предпросмотр недействительна или устарела",
    "error.404.cms_revision_not_found": "Версия не найдена",
    "error.409.cms_delete_published": "Опубликованное нельзя удалить — отправьте в архив",
    "error.409.cms_form_unpublished": "Сначала опубликуйте форму {form_id}, а затем страницу, которая её встраивает",
    "error.409.cms_path_taken": "Этот адрес уже занят другой страницей",
    "error.409.cms_slug_taken": "Этот адрес уже занят",
    "error.409.cms_transition_invalid": "Нельзя перейти из состояния {from} в {to}",
    "error.409.cms_variant_exists": "Версия на этом языке уже есть",
    "error.409.cms_version_conflict": "Кто-то сохранил это раньше вас; обновите, чтобы увидеть версию {current}",
    "error.503.cms_translation_unavailable": "Машинный перевод сейчас недоступен",
}

_MACHINE_ES = {
    "error.400.cms_block_type_unknown": "Tipo de bloque desconocido: {type}",
    "error.400.cms_blocks_invalid": "Un bloque de contenido no es válido: {detail}",
    "error.400.cms_blocks_too_large": "La página tiene demasiado contenido (como máximo {max_blocks} bloques y {max_bytes} bytes)",
    "error.400.cms_form_unknown": "No existe el formulario {form_id}",
    "error.400.cms_locale_unknown": "Este idioma no está habilitado",
    "error.400.cms_menu_invalid": "El menú no es válido: {detail}",
    "error.400.cms_object_expected": "Este campo debe ser un objeto",
    "error.400.cms_parent_invalid": "Esta página no se puede colocar ahí",
    "error.400.cms_path_reserved": "Esta dirección está reservada para el blog",
    "error.400.cms_publish_at_invalid": "Elige una hora de publicación en el futuro",
    "error.400.cms_redirect_invalid": "La redirección no es válida",
    "error.400.cms_site_unknown": "Sitio desconocido",
    "error.400.cms_slug_invalid": "La dirección solo puede contener letras, cifras y guiones",
    "error.400.cms_tag_unknown": "Etiqueta desconocida",
    "error.400.cms_template_unknown": "Plantilla de página desconocida",
    "error.400.cms_tree_too_deep": "Las páginas se pueden anidar como máximo {max_depth} niveles",
    "error.400.cms_url_unsafe": "Este enlace no está permitido",
    "error.404.cms_not_found": "Página no encontrada",
    "error.404.cms_preview_invalid": "Este enlace de vista previa no es válido o ha caducado",
    "error.404.cms_revision_not_found": "Revisión no encontrada",
    "error.409.cms_delete_published": "El contenido publicado no se puede eliminar; archívalo",
    "error.409.cms_form_unpublished": "Publica el formulario {form_id} antes que la página que lo incluye",
    "error.409.cms_path_taken": "Otra página ya usa esta dirección",
    "error.409.cms_slug_taken": "Esta dirección ya está ocupada",
    "error.409.cms_transition_invalid": "No se puede pasar de {from} a {to}",
    "error.409.cms_variant_exists": "Ya existe una versión en este idioma",
    "error.409.cms_version_conflict": "Otra persona guardó esto mientras tanto; recarga para ver la versión {current}",
    "error.503.cms_translation_unavailable": "La traducción automática no está disponible en este momento",
}

_MACHINE = {"ru": _MACHINE_RU, "es": _MACHINE_ES}


class _DictTranslator:
    """Offline translator seam — returns fixed machine translations by key."""

    def __init__(self, table):
        self._table = table

    def translate(self, entries, source_language, target_language):
        return {k: self._table[k] for k in entries if k in self._table}


def _regen(lang: str):
    return translate_catalog(
        "errors", lang, TRANSLATIONS,
        source_texts=source_texts("errors"),
        llm=True,
        translator=_DictTranslator(_MACHINE[lang]),
    )


def _owned() -> dict[str, str]:
    from stapel_core.i18n import owned_keys, source_owners

    return owned_keys(source_texts("errors"), source_owners("errors"), THIS_PACKAGE)


def test_regen():
    """Regenerate (env-gated) or assert every catalog is a no-op regen (drift)."""
    if os.environ.get("STAPEL_REGEN_ERROR_I18N"):
        for lang in TARGET_LANGUAGES:
            result = _regen(lang)
            assert not result.missing, f"{lang}: still missing: {result.missing}"
        for lang in LANGUAGES:
            call_command("generate_error_docs", "--lang", lang,
                         "--out", str(DOCS), "--translations", str(TRANSLATIONS),
                         stdout=io.StringIO())
        return

    for lang in TARGET_LANGUAGES:
        path = TRANSLATIONS / f"errors.{lang}.json"
        before = path.read_bytes()
        _regen(lang)
        assert path.read_bytes() == before, (
            f"errors.{lang}.json drifted — run "
            f"STAPEL_REGEN_ERROR_I18N=1 pytest tests/test_error_i18n.py::test_regen"
        )


def test_catalog_gate_green():
    """Missing / stale / params / byte-stability / foreign: all zero."""
    issues = check_translation_catalogs(
        "errors", TRANSLATIONS,
        source_texts=source_texts("errors"),
        languages=LANGUAGES,
        owner=THIS_PACKAGE,
    )
    errors, _warnings = summarize(issues)
    blocking = [i for i in issues if i.level == "error"]
    assert not blocking, "\n".join(f"[{i.code}/{i.language}] {i.message}" for i in blocking)
    assert errors == 0


def test_every_language_covers_every_code_in_errors_py():
    from stapel_cms.errors import STAPEL_CMS_ERRORS

    owned = _owned()
    assert set(owned) == set(STAPEL_CMS_ERRORS), (
        "the loader does not attribute this module's registry to it"
    )
    for lang in TARGET_LANGUAGES:
        catalog = load_catalog_file(TRANSLATIONS / f"errors.{lang}.json")
        missing = sorted(set(STAPEL_CMS_ERRORS) - set(catalog))
        assert not missing, f"{lang} catalog misses {missing}"
        empty = sorted(k for k, v in catalog.items() if not str(v).strip())
        assert not empty, f"{lang}: empty translation(s): {empty}"


@pytest.mark.parametrize("lang", TARGET_LANGUAGES)
def test_the_catalog_carries_nothing_but_owned_keys(lang):
    stray = sorted(set(load_catalog_file(TRANSLATIONS / f"errors.{lang}.json")) - set(_owned()))
    assert not stray, f"{lang}: not this module's keys: {stray}"


@pytest.mark.parametrize("lang", TARGET_LANGUAGES)
def test_translations_preserve_placeholders(lang):
    from stapel_core.i18n.domains import params_of

    canon = _owned()
    for key, text in load_catalog_file(TRANSLATIONS / f"errors.{lang}.json").items():
        assert set(params_of(text)) == set(params_of(canon[key])), f"{lang}: {key}"


def test_the_shipped_language_set_is_exactly_the_gated_one():
    shipped = {p.name for p in TRANSLATIONS.glob("errors.*.json")}
    assert shipped == {f"errors.{lang}.json" for lang in TARGET_LANGUAGES}


def test_error_reference_matches_a_fresh_regeneration(tmp_path):
    for lang in LANGUAGES:
        call_command("generate_error_docs", "--lang", lang, "--out", str(tmp_path),
                     "--translations", str(TRANSLATIONS), stdout=io.StringIO())
        assert (tmp_path / f"errors.{lang}.md").read_bytes() == \
            (DOCS / f"errors.{lang}.md").read_bytes(), (
                f"docs/errors.{lang}.md is stale — run "
                f"STAPEL_REGEN_ERROR_I18N=1 pytest tests/test_error_i18n.py::test_regen"
            )


def test_error_reference_has_no_en_fallback_rows():
    for lang in TARGET_LANGUAGES:
        assert "_(en)_" not in (DOCS / f"errors.{lang}.md").read_text(), (
            f"{lang} error reference has en-fallback rows — the catalog is incomplete"
        )


def test_the_wheel_ships_the_catalogue():
    """package-data must carry ``translations/*.json``, or no host reads it."""
    with open(REPO / "pyproject.toml", "rb") as handle:
        patterns = tomllib.load(handle)["tool"]["setuptools"]["package-data"]
    assert "translations/*.json" in patterns[THIS_PACKAGE]
