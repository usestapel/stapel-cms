# stapel-cms — MODULE.md

> Agent-facing map of this module: what it provides, where to extend it
> without forking, and what not to do. Kept in the same PR as any change
> to a seam. Design of record: `docs/SPEC.md`. See also README.md, CONFIG.MD
> and CHANGELOG.md.

## What this module provides

- **Public site content**: `Page` (slug tree; path = ancestor slugs; unique
  per site + locale), `Post` + `Tag` (blog, archives, RSS/Atom), `Menu` +
  `MenuItem` (tree; targets page / post / URL / named route), SEO fields,
  `Redirect` (written automatically when a published page or post moves),
  `Revision` (full snapshots).
- **Typed blocks** validated by pydantic models from a MERGE registry:
  `rich_text` (ProseMirror/TipTap JSON — never HTML), `hero`, `faq`,
  `gallery`, `embed` (host allowlist), `form` (stapel-forms public id),
  `listing_rail` (opaque query). One safe-URL rule for every link.
- **Workflow** `draft → scheduled → published → archived` (table in
  `fsm.py`); the public reads the published snapshot, never the working
  copy; signed preview tokens; optimistic lock on `version`.
- **Site + locale scoping** through the stapel-core site registry, with a
  locale fallback chain and translation groups (hreflang alternates);
  optional machine translation through a Function.
- **Cached public read** (per-site generation token, ETag/Last-Modified,
  304) and the facts a CDN purger, a search index or a sitemap pinger needs.

Not stapel-docs (private workspace documents). Comments are stapel-feed;
forms are stapel-forms (embedded by id); media are stapel-cdn refs.

## Mounting

```python
INSTALLED_APPS = [..., "stapel_cms"]
path("cms/", include("stapel_cms.urls"))          # -> /cms/api/v1/...
CELERY_BEAT_SCHEDULE = {**get_cms_beat_schedule()} # stapel_cms.beat; or `manage.py cms_publish_due` each minute
```

## Extension points (fork-free)

### Settings — `STAPEL_CMS` namespace (`conf.py`, registry: CONFIG.MD)

| Key | Default | Kind |
|---|---|---|
| `BLOCK_TYPES` | `{}` | **MERGE** over `blocks.BUILTIN_BLOCK_TYPES`; `None` removes a built-in |
| `BLOG_ENABLED` | `True` | axis; False unmounts the blog routes (`urls_v1.GATE_REGISTRY`) |
| `STAFF_AUTHZ` | `"staff"` | axis; `"model_perms"` adds the `@access` mandate per model |
| `LOCALES` / `DEFAULT_LOCALE` / `LOCALE_FALLBACKS` | `["en"]` / `"en"` / `{}` | replace |
| `EMBED_HOSTS`, `PAGE_TEMPLATES`, `BLOG_PATH_PREFIX` | see CONFIG.MD | replace |
| `MACHINE_TRANSLATE` | `""` | comm Function name (contract `schemas/functions/machine_translate.json`) |
| `MEDIA_REFS_FUNCTION` | `"cdn.refs_sync"` | comm Function name; empty disables |
| limits, cache, preview | see CONFIG.MD | replace |

### Block registry (`blocks.py`)

A block is a pydantic model subclassing `stapel_cms.blocks.BlockData`
(`extra="forbid"`). Register it in settings (`BLOCK_TYPES`) or at runtime
(`register_block_type(name, Model)` from `AppConfig.ready()`). Text the
walkers treat as human text (translation, reading time) lives under the keys
in `blocks.TEXT_KEYS`; a key named `query` is opaque. `GET
staff/block-types/` publishes every model's JSON schema to the editor.

### Presenters (`STAPEL_SWAP`)

| Swap key | Default |
|---|---|
| `STAPEL_CMS_PUBLIC_PRESENTER` | `stapel_cms.presenters.PublicPresenter` |
| `STAPEL_CMS_STAFF_PRESENTER` | `stapel_cms.presenters.StaffPresenter` |

### Serializer seams (`views.py`)

Every view inherits `StapelAPIView`; subclass it, set
`request_serializer_class` / `response_serializer_class`, remount the URL.

### Comm surface

| Kind | Name | Schema |
|---|---|---|
| Function (provides) | `cms.sitemap_entries {site?, locale?, cursor?, limit?}` → `{entries, cursor}` — a stapel-core sitemap provider | `schemas/functions/cms.sitemap_entries.json` |
| Function (provides) | `cms.resolve_path {site, locale, path}` → `{found, kind, id, locale, title, path}` | `schemas/functions/cms.resolve_path.json` |
| Function (provides) | `cms.feed {site, locale, type}` → `{content_type, body}` | `schemas/functions/cms.feed.json` |
| Function (calls, optional) | `MACHINE_TRANSLATE`, `MEDIA_REFS_FUNCTION` | `schemas/functions/machine_translate.json`; cdn's own |
| Action (emits) | `cms.page.published`, `cms.page.unpublished`, `cms.post.published`, `cms.post.unpublished`, `cms.menu.changed`, `cms.redirect.created` | `schemas/emits/` |
| Action (consumes) | `user.merged` (authorship ids follow the survivor) | `schemas/consumes/user.merged.json` |

### Sitemap (stapel-core's aggregator)

With a core that ships `stapel_core.django.sitemap`, `AppConfig.ready()`
registers `cms.sitemap_entries` as provider `"cms"` (remove it with
`STAPEL_SITEMAP = {"PROVIDERS": {"cms": None}}`), and every publish,
unpublish or move of public content drops the site's cached set
(`invalidate_sitemaps(site)`, now and after commit). The host mounts
`get_sitemap_urls()`. Site keys are core's `Site.key`.

**Locales.** Variant paths carry no locale (`/about` in `en` and in `de`).
If the frontend prefixes locales, set
`STAPEL_SITEMAP["URL_TEMPLATE"] = "{origin}/{locale}{path}"`; with more than
one locale and no `{locale}` in the template, check `W003` warns (every
variant would become one URL). One site per locale: silence `W003`.

GDPR: `register_gdpr_owner("cms", ["account"], erase_subject)` — erasure
pseudonymizes staff ids, content stays.

### System checks

`E001` block registry, `E002` STAFF_AUTHZ, `E003` locales, `E004` templates,
`E005` embed hosts, `W001` translation Function unreachable, `W002`
per-process cache, `W003` several locales but the sitemap URL template has no
`{locale}`.

## Contract emission — the `info.version` convention

`make contract` emits `docs/schema.json` (+ flows, errors, capabilities,
llms.txt, README) on Python 3.12; leave `SPECTACULAR_SETTINGS` unset in
`_codegen_settings.py` so the schema stays byte-identical to a monolith
aggregate's slice. `info.version` is not the contract's version.

## Anti-patterns

- **Don't store HTML.** Rich text is a typed document; a renderer maps
  nodes to elements. An "html" block is the class this module exists to
  close — add a typed block instead.
- **Don't read the working copy on a public path.** Public reads go through
  `services.public` (published snapshots); only a preview token unlocks the
  working copy.
- **Don't import other stapel modules** — cdn, forms, translate, feed are
  reached by Function name or by opaque id (architecture test).
- **Don't bypass `content.update`** for edits — it holds the version guard,
  the path move with its redirects, the revision and the cache bump.
- **Don't fork to change behavior** — every knob above is a seam; if a
  change is impossible without editing this package, that is an upstream
  bug.
