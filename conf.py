"""Settings namespace for stapel-cms.

All configuration is read through ``cms_settings`` (lazily, at call time).
Resolution order per key: ``settings.STAPEL_CMS`` dict -> flat Django setting
of the same name -> environment variable -> default below.

``BLOCK_TYPES`` is a MERGE registry over the built-in block types
(``blocks.BUILTIN_BLOCK_TYPES``): ``{"<type>": "dotted.path.Model" | None}``,
``None`` removes a built-in. Every other key replaces its default.
"""
from stapel_core.conf import AppSettings

#: Hosts an ``embed`` block may point at (exact host match, https only).
DEFAULT_EMBED_HOSTS = [
    "www.youtube.com",
    "youtube.com",
    "www.youtube-nocookie.com",
    "player.vimeo.com",
    "vimeo.com",
    "www.google.com",
    "maps.google.com",
]

#: AppSettings-shaped literal dict: a top-level DEFAULTS lets the
#: capabilities.json emitter introspect axis keys/kinds.
DEFAULTS = {
    # Axis: True mounts the blog (posts, tags, archives, feed); False leaves
    # pages, menus and redirects only.
    "BLOG_ENABLED": True,
    # Axis: who may use the staff API. "staff": is_staff (IsStaffUser).
    # "model_perms": is_staff AND the @access mandate (has_perm per model).
    "STAFF_AUTHZ": "staff",
    # Locales content may be written in; the first fallback is DEFAULT_LOCALE.
    "LOCALES": ["en"],
    "DEFAULT_LOCALE": "en",
    # {"de-at": ["de"]}: extra fallbacks tried before DEFAULT_LOCALE.
    "LOCALE_FALLBACKS": {},
    # {"<type>": "dotted.path.PydanticModel" | None} merged over the built-ins.
    "BLOCK_TYPES": {},
    "EMBED_HOSTS": DEFAULT_EMBED_HOSTS,
    # Template keys a page may name; the frontend maps each to a layout.
    "PAGE_TEMPLATES": ["default", "landing", "legal", "faq"],
    # Public path prefix of blog posts: /blog/<slug>.
    "BLOG_PATH_PREFIX": "/blog",
    "WORDS_PER_MINUTE": 200,
    "REVISIONS_KEEP": 50,
    "PAGE_MAX_DEPTH": 6,
    "MENU_MAX_DEPTH": 3,
    "MENU_MAX_ITEMS": 200,
    "MAX_BLOCKS": 200,
    "MAX_BLOCKS_BYTES": 262144,
    "PREVIEW_TOKEN_TTL_SECONDS": 3600,
    # "https://example.com/preview?token={token}"; empty = no url in the
    # preview-token response.
    "PREVIEW_URL_TEMPLATE": "",
    # Absolute origin for feed and sitemap links when the site registry is
    # empty ("https://example.com"); with a registry the site's host is used.
    "SITE_ORIGIN": "",
    "FEED_ITEMS": 20,
    "CACHE_ALIAS": "default",
    "CACHE_TTL_SECONDS": 300,
    "HTTP_MAX_AGE": 60,
    # comm Function keeping cdn's media references; empty disables.
    "MEDIA_REFS_FUNCTION": "cdn.refs_sync",
    # comm Function checking a form block's reference ({public_id} ->
    # {exists, published}); empty = shape check only.
    "FORM_EXISTS_FUNCTION": "forms.form.exists",
    # comm Function translating text batches ({texts, source, target} ->
    # {texts}); empty = machine translation is off.
    "MACHINE_TRANSLATE": "",
    # Seconds one MACHINE_TRANSLATE call may take; a big page is several
    # sequential calls, each translated by an LLM in provider batches.
    "MACHINE_TRANSLATE_TIMEOUT_SECONDS": 300,
    # The translation Function's bounds (stapel-translate's defaults): chars
    # per text (longer rich-text leaves are split at sentence boundaries),
    # texts per call and chars per call (a page becomes several calls).
    "MACHINE_TRANSLATE_MAX_TEXT_CHARS": 5000,
    "MACHINE_TRANSLATE_MAX_ITEMS": 2000,
    "MACHINE_TRANSLATE_MAX_CHARS": 200000,
}

#: The values STAFF_AUTHZ accepts (system check E002 refuses anything else).
STAFF_AUTHZ_CHOICES = ("staff", "model_perms")

cms_settings = AppSettings("STAPEL_CMS", defaults=DEFAULTS)

__all__ = ["cms_settings", "DEFAULTS", "DEFAULT_EMBED_HOSTS", "STAFF_AUTHZ_CHOICES"]
