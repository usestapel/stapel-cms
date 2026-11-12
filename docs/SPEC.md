# SPEC — stapel-cms 0.1.0 (public content: pages, blog, menus, SEO)

Status: **decided; 0.1.0 built, not yet published.** Consumers: the React
pair (`@stapel/cms-react`) generates from `docs/schema.json` and reads this
file for the semantics; the gates in §12 enforce it (`tests/`).

## 1. Scope boundary

| Decision | Reason |
|---|---|
| **In: public site content** — pages (slug tree), blog posts + tags, menus, SEO fields, redirects. Read anonymously, cached, by path. | "About / FAQ / terms pages, a blog, edit the menu myself, SEO fields" is the first request after every archetype's v1. |
| **Not stapel-docs.** stapel-docs holds *private workspace documents*: Drive-style folders, workspace capability authz, snapshot/CRDT collaboration, content-addressed blob storage, trash. stapel-cms holds *public, site-scoped, staff-authored content* with a publish workflow and an anonymous read path. The boundary: **if an anonymous visitor reads it at a URL of the site, it is cms; if a workspace member edits it as a file, it is docs.** cms has no folders, no workspace ids, no blob storage, no collaboration protocol; docs has no publish state, no public read, no SEO. Neither imports the other. | Two different products sharing the word "revision". Duplicating docs' storage or authz here would be a second, weaker docs; bending docs into a public site would put an anonymous read path behind workspace authz. |
| **In: revisions** as full JSON snapshots of the editable fields, restore = copy a snapshot into the working copy. | The editing model is "one editor at a time, optimistic lock on `version`", not collaboration. |
| **Out: page builder UI** (drag and drop canvas). The staff API takes a validated `blocks` array; the pair ships a form-per-block editor. | A canvas is a product, not a brick. |
| **Out: comments** — that is stapel-feed. A post page embeds feed's thread by the post id if the host wants one. | One comment system in the fleet. |
| **Out: forms** — stapel-forms owns them; the `form` block embeds a form by its stapel-forms `public_id`. | Admin-defined forms with submissions already exist. |
| **Out: search indexing.** Facts (`cms.page.published`, …) carry the path so a search module can index later. | No search coupling in 0.1.0. |
| **Out: per-user content, personalisation, A/B.** | Content is the site's, not a user's. |

## 2. Site and locale

- **Site scoping** follows the stapel-core site registry (`stapel_core.sites`).
  Every row carries `site` (`CharField(64)`): the registry entry's brand key,
  else its host; `""` on a single-host deployment (empty registry). The
  public read derives the site from the request through
  `stapel_core.django.sites.site_for_request` (an unmatched host falls back
  to the primary, as the registry defines). The staff API takes `site`
  explicitly and refuses a key the registry does not declare
  (`error.400.cms_site_unknown`); with an empty registry only `""` is valid.
- **Locale variants** are rows keyed by `(site, locale, path)` for pages,
  `(site, locale, slug)` for posts/tags, `(site, locale, key)` for menus.
  Variants of one page share a `translation_group` UUID (the hreflang set).
  `LOCALES` (default `["en"]`), `DEFAULT_LOCALE` (`"en"`), `LOCALE_FALLBACKS`
  (`{"de-at": ["de"]}` style, default `{}`). The fallback chain of a request
  is `[requested, *LOCALE_FALLBACKS[requested], DEFAULT_LOCALE]`, deduplicated;
  the response names the locale it actually served and the published
  `alternates` of its translation group.
