# CONFIG.MD — stapel-cms

Config registry for **stapel-cms**. One row per configuration key the module
reads, its **source** (`env` = the process environment / the `STAPEL_CMS`
settings dict), what it is for, whether it is required, and its default.

Every key is read through `cms_settings` (`stapel_cms.conf`, namespace
`STAPEL_CMS`). Resolution order per key: `settings.STAPEL_CMS` dict → a flat
Django setting of the same name → environment variable → the default below.
`BLOG_ENABLED` and `STAFF_AUTHZ` are CTO-facing config axes. `BLOCK_TYPES`
MERGES over the built-in block types; every other key replaces its default.

## stapel-cms

| Key | Source | Purpose | Required | Default |
|-----|--------|---------|----------|---------|
| BLOG_ENABLED | env | axis: false unmounts posts, tags, archives and the feed (pages, menus, redirects stay). | no | true |
| STAFF_AUTHZ | env | axis: `staff` = any staff account edits; `model_perms` = staff plus the @access mandate per model (`has_perm("cms.<action>_<model>")`). Anything else is check E002. | no | staff |
| LOCALES | settings | locales content may be written in; must contain DEFAULT_LOCALE (E003). | no | ["en"] |
| DEFAULT_LOCALE | env | last step of every fallback chain; the locale of seed pages. | no | en |
| LOCALE_FALLBACKS | settings | `{"de-at": ["de"]}`: fallbacks tried before DEFAULT_LOCALE; every name must be in LOCALES (E003). | no | {} |
| BLOCK_TYPES | settings | `{"<type>": "dotted.path.PydanticModel" or None}` merged over the built-ins (rich_text, hero, faq, gallery, embed, form, listing_rail); None removes one. Checked by E001. | no | {} |
| EMBED_HOSTS | settings | exact hosts an embed block may use (https only); bare host names (E005). | no | youtube, youtube-nocookie, vimeo, google maps hosts |
| PAGE_TEMPLATES | settings | template keys a page may name; the frontend maps each to a layout. Empty is E004. | no | ["default", "landing", "legal", "faq"] |
| BLOG_PATH_PREFIX | env | public path prefix of posts (`/blog/<slug>`); pages may not live under it. | no | /blog |
| WORDS_PER_MINUTE | env | reading-time divisor. | no | 200 |
| REVISIONS_KEEP | env | revisions kept per page or post; the live and scheduled ones are never pruned. | no | 50 |
| PAGE_MAX_DEPTH | env | path segments a page may have. | no | 6 |
| MENU_MAX_DEPTH | env | nesting levels of a menu. | no | 3 |
| MENU_MAX_ITEMS | env | items per menu. | no | 200 |
| MAX_BLOCKS | env | blocks per page or post. | no | 200 |
| MAX_BLOCKS_BYTES | env | serialized size of a block list. | no | 262144 |
| PREVIEW_TOKEN_TTL_SECONDS | env | lifetime of a signed preview link. | no | 3600 |
| PREVIEW_URL_TEMPLATE | env | `https://…?token={token}` returned with a preview token; empty = no url. | no | "" |
| SITE_ORIGIN | env | absolute origin for feed links when the site registry is empty. | no | "" |
| FEED_ITEMS | env | posts in the RSS/Atom feed. | no | 20 |
| CACHE_ALIAS | env | Django cache alias of the public read cache; a per-process cache is warning W002. | no | default |
| CACHE_TTL_SECONDS | env | lifetime of a cached public body (bounds staleness on a per-process cache). | no | 300 |
| HTTP_MAX_AGE | env | `Cache-Control: public, max-age` of public reads. | no | 60 |
| MEDIA_REFS_FUNCTION | env | comm Function told which cdn refs content uses (`cdn.refs_sync` contract); empty disables. | no | cdn.refs_sync |
| MACHINE_TRANSLATE | env | comm Function `{texts, source, target}` → `{texts}` for machine-translated locale variants; empty = off; unreachable is W001. | no | "" |
| MACHINE_TRANSLATE_TIMEOUT_SECONDS | env | seconds one MACHINE_TRANSLATE call may take (a page is several sequential calls). | no | 300 |
| MACHINE_TRANSLATE_MAX_TEXT_CHARS | env | chars per text the translation Function accepts; longer rich-text leaves are split at sentence boundaries and rejoined. | no | 5000 |
| MACHINE_TRANSLATE_MAX_ITEMS | env | texts per translation call. | no | 2000 |
| MACHINE_TRANSLATE_MAX_CHARS | env | chars per translation call. | no | 200000 |
| FORM_EXISTS_FUNCTION | env | comm Function `{public_id}` → `{exists, published}` checking a form block on save (unknown refused) and publish (unpublished refused); unreachable = shape check plus a warning; empty disables. | no | forms.form.exists |
