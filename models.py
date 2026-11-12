"""Models of stapel-cms.

Every row is scoped to a ``site`` (the stapel-core site registry key, ``""``
on a single-host deployment) and a ``locale``. A ``Page``/``Post`` row is the
staff's working copy; what the public reads is ``live_revision.snapshot``,
so an edit is invisible until it is published (docs/SPEC.md §3). People are
referenced by id strings, never foreign keys: erasure pseudonymizes them.
"""
from __future__ import annotations

import uuid

from django.db import models
from stapel_core.access import access

USER_ID_MAX_LENGTH = 64
SITE_MAX_LENGTH = 64
LOCALE_MAX_LENGTH = 16
SLUG_MAX_LENGTH = 100
PATH_MAX_LENGTH = 500
TITLE_MAX_LENGTH = 200
SEO_TITLE_MAX_LENGTH = 200
SEO_DESCRIPTION_MAX_LENGTH = 320
URL_MAX_LENGTH = 500
MEDIA_REF_MAX_LENGTH = 200
TEMPLATE_MAX_LENGTH = 64
EXCERPT_MAX_LENGTH = 500
TAG_NAME_MAX_LENGTH = 100
MENU_KEY_MAX_LENGTH = 64
MENU_LABEL_MAX_LENGTH = 120
ROUTE_MAX_LENGTH = 100
NOTE_MAX_LENGTH = 200


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Kind(models.TextChoices):
    PAGE = "page", "Page"
    POST = "post", "Post"


class TargetType(models.TextChoices):
    PAGE = "page", "Page"
    POST = "post", "Post"
    URL = "url", "URL"
    ROUTE = "route", "Named route"


@access.ops
class Revision(models.Model):
    """A full snapshot of one page's or post's editable fields."""

    kind = models.CharField(max_length=8, choices=Kind.choices, help_text="page or post.")
    object_id = models.BigIntegerField(help_text="Id of the page or post.")
    number = models.PositiveIntegerField(help_text="1, 2, 3 … per object.")
    snapshot = models.JSONField(help_text="The editable fields at this point.")
    note = models.CharField(max_length=NOTE_MAX_LENGTH, blank=True, default="", help_text="Why it was taken.")
    created_by_id = models.CharField(
        max_length=USER_ID_MAX_LENGTH, blank=True, default="", help_text="str(user.pk) of the editor."
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the snapshot was taken.")

    class Meta:
        app_label = "cms"
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "object_id", "number"], name="cms_revision_number_unique"),
        ]
        indexes = [models.Index(fields=["kind", "object_id", "-number"], name="cms_revision_object")]

    def __str__(self) -> str:
        return f"{self.kind}:{self.object_id}#{self.number}"


class Content(models.Model):
    """Fields a page and a post share: scope, SEO, workflow, authorship."""

    site = models.CharField(max_length=SITE_MAX_LENGTH, blank=True, default="", help_text="Site key; '' = single site.")
    locale = models.CharField(max_length=LOCALE_MAX_LENGTH, help_text="Language of this variant.")
    translation_group = models.UUIDField(default=uuid.uuid4, db_index=True, help_text="Shared by locale variants.")
    slug = models.CharField(max_length=SLUG_MAX_LENGTH, blank=True, default="", help_text="Last path segment.")
    title = models.CharField(max_length=TITLE_MAX_LENGTH, help_text="Visible title.")
    blocks = models.JSONField(default=list, blank=True, help_text="Validated block list (blocks.py).")
    seo_title = models.CharField(max_length=SEO_TITLE_MAX_LENGTH, blank=True, default="", help_text="<title>; '' = title.")
    seo_description = models.CharField(
        max_length=SEO_DESCRIPTION_MAX_LENGTH, blank=True, default="", help_text="Meta description."
    )
    canonical_url = models.CharField(max_length=URL_MAX_LENGTH, blank=True, default="", help_text="Canonical link.")
    og_image = models.CharField(max_length=MEDIA_REF_MAX_LENGTH, blank=True, default="", help_text="cdn ref.")
    noindex = models.BooleanField(default=False, help_text="Ask search engines not to index; left out of the sitemap.")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True,
        help_text="Workflow status; moved only through fsm.py.",
    )
    version = models.PositiveIntegerField(default=1, help_text="Optimistic lock; +1 on every save.")
    live_revision = models.ForeignKey(
        Revision, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="What the public reads; NULL = not public.",
    )
    scheduled_revision = models.ForeignKey(
        Revision, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Snapshot that goes live at publish_at.",
    )
    publish_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text="When the scheduled snapshot goes live.")
    published_at = models.DateTimeField(null=True, blank=True, help_text="First publication (a post's date).")
    last_published_at = models.DateTimeField(null=True, blank=True, help_text="Most recent publication.")
    archived_at = models.DateTimeField(null=True, blank=True, help_text="When it was archived.")
    author_id = models.CharField(max_length=USER_ID_MAX_LENGTH, blank=True, default="", help_text="Staff author id.")
    updated_by_id = models.CharField(max_length=USER_ID_MAX_LENGTH, blank=True, default="", help_text="Last editor id.")
    media_refs = models.JSONField(default=list, blank=True, help_text="cdn refs last synced to cdn.refs_sync.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last save.")

    class Meta:
        abstract = True


