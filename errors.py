"""i18n error keys of stapel-cms.

Only ``error.<status>.<slug>`` keys leave this package — human-readable
strings are translations, never literals in responses.
"""
from stapel_core.django.api.errors import register_service_errors

ERR_400_BLOCKS_INVALID = "error.400.cms_blocks_invalid"
ERR_400_BLOCK_TYPE_UNKNOWN = "error.400.cms_block_type_unknown"
ERR_400_BLOCKS_TOO_LARGE = "error.400.cms_blocks_too_large"
ERR_400_URL_UNSAFE = "error.400.cms_url_unsafe"
ERR_400_SITE_UNKNOWN = "error.400.cms_site_unknown"
ERR_400_LOCALE_UNKNOWN = "error.400.cms_locale_unknown"
ERR_400_TEMPLATE_UNKNOWN = "error.400.cms_template_unknown"
ERR_400_SLUG_INVALID = "error.400.cms_slug_invalid"
ERR_400_PARENT_INVALID = "error.400.cms_parent_invalid"
ERR_400_TREE_TOO_DEEP = "error.400.cms_tree_too_deep"
ERR_400_PATH_RESERVED = "error.400.cms_path_reserved"
ERR_400_PUBLISH_AT_INVALID = "error.400.cms_publish_at_invalid"
ERR_400_MENU_INVALID = "error.400.cms_menu_invalid"
ERR_400_REDIRECT_INVALID = "error.400.cms_redirect_invalid"
ERR_400_TAG_UNKNOWN = "error.400.cms_tag_unknown"
ERR_400_OBJECT_EXPECTED = "error.400.cms_object_expected"
ERR_404_NOT_FOUND = "error.404.cms_not_found"
ERR_404_PREVIEW_INVALID = "error.404.cms_preview_invalid"
ERR_404_REVISION_NOT_FOUND = "error.404.cms_revision_not_found"
ERR_409_PATH_TAKEN = "error.409.cms_path_taken"
ERR_409_SLUG_TAKEN = "error.409.cms_slug_taken"
ERR_409_VERSION_CONFLICT = "error.409.cms_version_conflict"
ERR_409_TRANSITION_INVALID = "error.409.cms_transition_invalid"
ERR_409_DELETE_PUBLISHED = "error.409.cms_delete_published"
ERR_409_VARIANT_EXISTS = "error.409.cms_variant_exists"
ERR_503_TRANSLATION_UNAVAILABLE = "error.503.cms_translation_unavailable"

STAPEL_CMS_ERRORS = {
    ERR_400_BLOCKS_INVALID: "A content block is invalid: {detail}",
    ERR_400_BLOCK_TYPE_UNKNOWN: "Unknown content block type: {type}",
    ERR_400_BLOCKS_TOO_LARGE: "The page has too much content (at most {max_blocks} blocks, {max_bytes} bytes)",
    ERR_400_URL_UNSAFE: "This link is not allowed",
    ERR_400_SITE_UNKNOWN: "Unknown site",
    ERR_400_LOCALE_UNKNOWN: "This language is not enabled",
    ERR_400_TEMPLATE_UNKNOWN: "Unknown page template",
    ERR_400_SLUG_INVALID: "The address part may contain only letters, digits and dashes",
    ERR_400_PARENT_INVALID: "This page cannot be placed there",
    ERR_400_TREE_TOO_DEEP: "Pages may be nested at most {max_depth} levels deep",
    ERR_400_PATH_RESERVED: "This address is reserved for the blog",
    ERR_400_PUBLISH_AT_INVALID: "Pick a publication time in the future",
    ERR_400_MENU_INVALID: "The menu is invalid: {detail}",
    ERR_400_REDIRECT_INVALID: "The redirect is invalid",
    ERR_400_TAG_UNKNOWN: "Unknown tag",
    ERR_400_OBJECT_EXPECTED: "This field must be an object",
    ERR_404_NOT_FOUND: "Page not found",
    ERR_404_PREVIEW_INVALID: "This preview link is invalid or has expired",
    ERR_404_REVISION_NOT_FOUND: "Revision not found",
    ERR_409_PATH_TAKEN: "Another page already uses this address",
    ERR_409_SLUG_TAKEN: "This address is already taken",
    ERR_409_VERSION_CONFLICT: "Someone else saved this in the meantime; reload to see version {current}",
    ERR_409_TRANSITION_INVALID: "Cannot move from {from} to {to}",
    ERR_409_DELETE_PUBLISHED: "Published content cannot be deleted; archive it instead",
    ERR_409_VARIANT_EXISTS: "This language version already exists",
    ERR_503_TRANSLATION_UNAVAILABLE: "Machine translation is unavailable right now",
}

#: Explicit remediation where the status heuristic would mislead.
STAPEL_CMS_REMEDIATION = {
    ERR_409_VERSION_CONFLICT: "retry",
    ERR_503_TRANSLATION_UNAVAILABLE: "wait_and_retry",
}

register_service_errors(STAPEL_CMS_ERRORS, remediation=STAPEL_CMS_REMEDIATION)

__all__ = ["STAPEL_CMS_ERRORS", *sorted(name for name in list(globals()) if name.startswith("ERR_"))]