- **Machine translation is optional**: `POST staff/pages/{id}/variants/`
  copies a page into another locale as a draft; with
  `machine_translate: true` and `MACHINE_TRANSLATE` naming a reachable comm
  Function (stapel-translate's `translate.text`), the human text is sent:
  title, excerpt, SEO title/description, every block string field whose
  schema carries `x-cms-translatable`, and every text node of a rich
  document one by one (marks and structure untouched; code marks, code
  blocks, urls, media refs, ids and opaque queries never leave). A text
  longer than `MACHINE_TRANSLATE_MAX_TEXT_CHARS` (5000, the provider's
  per-text bound) is split at sentence boundaries and rejoined with its own
  separators; each node keeps its edge whitespace; the batch becomes
  sequential calls of at most `MACHINE_TRANSLATE_MAX_ITEMS` (2000) texts and
  `MACHINE_TRANSLATE_MAX_CHARS` (200 000) chars, each with
  `MACHINE_TRANSLATE_TIMEOUT_SECONDS` (300). Everything is translated before
  the variant is written (one transaction): unset, unreachable,
  `error.503.translate.unavailable`, a refusal or a malformed answer →
  `error.503.cms_translation_unavailable` with `params.reason`
  (`not_configured` | `unreachable` | `provider_failed` | `refused` |
  `malformed` | `failed`) and `params.upstream_error` (the neighbour's key,
  when it named one) — never a half-translated or untranslated copy.

## 3. Models

All user references are `CharField(64)` ids (`str(user.pk)`), never FKs —
pseudonymized ids must fit. `@access.standard` on Page, Post, Tag, Menu,
MenuItem, Redirect; `@access.ops` on Revision.

| Model | Fields (beyond id/timestamps) | Constraints |
|---|---|---|
| `Page` | `site, locale, translation_group, parent (self FK, same site+locale), slug (unicode slug ≤100, "" only for the root page), path (≤500, derived), template (key ≤64 from PAGE_TEMPLATES), title ≤200, blocks JSON, seo_title ≤200, seo_description ≤320, canonical_url ≤500, og_image (cdn ref ≤200), noindex, status, version, live_revision FK, scheduled_revision FK, publish_at, published_at (first), last_published_at, archived_at, author_id, updated_by_id, media_refs JSON` | unique `(site, locale, path)`; depth ≤ `PAGE_MAX_DEPTH` (6); a page may not live under `BLOG_PATH_PREFIX/` |
| `Post` | `site, locale, translation_group, slug, title, excerpt ≤500, cover (cdn ref), blocks, reading_time_minutes, tags M2M, author_id, …same SEO/workflow fields as Page` | unique `(site, locale, slug)` |
| `Tag` | `site, locale, slug ≤100, name ≤100` | unique `(site, locale, slug)` |
| `Menu` | `site, locale, key (slug ≤64, e.g. header/footer), title` | unique `(site, locale, key)` |
| `MenuItem` | `menu FK, parent (self FK), position, label ≤120, target_type (page/post/url/route), page FK SET_NULL, post FK SET_NULL, url ≤500 (safe-URL rule §5), route ≤100 + route_params JSON, new_tab` | depth ≤ `MENU_MAX_DEPTH` (3), items ≤ `MENU_MAX_ITEMS` (200) |
| `Redirect` | `site, locale, old_path, new_path, permanent, source (auto/manual), created_by_id` | unique `(site, locale, old_path)` |
| `Revision` | `kind (page/post), object_id, number, snapshot JSON, note ≤200, created_by_id` | unique `(kind, object_id, number)` |

**Working copy vs live.** The `Page`/`Post` row is the working copy the staff
edit. The public read serves `live_revision.snapshot` — never the working
copy — so editing a published page changes nothing visible until it is
published again. `has_unpublished_changes` = working copy differs from the
live snapshot.

## 4. Block registry

`blocks` is a list of `{"type": str, "id": str ≤64, "data": {…}}` (≤
`MAX_BLOCKS` = 200 blocks, ≤ `MAX_BLOCKS_BYTES` = 256 KiB serialized). Each
type has a **pydantic model** (`extra="forbid"`; blocks are untrusted
structured text from an editor) — the canon's validation boundary.
`STAPEL_CMS["BLOCK_TYPES"]` is a **MERGE registry** over the built-ins:
`{"<type>": "dotted.path.to.PydanticModel" | None}` (`None` removes a
built-in); `register_block_type()` is the runtime door. A project adds a
block fork-free. `GET staff/block-types/` publishes each type's
`model_json_schema()` so the pair's editor generates forms and the renderer
knows the shapes.

| Type | `data` |
|---|---|
| `rich_text` | `{doc: RichDoc}` (§5) |
| `hero` | `{heading ≤200, subheading? ≤500, media? (cdn ref), cta? {label ≤80, href (safe URL)}, align: start/center}` |
| `faq` | `{title? ≤200, items[≤100]: {question ≤300, answer: RichDoc}}` |
| `gallery` | `{layout: grid/carousel, items[1..60]: {media (cdn ref), alt ≤300, caption? ≤300}}` |
| `embed` | `{url (https, host in EMBED_HOSTS), title ≤200, aspect_ratio: 16:9/4:3/1:1/9:16}` |
| `form` | `{form_id (stapel-forms public_id ≤32), title? ≤200}` — checked through `forms.form.exists` (`FORM_EXISTS_FUNCTION`): unknown → `400 error.400.cms_form_unknown {field, form_id}` on save; unpublished → allowed in a draft with a `form_unpublished` warning, `409 error.409.cms_form_unpublished` on publish or schedule; Function unreachable → shape check only plus a `form_unverified` warning (never a 500). Staff content responses carry `warnings: [{code, field, params}]` of that request (empty on reads). |
| `listing_rail` | `{title? ≤200, source ≤32 (e.g. "listings"), query: opaque JSON object ≤2 KiB, limit 1..24}` — cms never interprets `query`; the pair hands it to the named source's hook |

A media reference is a stapel-cdn ref `<type>/<id>` (opaque). On save cms
calls `cdn.refs_sync` (`MEDIA_REFS_FUNCTION`, best-effort, after commit) so
cdn's unclaimed-media sweep does not delete pictures a page uses.

## 5. Rich text and untrusted-content safety

**Decision: a portable JSON document, not sanitised HTML.** `RichDoc` is the
ProseMirror/TipTap JSON subset: nodes `doc, paragraph, heading(level 1-6),
bulletList, orderedList(start), listItem, blockquote, codeBlock(language),
horizontalRule, hardBreak, image(media, alt, title), text`; marks `bold,
italic, underline, strike, code, link(href, new_tab)`. Why:

1. **No HTML ever reaches a renderer.** The pair maps nodes to React
   elements; there is no `dangerouslySetInnerHTML` to get wrong. An HTML
   sanitiser is an allowlist that must be correct in two languages (server
   cleaning, browser parsing) — mutation XSS lives in that gap. A typed tree
   has no gap: an unknown node or attribute is a validation error.
2. **Portable**: the same document renders to web, e-mail and mobile, and
   TipTap (the pair's editor) reads and writes it natively.
3. **No sanitiser dependency** in a Python package (nh3/bleach) and no
   "sanitised on write vs on read" fork.

The rules, enforced by pydantic (`extra="forbid"` on every node and mark):
unknown node/mark types are refused (no `html`, `script`, `iframe`, `style`
node exists); no `style`, `class` or `on*` attributes exist on any node;
`text` is plain text (a `<script>` inside it is characters, escaped by every
renderer); every URL (`link.href`, `cta.href`, menu `url`, `canonical_url`)
passes **one** safe-URL function: whitespace and control characters are
refused outright, then the value must start with `https://`, `http://`,
`mailto:`, `tel:`, `/` (not `//`) or `#` — so `javascript:`, `JaVaScRiPt:`,
`java\tscript:`, `data:`, `vbscript:`, `&#106;avascript:` and
protocol-relative `//evil.example` all fail. Embed URLs are `https` only and
the host must be in `EMBED_HOSTS` (exact host, case-folded, no userinfo, no
port). Depth ≤ 12, nodes per document ≤ 5000, text leaf ≤ 20 000 chars (kept above
the translation provider's 5000 per text: machine translation splits a long
leaf at sentence boundaries).
`tests/test_safety.py` holds the payload table.

## 6. Publish workflow

`status`: `draft → scheduled → published → archived`, table in `fsm.py`
(`TRANSITIONS`, inversion test: every illegal edge is a 409
`error.409.cms_transition_invalid`).

| From \ to | draft | scheduled | published | archived |
|---|---|---|---|---|
| draft | – | ✓ (`publish_at` in the future) | ✓ | ✓ |
| scheduled | ✓ (cancel: back to `published` when a live revision exists) | ✓ (reschedule) | ✓ (now) | ✓ |
| published | – | ✓ (schedule edits; the live revision keeps serving) | ✓ (republish edits) | ✓ |
| archived | ✓ (reopen as draft) | – | – | – |

- **Publish** snapshots the working copy into a new `Revision`, points
  `live_revision` at it, stamps `published_at` (first time only — the post
  date; staff may set it explicitly) and `last_published_at`, bumps the site
  cache generation and emits the fact — one `mutate_and_emit()` block.
- **Schedule** snapshots into `scheduled_revision` with `publish_at`. The
  public read already serves a due `scheduled_revision` (exact-time
  correctness without a scheduler); the beat pass `cms.publish_due` (every
  minute; `manage.py cms_publish_due` for hosts without Celery) promotes due
  rows, bumps the cache and emits the facts.
- **Archive** drops `live_revision`; the path stays reserved by the row.
- **Revisions**: every staff save, publish and schedule appends one; at most
  `REVISIONS_KEEP` (50) per object, the oldest pruned except the live and
  scheduled ones. `POST …/revisions/{number}/restore/` copies the snapshot
  into the working copy (itself a new revision); publishing stays a separate
  act.
- **Optimistic lock**: PATCH carries `version`; the update is
  `UPDATE … WHERE version = v` under `select_for_update` — a stale editor gets
  `error.409.cms_version_conflict` with the current version in params.
- **Preview**: `POST staff/{pages|posts}/{id}/preview-token/` → a signed
  token (`django.core.signing`, salt `stapel_cms.preview`, TTL
  `PREVIEW_TOKEN_TTL_SECONDS` = 3600) → `GET public/preview/?token=` serves
  the working copy with `Cache-Control: private, no-store` and `noindex`.
  Expired/forged → `error.404.cms_preview_invalid` (404, so a token cannot be
  probed).

## 7. Paths and redirects

`path` = `/` + slugs of the ancestor chain joined by `/`; the root page has
slug `""` and path `/`. A slug or parent change recomputes the subtree's
paths in one transaction; for every row that was ever published an
automatic `Redirect(old → new, permanent)` is written. Chains collapse
(`A→B` + `B→C` ⇒ `A→C`), a redirect whose `old_path` becomes a real page path
again is deleted (a page beats a redirect), a self-loop is never written. A
post slug change writes `/blog/old → /blog/new` the same way. Staff manage
manual redirects through `staff/redirects/`.

## 8. API (`path("cms/api/", include("stapel_cms.urls"))` → `/cms/api/v1/…`)

Public (`AllowAny`, `ANONYMOUS_ALLOWED`; site from the request):

| Method/path | Response |
|---|---|
| `GET public/resolve/?path=&locale=` | `ResolveResponse {kind: page/post/redirect, locale, page?, post?, redirect?}`; 404 `error.404.cms_not_found` |
| `GET public/posts/?locale=&tag=&year=&month=` | `PublicPostPage` (anchor on `published_at,id`, newest first) |
| `GET public/posts/{slug}/?locale=` | `PublicPost` |
| `GET public/post-archive/?locale=` | `PostArchiveResponse {months: [{year, month, count}]}` |
| `GET public/tags/?locale=` | `PublicTagList {items: [{slug, name, count}]}` |
| `GET public/menus/{key}/?locale=` | `PublicMenu {key, title, locale, items: [tree]}`; page/post targets resolved to their live path, unpublished targets dropped |
| `GET public/feed/?locale=&type=rss|atom` | RSS 2.0 / Atom XML |
| `GET public/preview/?token=` | `ResolveResponse` of the working copy |

Every public JSON read carries `ETag` (sha256 of the body) and
`Last-Modified`, answers `304` to `If-None-Match` / `If-Modified-Since`, and
`Cache-Control: public, max-age=HTTP_MAX_AGE` (60).

Staff (`ANONYMOUS_DENIED`; `STAFF_AUTHZ="staff"` → `IsStaffUser`,
`"model_perms"` → the `@access` mandate via `has_perm("cms.<action>_<model>")`):

| Method/path | |
|---|---|
| `GET/POST staff/pages/`, `GET/PATCH/DELETE staff/pages/{id}/` | `StaffPage`; list anchor-paginated, filters `site, locale, status, parent, q`; DELETE only when never published (else archive) |
| `POST staff/pages/{id}/transition/` | `TransitionRequest {to, publish_at?}` |
| `GET staff/pages/{id}/revisions/`, `POST staff/pages/{id}/revisions/{number}/restore/` | |
| `POST staff/pages/{id}/preview-token/` | `PreviewTokenResponse {token, expires_at, url}` |
| `POST staff/pages/{id}/variants/` | `VariantRequest {locale, machine_translate}` → `201 StaffPage` |
| the same five for `staff/posts/` | |
| `GET/POST staff/tags/`, `PATCH/DELETE staff/tags/{id}/` | |
| `GET/POST staff/menus/`, `GET/PUT/DELETE staff/menus/{id}/` | PUT replaces the item tree atomically |
| `GET/POST staff/redirects/`, `DELETE staff/redirects/{id}/` | |
| `GET staff/block-types/` | `BlockTypeList {items: [{type, schema}]}` |

`BLOG_ENABLED=False` unmounts every post/tag/feed route (`GATE_REGISTRY`).

## 9. Caching

Public JSON bodies are cached in `CACHE_ALIAS` (default `default`) under a
key that includes the **site generation token** (`cms:gen:<site>`). Every
publish, schedule promotion, archive, menu write, redirect write and
path move replaces the token in the same transaction's `on_commit`, which
invalidates every cached body of the site at once (content sites are small;
per-path purge is a later optimisation). Entries expire after
`CACHE_TTL_SECONDS` (300) regardless, which bounds staleness when the
deployment's cache is per-process (locmem) — a multi-process deployment
uses a shared cache. CDN purge subscribes to the facts.

## 10. Comm surface

**Emits** (inside `mutate_and_emit()`, key = object id; no personal data
beyond the staff `author_id`):
`cms.page.published {page_id, site, locale, path, revision, translation_group, published_at, first}`,
`cms.page.unpublished {page_id, site, locale, path}`,
`cms.post.published {post_id, site, locale, path, revision, published_at, tags, author_id, first}`,
`cms.post.unpublished {post_id, site, locale, path}`,
`cms.menu.changed {menu_id, site, locale, key}`,
`cms.redirect.created {site, locale, old_path, new_path, source}`.

**Functions**: `cms.sitemap_entries {site?, locale?, cursor?, limit?}` →
`{entries: [{path, locale, kind, lastmod, alternates}], cursor}` (published,
not `noindex`; `alternates` lists the indexable live variants of a
translation group of two or more, else `[]`; `limit` clamped to 1..5000).
It answers stapel-core's sitemap provider contract and is registered with
core's aggregator (`register_sitemap_provider`) from `AppConfig.ready()` when
core has it; publish, unpublish and a move of public content drop the site's
cached sitemap set (`invalidate_sitemaps(site)`). Variant paths carry no
locale: a frontend that prefixes locales sets `STAPEL_SITEMAP["URL_TEMPLATE"]
= "{origin}/{locale}{path}"` (check W003 otherwise). `cms.resolve_path {site, locale, path}` →
`{found, kind, id, locale, title, path}`; `cms.feed {site, locale, type}` →
`{content_type, body}`.

**Calls (optional, by name)**: `cdn.refs_sync` (`MEDIA_REFS_FUNCTION`), the
machine-translation Function (`MACHINE_TRANSLATE`).

**Consumes**: `user.merged` (author ids re-parented); `user.deleted` /
`gdpr.erasure.requested` through `register_gdpr_owner`.

## 11. Settings, GDPR, seed, admin

`STAPEL_CMS` (`AppSettings`, CONFIG.MD is the registry). Axes:
`BLOG_ENABLED` (true), `STAFF_AUTHZ` (`staff` / `model_perms`). Rest in
CONFIG.MD.

**GDPR stance**: content is staff-authored site content, owned by the site.
The only personal data is staff ids (`author_id`, `updated_by_id`,
`Revision.created_by_id`, `Redirect.created_by_id`). Export lists what the
person authored; erasure **pseudonymizes** those ids
(`stapel_core.gdpr.pseudonymize`) and keeps the content — the site's pages do
not disappear when an editor leaves. `register_gdpr_owner("cms",
["account"], erase)`.

**Seed**: `manage.py cms_seed [--site] [--locale]` creates `about`,
`contacts`, `terms`, `privacy`, `faq` as drafts with placeholder blocks
(idempotent; never publishes, never overwrites).

**Admin**: every model registered; status moves through the service
(admin actions publish/archive), never a raw field edit; revisions read-only.

## 12. Gates

pytest on 3.12 and 3.14 (contract emission pinned to 3.12);
`make contract-check`; `stapel-verify .`; `stapel-schema-lint --strict`;
`stapel-migration-lint --strict`; `stapel-sibling-lint`;
`python -m stapel_core.lint.emit_check`; `manage.py check` with and without
the site registry; migrate from zero; GDPR export + erase; concurrency:
two PATCHes on one version → one 200 + one 409, revision numbers unique
under a race; named inversion tests: FSM table, safe-URL payload table,
block registry merge/remove, architecture grep (no `stapel_*` sibling import).

## 13. Upstream asks

| Id | Repo | Ask |
|---|---|---|
| T1 | stapel-translate | a content Function (`translate.text {texts, source, target}` → `{texts}`) behind `MACHINE_TRANSLATE` — built; cms chunks to its bounds |
| F1 | stapel-forms | a public `forms.form.exists {public_id}` Function so the `form` block can be validated at save time — built; cms checks on save and publish |
| X1 | stapel-tools | `STAPEL_LIBS["cms"]` (url_prefix `cms/api/`, beat `stapel_cms.beat.get_cms_beat_schedule`), `_gdpr_owners.py` += `cms: ["account"]` |
| S1 | stapel-core | a site-scoped sitemap aggregator that asks `<module>.sitemap_entries` Functions — built (`stapel_core.django.sitemap`); cms registers with it and invalidates it |