@access.standard
class Page(Content):
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children",
        help_text="Parent page (same site and locale); NULL = top level.",
    )
    path = models.CharField(max_length=PATH_MAX_LENGTH, help_text="Derived: '/' + ancestor slugs.")
    template = models.CharField(max_length=TEMPLATE_MAX_LENGTH, default="default", help_text="PAGE_TEMPLATES key.")

    class Meta:
        app_label = "cms"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["site", "locale", "path"], name="cms_page_path_unique"),
        ]
        indexes = [models.Index(fields=["site", "locale", "status"], name="cms_page_scope")]

    def __str__(self) -> str:
        return f"{self.site or '-'}:{self.locale}:{self.path}"


@access.standard
class Tag(models.Model):
    site = models.CharField(max_length=SITE_MAX_LENGTH, blank=True, default="", help_text="Site key.")
    locale = models.CharField(max_length=LOCALE_MAX_LENGTH, help_text="Language.")
    slug = models.CharField(max_length=SLUG_MAX_LENGTH, help_text="URL key.")
    name = models.CharField(max_length=TAG_NAME_MAX_LENGTH, help_text="Visible name.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created.")

    class Meta:
        app_label = "cms"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["site", "locale", "slug"], name="cms_tag_slug_unique")]

    def __str__(self) -> str:
        return self.name


@access.standard
class Post(Content):
    excerpt = models.CharField(max_length=EXCERPT_MAX_LENGTH, blank=True, default="", help_text="Teaser text.")
    cover = models.CharField(max_length=MEDIA_REF_MAX_LENGTH, blank=True, default="", help_text="cdn ref of the cover.")
    reading_time_minutes = models.PositiveIntegerField(default=1, help_text="Derived from the word count.")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts", help_text="Same site and locale.")

    class Meta:
        app_label = "cms"
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["site", "locale", "slug"], name="cms_post_slug_unique")]
        indexes = [models.Index(fields=["site", "locale", "status"], name="cms_post_scope")]

    def __str__(self) -> str:
        return f"{self.site or '-'}:{self.locale}:{self.slug}"


@access.standard
class Menu(models.Model):
    site = models.CharField(max_length=SITE_MAX_LENGTH, blank=True, default="", help_text="Site key.")
    locale = models.CharField(max_length=LOCALE_MAX_LENGTH, help_text="Language.")
    key = models.CharField(max_length=MENU_KEY_MAX_LENGTH, help_text="header, footer, …")
    title = models.CharField(max_length=TITLE_MAX_LENGTH, blank=True, default="", help_text="Staff-facing name.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last change of the menu or its items.")

    class Meta:
        app_label = "cms"
        ordering = ["key"]
        constraints = [models.UniqueConstraint(fields=["site", "locale", "key"], name="cms_menu_key_unique")]

    def __str__(self) -> str:
        return f"{self.site or '-'}:{self.locale}:{self.key}"


@access.standard
class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items", help_text="Owning menu.")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", help_text="Parent item.",
    )
    position = models.PositiveIntegerField(default=0, help_text="Order among siblings.")
    label = models.CharField(max_length=MENU_LABEL_MAX_LENGTH, help_text="Visible text.")
    target_type = models.CharField(max_length=8, choices=TargetType.choices, help_text="What the item opens.")
    page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", help_text="Target page.")
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", help_text="Target post.")
    url = models.CharField(max_length=URL_MAX_LENGTH, blank=True, default="", help_text="Target URL (safe-URL rule).")
    route = models.CharField(max_length=ROUTE_MAX_LENGTH, blank=True, default="", help_text="Frontend route name.")
    route_params = models.JSONField(default=dict, blank=True, help_text="Route parameters.")
    new_tab = models.BooleanField(default=False, help_text="Open in a new tab.")

    class Meta:
        app_label = "cms"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.label


class RedirectSource(models.TextChoices):
    AUTO = "auto", "Written on a path change"
    MANUAL = "manual", "Added by staff"


@access.standard
class Redirect(models.Model):
    site = models.CharField(max_length=SITE_MAX_LENGTH, blank=True, default="", help_text="Site key.")
    locale = models.CharField(max_length=LOCALE_MAX_LENGTH, help_text="Language.")
    old_path = models.CharField(max_length=PATH_MAX_LENGTH, help_text="Path that moved.")
    new_path = models.CharField(max_length=PATH_MAX_LENGTH, help_text="Where it lives now (path or https URL).")
    permanent = models.BooleanField(default=True, help_text="301 rather than 302.")
    source = models.CharField(max_length=8, choices=RedirectSource.choices, default=RedirectSource.MANUAL, help_text="Who wrote it.")
    created_by_id = models.CharField(max_length=USER_ID_MAX_LENGTH, blank=True, default="", help_text="Staff id for manual rows.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created.")

    class Meta:
        app_label = "cms"
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["site", "locale", "old_path"], name="cms_redirect_unique")]

    def __str__(self) -> str:
        return f"{self.old_path} -> {self.new_path}"
