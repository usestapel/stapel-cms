# Changelog

All notable changes to stapel-cms are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Pre-1.0 semver: **minor = breaking**, patch = compatible.

## [Unreleased]

## [0.1.0] - 2026-11-12

### Added
- Pages in a slug tree (path unique per site and locale), blog posts with
  tags, date and tag archives and an RSS/Atom feed, menus with page / post /
  URL / named-route targets, SEO fields, redirects.
- Typed block registry (MERGE over built-ins `rich_text`, `hero`, `faq`,
  `gallery`, `embed`, `form`, `listing_rail`) validated by pydantic models;
  rich text is a ProseMirror/TipTap JSON document; one safe-URL rule for
  every link; embed host allowlist.
- Workflow draft → scheduled → published → archived with full-snapshot
  revisions and restore, signed preview tokens, optimistic lock on
  `version`; the public reads the published snapshot only.
- Automatic redirects when a published page subtree or post moves (chains
  collapse, a page beats a redirect).
- Site scoping through the stapel-core site registry, locale variants with a
  fallback chain and hreflang alternates, optional machine translation via a
  comm Function.
- Cached public read API (per-site generation token, ETag / Last-Modified,
  304) and staff API (`STAFF_AUTHZ` = `staff` | `model_perms`).
- Facts `cms.page.published`, `cms.page.unpublished`, `cms.post.published`,
  `cms.post.unpublished`, `cms.menu.changed`, `cms.redirect.created`;
  Functions `cms.sitemap_entries`, `cms.resolve_path`, `cms.feed`;
  `cms.sitemap_entries` is a provider of stapel-core's sitemap aggregator
  (registered when core has it; publish / unpublish / move drop the site's
  cached sitemaps; hreflang alternates for variant groups);
  `user.merged` consumer; GDPR owner (staff ids pseudonymized, content kept).
- `cms_seed` (about, contacts, terms, privacy, FAQ as drafts),
  `cms_publish_due` and the beat entry, admin, system checks E001–E005,
  W001–W003.
