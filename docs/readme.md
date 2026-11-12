## What this is

Public site content for a Stapel product: **pages** in a slug tree, a
**blog** (posts, tags, archives, RSS/Atom), **menus**, **SEO** fields, a
sitemap Function and **redirects** written for you when a published page
moves. Staff write typed blocks, preview drafts by a signed link, publish
now or on a schedule, and restore revisions; the anonymous read is cached per
site and answers conditional requests. Content is scoped by the stapel-core
site registry and by locale, with a fallback chain.

Not stapel-docs: docs holds private workspace documents; cms holds what an
anonymous visitor reads at a URL of the site.

## Quick start

```python
INSTALLED_APPS = [
    # ...
    "stapel_cms",
]

STAPEL_CMS = {
    "LOCALES": ["en", "de"],
    "DEFAULT_LOCALE": "en",
}

# urls.py
path("cms/", include("stapel_cms.urls"))   # -> /cms/api/v1/...

# settings.py — scheduled publication every minute (Celery optional;
# `manage.py cms_publish_due` runs the same pass)
from stapel_cms.beat import get_cms_beat_schedule
CELERY_BEAT_SCHEDULE = {**get_cms_beat_schedule()}
```

```bash
python manage.py migrate
python manage.py cms_seed          # about, contacts, terms, privacy, faq as drafts
```

A project's own block is one pydantic model and one setting:

```python
from pydantic import Field
from stapel_cms.blocks import BlockData

class PricingTable(BlockData):
    plans: list[str] = Field(min_length=1, max_length=5)

STAPEL_CMS = {"BLOCK_TYPES": {"pricing_table": "myapp.blocks.PricingTable"}}
```

## Concepts

- **Page / Post** — the row is the staff's working copy; the public reads
  the **published snapshot** (a revision), so edits are invisible until
  published again. Workflow `draft → scheduled → published → archived`;
  every save, publish and schedule appends a revision; restore copies one
  back into the working copy. Optimistic lock on `version`.
- **Blocks** — `[{type, id, data}]`, each type a pydantic model from a MERGE
  registry: `rich_text` (a ProseMirror/TipTap JSON document — never HTML),
  `hero`, `faq`, `gallery`, `embed` (allowlisted hosts), `form` (a
  stapel-forms id), `listing_rail` (an opaque query for another module).
  Every link passes one safe-URL rule; `javascript:` and friends cannot be
  stored.
- **Paths and redirects** — a page's path is its ancestors' slugs; moving a
  published page (or renaming a published post) writes `old → new`
  redirects for the whole subtree, chains collapse, a page beats a redirect.
- **Sites and locales** — every row has a site key (stapel-core site
  registry; `""` on a single host) and a locale; reads fall back
  `requested → LOCALE_FALLBACKS → DEFAULT_LOCALE`; variants share a
  translation group (hreflang alternates). Machine translation is an
  optional Function.
- **Caching** — public bodies are cached per site and invalidated as a whole
  on every publish; `ETag` / `Last-Modified` answer 304.
- **GDPR** — staff ids are the only personal data; erasure pseudonymizes
  them and keeps the content.
