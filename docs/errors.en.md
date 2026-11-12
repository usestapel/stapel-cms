# Errors — English

`111` error keys. Canonical texts live in the code (`register_service_errors`); localized texts in `translations/errors.en.json`.

| Code | Status | Params | Remediation | Text |
|---|---|---|---|---|
| `error.400.bad_request` | 400 | — | `fix_input` | Bad request |
| `error.400.captcha_invalid` | 400 | — | `retry` | Captcha verification failed. Please try again. |
| `error.400.captcha_required` | 400 | — | `retry` | Captcha token is required. |
| `error.400.cms_block_type_unknown` | 400 | `type` | `fix_input` | Unknown content block type: {type} |
| `error.400.cms_blocks_invalid` | 400 | `detail` | `fix_input` | A content block is invalid: {detail} |
| `error.400.cms_blocks_too_large` | 400 | `max_blocks`, `max_bytes` | `fix_input` | The page has too much content (at most {max_blocks} blocks, {max_bytes} bytes) |
| `error.400.cms_form_unknown` | 400 | `form_id` | `fix_input` | There is no form {form_id} |
| `error.400.cms_locale_unknown` | 400 | — | `fix_input` | This language is not enabled |
| `error.400.cms_menu_invalid` | 400 | `detail` | `fix_input` | The menu is invalid: {detail} |
| `error.400.cms_object_expected` | 400 | — | `fix_input` | This field must be an object |
| `error.400.cms_parent_invalid` | 400 | — | `fix_input` | This page cannot be placed there |
| `error.400.cms_path_reserved` | 400 | — | `fix_input` | This address is reserved for the blog |
| `error.400.cms_publish_at_invalid` | 400 | — | `fix_input` | Pick a publication time in the future |
| `error.400.cms_redirect_invalid` | 400 | — | `fix_input` | The redirect is invalid |
| `error.400.cms_site_unknown` | 400 | — | `fix_input` | Unknown site |
| `error.400.cms_slug_invalid` | 400 | — | `fix_input` | The address part may contain only letters, digits and dashes |
| `error.400.cms_tag_unknown` | 400 | — | `fix_input` | Unknown tag |
| `error.400.cms_template_unknown` | 400 | — | `fix_input` | Unknown page template |
| `error.400.cms_tree_too_deep` | 400 | `max_depth` | `fix_input` | Pages may be nested at most {max_depth} levels deep |
| `error.400.cms_url_unsafe` | 400 | — | `fix_input` | This link is not allowed |
| `error.400.description_too_long` | 400 | `max_length` | `fix_input` | Description must be at most {max_length} characters |
| `error.400.description_too_short` | 400 | `min_length` | `fix_input` | Description must be at least {min_length} characters |
| `error.400.expected_list` | 400 | — | `fix_input` | Expected a list of items |
| `error.400.feature_above_maximum` | 400 | `feature` | `fix_input` | Value is above maximum for {feature} |
| `error.400.feature_below_minimum` | 400 | `feature` | `fix_input` | Value is below minimum for {feature} |
| `error.400.feature_invalid_config` | 400 | `feature` | `fix_input` | Invalid config for {feature} |
| `error.400.feature_invalid_format` | 400 | `feature` | `fix_input` | Invalid format for {feature} |
| `error.400.feature_invalid_rules` | 400 | `feature` | `fix_input` | Invalid rules for {feature} |
| `error.400.feature_invalid_type` | 400 | `feature` | `fix_input` | Invalid type for {feature} |
| `error.400.feature_mandatory_missing` | 400 | `feature` | `fix_input` | Mandatory feature {feature} is required |
| `error.400.feature_not_allowed` | 400 | `feature` | `fix_input` | Feature {feature} is not allowed here |
| `error.400.feature_not_in_options` | 400 | `feature` | `fix_input` | Value is not in allowed options for {feature} |
| `error.400.feature_unknown` | 400 | `feature` | `fix_input` | Unknown feature {feature} |
| `error.400.feature_unknown_type` | 400 | `feature` | `fix_input` | Unknown feature type for {feature} |
| `error.400.field.blank` | 400 | `field` | `fix_input` | {field} may not be blank |
| `error.400.field.does_not_exist` | 400 | `field` | `fix_input` | {field} does not exist |
| `error.400.field.invalid` | 400 | `field` | `fix_input` | {field} is invalid |
| `error.400.field.invalid_choice` | 400 | `field` | `fix_input` | {field} is not a valid choice |
| `error.400.field.max_length` | 400 | `field`, `max_length` | `fix_input` | {field} must be at most {max_length} characters |
| `error.400.field.max_value` | 400 | `field`, `max_value` | `fix_input` | {field} must be at most {max_value} |
| `error.400.field.min_length` | 400 | `field`, `min_length` | `fix_input` | {field} must be at least {min_length} characters |
| `error.400.field.min_value` | 400 | `field`, `min_value` | `fix_input` | {field} must be at least {min_value} |
| `error.400.field.null` | 400 | `field` | `fix_input` | {field} may not be null |
| `error.400.field.required` | 400 | `field` | `fix_input` | {field} is required |
| `error.400.field.unique` | 400 | `field` | `fix_input` | {field} must be unique |
| `error.400.forms_answers_not_object` | 400 | — | `fix_input` | Answers must be an object keyed by field slug |
| `error.400.forms_duplicate_slug` | 400 | `slug` | `fix_input` | Field slug {slug} appears more than once |
| `error.400.forms_empty_schema` | 400 | — | `fix_input` | A form must have at least one field to publish |
| `error.400.forms_invalid_retention` | 400 | — | `fix_input` | The retention override may only shorten the module retention period |
| `error.400.forms_invalid_schema` | 400 | — | `fix_input` | The form schema is not valid |
| `error.400.forms_invalid_state` | 400 | — | `fix_input` | Unknown form state |
| `error.400.forms_kind_not_allowed` | 400 | `kind` | `fix_input` | Field kind {kind} may not be used in a form |
| `error.400.forms_no_draft` | 400 | — | `fix_input` | There is no draft to publish |
| `error.400.forms_no_recipients` | 400 | — | `fix_input` | No notification recipient is configured for this form |
| `error.400.forms_not_published` | 400 | — | `fix_input` | The form has no published version yet |
| `error.400.forms_too_many_fields` | 400 | — | `fix_input` | The form has more fields than the limit allows |
| `error.400.forms_too_many_open` | 400 | — | `contact_support` | This workspace already has the maximum number of open forms |
| `error.400.forms_unknown_field` | 400 | — | `fix_input` | The submission answers a field the form does not have |
| `error.400.invalid_ad_id` | 400 | — | `fix_input` | Invalid advertisement ID |
| `error.400.translate.batch_too_large` | 400 | `max_items` | `fix_input` | A batch may hold at most {max_items} texts |
| `error.400.translate.batch_too_long` | 400 | `max_chars` | `fix_input` | The batch holds more than {max_chars} characters in total |
| `error.400.translate.text_required` | 400 | — | `fix_input` | Provide either a text or a non-empty list of texts |
| `error.400.translate.text_too_long` | 400 | `max_chars` | `fix_input` | Text is longer than {max_chars} characters |
| `error.400.translate.unsupported_language` | 400 | `language` | `fix_input` | Language {language} is not configured here |
| `error.400.validation_error` | 400 | — | `fix_input` | Validation error |
| `error.400.verification_failed` | 400 | — | `verify` | Verification failed |
| `error.400.verification_invalid_factor` | 400 | — | `verify` | This verification factor is not available |
| `error.401.unauthorized` | 401 | — | `reauthenticate` | Authentication required |
| `error.402.payment_required` | 402 | — | `retry` | Payment required |
| `error.403.forbidden` | 403 | — | `retry` | You do not have permission to perform this action |
| `error.403.forms_forbidden` | 403 | — | `contact_support` | You do not have access to this form |
| `error.403.network_blocked` | 403 | — | `contact_support` | Requests from this network are not allowed |
| `error.403.verification_enrollment_required` | 403 | — | `verify` | Verification factor enrollment required |
| `error.403.verification_required` | 403 | — | `verify` | Additional verification required |
| `error.404.ad_not_found` | 404 | — | `retry` | Listing not found |
| `error.404.cms_not_found` | 404 | — | `retry` | Page not found |
| `error.404.cms_preview_invalid` | 404 | — | `fix_input` | This preview link is invalid or has expired |
| `error.404.cms_revision_not_found` | 404 | — | `retry` | Revision not found |
| `error.404.forms_not_found` | 404 | — | `verify` | Form not found |
| `error.404.forms_submission_not_found` | 404 | — | `verify` | Submission not found |
| `error.404.not_found` | 404 | — | `retry` | Requested resource not found |
| `error.404.verification_challenge_not_found` | 404 | — | `verify` | Verification challenge not found or expired |
| `error.405.method_not_allowed` | 405 | — | `retry` | Method not allowed |
| `error.406.not_acceptable` | 406 | — | `retry` | Not acceptable |
| `error.408.request_timeout` | 408 | — | `retry` | Request timeout |
| `error.409.cms_delete_published` | 409 | — | `fix_input` | Published content cannot be deleted; archive it instead |
| `error.409.cms_form_unpublished` | 409 | `form_id` | `fix_input` | Publish the form {form_id} before the page that embeds it |
| `error.409.cms_path_taken` | 409 | — | `fix_input` | Another page already uses this address |
| `error.409.cms_slug_taken` | 409 | — | `fix_input` | This address is already taken |
| `error.409.cms_transition_invalid` | 409 | `from`, `to` | `fix_input` | Cannot move from {from} to {to} |
| `error.409.cms_variant_exists` | 409 | — | `fix_input` | This language version already exists |
| `error.409.cms_version_conflict` | 409 | `current` | `retry` | Someone else saved this in the meantime; reload to see version {current} |
| `error.409.conflict` | 409 | — | `fix_input` | Resource already exists |
| `error.409.forms_submission_cap` | 409 | — | `contact_support` | This form has reached its submission limit |
| `error.409.forms_version_superseded` | 409 | — | `retry` | The form changed while you were filling it in |
| `error.410.forms_closed` | 410 | — | `contact_support` | This form is closed |
| `error.410.gone` | 410 | — | `retry` | Resource has been permanently removed |
| `error.413.forms_body_too_large` | 413 | — | `fix_input` | The submission exceeds the size limit |
| `error.413.payload_too_large` | 413 | — | `retry` | Request body is too large |
| `error.415.unsupported_media_type` | 415 | — | `retry` | Unsupported media type |
| `error.422.unprocessable_entity` | 422 | — | `wait_and_retry` | Unprocessable entity |
| `error.423.locked` | 423 | — | `wait_and_retry` | Resource is locked |
| `error.423.verification_locked` | 423 | — | `wait_and_retry` | Too many failed attempts — verification locked |
| `error.429.rate_limit` | 429 | `retry_after_minutes` | `wait_and_retry` | Too many attempts. Try again in {retry_after_minutes} minutes. |
| `error.429.too_many_requests` | 429 | — | `wait_and_retry` | Too many requests. Please try again later. |
| `error.500.internal` | 500 | — | `contact_support` | Something went wrong |
| `error.502.translate.provider_unavailable` | 502 | — | `retry` | The translation provider is unavailable |
| `error.503.cms_translation_unavailable` | 503 | — | `wait_and_retry` | Machine translation is unavailable right now |
| `error.503.forms_workspaces_unavailable` | 503 | — | `wait_and_retry` | Workspace membership service is unavailable |
| `error.503.mandate_unavailable` | 503 | — | `retry` | Cannot verify workspace mandate right now |
| `error.503.translate.unavailable` | 503 | — | `retry` | Content translation is not available here |
