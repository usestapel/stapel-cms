"""Admin for stapel-cms.

Status moves only through the service (publish/archive actions), never a raw
field edit, so every move is checked by the FSM, snapshotted and announced.
Revisions are read-only.
"""
from django.contrib import admin, messages

from .models import Menu, MenuItem, Page, Post, Redirect, Revision, Tag

WORKFLOW_FIELDS = ("status", "version", "live_revision", "scheduled_revision", "publish_at", "published_at",
                   "last_published_at", "archived_at", "author_id", "updated_by_id", "media_refs",
                   "translation_group")


def _transition_action(kind: str, to_status: str):
    def action(modeladmin, request, queryset):
        from .services import CmsError
        from .services.content import transition

        moved = refused = 0
        for obj in queryset:
            try:
                transition(kind, obj.pk, request.user, to_status)
                moved += 1
            except CmsError:
                refused += 1
        if moved:
            modeladmin.message_user(request, f"{moved} item(s) moved to {to_status}.")
        if refused:
            modeladmin.message_user(request, f"{refused} item(s) cannot move to {to_status}.", messages.WARNING)

    action.__name__ = f"{kind}_{to_status}"
    action.short_description = f"Move selected to {to_status}"
    return action


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("path", "title", "site", "locale", "status", "last_published_at")
    list_filter = ("status", "site", "locale", "template")
    search_fields = ("title", "path")
    readonly_fields = ("path", *WORKFLOW_FIELDS)
    actions = [_transition_action("page", "published"), _transition_action("page", "archived")]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "site", "locale", "status", "published_at")
    list_filter = ("status", "site", "locale")
    search_fields = ("title", "slug")
    readonly_fields = ("reading_time_minutes", *WORKFLOW_FIELDS)
    actions = [_transition_action("post", "published"), _transition_action("post", "archived")]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "site", "locale")
    list_filter = ("site", "locale")


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    fields = ("parent", "position", "label", "target_type", "page", "post", "url", "route", "new_tab")


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "site", "locale", "updated_at")
    list_filter = ("site", "locale")
    inlines = [MenuItemInline]


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("old_path", "new_path", "site", "locale", "permanent", "source")
    list_filter = ("source", "site", "locale")
    search_fields = ("old_path", "new_path")


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("kind", "object_id", "number", "note", "created_by_id", "created_at")
    list_filter = ("kind",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
