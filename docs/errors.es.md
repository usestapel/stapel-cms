# Errors — Español

`111` error keys. Canonical texts live in the code (`register_service_errors`); localized texts in `translations/errors.es.json`.

| Código | Estado | Parámetros | Acción | Texto |
|---|---|---|---|---|
| `error.400.bad_request` | 400 | — | `fix_input` | Solicitud incorrecta |
| `error.400.captcha_invalid` | 400 | — | `retry` | La verificación del captcha ha fallado. Inténtalo de nuevo. |
| `error.400.captcha_required` | 400 | — | `retry` | Se requiere el token del captcha. |
| `error.400.cms_block_type_unknown` | 400 | `type` | `fix_input` | Tipo de bloque desconocido: {type} |
| `error.400.cms_blocks_invalid` | 400 | `detail` | `fix_input` | Un bloque de contenido no es válido: {detail} |
| `error.400.cms_blocks_too_large` | 400 | `max_blocks`, `max_bytes` | `fix_input` | La página tiene demasiado contenido (como máximo {max_blocks} bloques y {max_bytes} bytes) |
| `error.400.cms_form_unknown` | 400 | `form_id` | `fix_input` | No existe el formulario {form_id} |
| `error.400.cms_locale_unknown` | 400 | — | `fix_input` | Este idioma no está habilitado |
| `error.400.cms_menu_invalid` | 400 | `detail` | `fix_input` | El menú no es válido: {detail} |
| `error.400.cms_object_expected` | 400 | — | `fix_input` | Este campo debe ser un objeto |
| `error.400.cms_parent_invalid` | 400 | — | `fix_input` | Esta página no se puede colocar ahí |
| `error.400.cms_path_reserved` | 400 | — | `fix_input` | Esta dirección está reservada para el blog |
| `error.400.cms_publish_at_invalid` | 400 | — | `fix_input` | Elige una hora de publicación en el futuro |
| `error.400.cms_redirect_invalid` | 400 | — | `fix_input` | La redirección no es válida |
| `error.400.cms_site_unknown` | 400 | — | `fix_input` | Sitio desconocido |
| `error.400.cms_slug_invalid` | 400 | — | `fix_input` | La dirección solo puede contener letras, cifras y guiones |
| `error.400.cms_tag_unknown` | 400 | — | `fix_input` | Etiqueta desconocida |
| `error.400.cms_template_unknown` | 400 | — | `fix_input` | Plantilla de página desconocida |
| `error.400.cms_tree_too_deep` | 400 | `max_depth` | `fix_input` | Las páginas se pueden anidar como máximo {max_depth} niveles |
| `error.400.cms_url_unsafe` | 400 | — | `fix_input` | Este enlace no está permitido |
| `error.400.description_too_long` | 400 | `max_length` | `fix_input` | La descripción debe tener como máximo {max_length} caracteres |
| `error.400.description_too_short` | 400 | `min_length` | `fix_input` | La descripción debe tener al menos {min_length} caracteres |
| `error.400.expected_list` | 400 | — | `fix_input` | Se esperaba una lista de elementos |
| `error.400.feature_above_maximum` | 400 | `feature` | `fix_input` | El valor de {feature} es superior al máximo permitido |
| `error.400.feature_below_minimum` | 400 | `feature` | `fix_input` | El valor de {feature} es inferior al mínimo permitido |
| `error.400.feature_invalid_config` | 400 | `feature` | `fix_input` | Configuración no válida para {feature} |
| `error.400.feature_invalid_format` | 400 | `feature` | `fix_input` | Formato no válido para {feature} |
| `error.400.feature_invalid_rules` | 400 | `feature` | `fix_input` | Reglas no válidas para {feature} |
| `error.400.feature_invalid_type` | 400 | `feature` | `fix_input` | Tipo de valor no válido para {feature} |
| `error.400.feature_mandatory_missing` | 400 | `feature` | `fix_input` | La característica {feature} es obligatoria |
| `error.400.feature_not_allowed` | 400 | `feature` | `fix_input` | La característica {feature} no está permitida aquí |
| `error.400.feature_not_in_options` | 400 | `feature` | `fix_input` | El valor de {feature} no es una opción permitida |
| `error.400.feature_unknown` | 400 | `feature` | `fix_input` | Característica desconocida: {feature} |
| `error.400.feature_unknown_type` | 400 | `feature` | `fix_input` | Tipo de característica desconocido para {feature} |
| `error.400.field.blank` | 400 | `field` | `fix_input` | {field} no puede estar vacío |
| `error.400.field.does_not_exist` | 400 | `field` | `fix_input` | {field} no existe |
| `error.400.field.invalid` | 400 | `field` | `fix_input` | {field} no es válido |
| `error.400.field.invalid_choice` | 400 | `field` | `fix_input` | {field} no es una opción válida |
| `error.400.field.max_length` | 400 | `field`, `max_length` | `fix_input` | {field} debe tener como máximo {max_length} caracteres |
| `error.400.field.max_value` | 400 | `field`, `max_value` | `fix_input` | {field} debe ser como máximo {max_value} |
| `error.400.field.min_length` | 400 | `field`, `min_length` | `fix_input` | {field} debe tener al menos {min_length} caracteres |
| `error.400.field.min_value` | 400 | `field`, `min_value` | `fix_input` | {field} debe ser como mínimo {min_value} |
| `error.400.field.null` | 400 | `field` | `fix_input` | {field} no puede ser nulo |
| `error.400.field.required` | 400 | `field` | `fix_input` | {field} es obligatorio |
| `error.400.field.unique` | 400 | `field` | `fix_input` | {field} debe ser único |
| `error.400.forms_answers_not_object` | 400 | — | `fix_input` | Las respuestas deben ser un objeto indexado por identificador de campo |
| `error.400.forms_duplicate_slug` | 400 | `slug` | `fix_input` | El identificador de campo {slug} aparece más de una vez |
| `error.400.forms_empty_schema` | 400 | — | `fix_input` | Un formulario debe tener al menos un campo para publicarse |
| `error.400.forms_invalid_retention` | 400 | — | `fix_input` | La retención por formulario solo puede acortar el periodo del módulo |
| `error.400.forms_invalid_schema` | 400 | — | `fix_input` | El esquema del formulario no es válido |
| `error.400.forms_invalid_state` | 400 | — | `fix_input` | Estado de formulario desconocido |
| `error.400.forms_kind_not_allowed` | 400 | `kind` | `fix_input` | El tipo de campo {kind} no puede usarse en un formulario |
| `error.400.forms_no_draft` | 400 | — | `fix_input` | No hay ningún borrador que publicar |
| `error.400.forms_no_recipients` | 400 | — | `fix_input` | Este formulario no tiene ningún destinatario de notificaciones configurado |
| `error.400.forms_not_published` | 400 | — | `fix_input` | El formulario aún no tiene ninguna versión publicada |
| `error.400.forms_too_many_fields` | 400 | — | `fix_input` | El formulario tiene más campos de los que permite el límite |
| `error.400.forms_too_many_open` | 400 | — | `contact_support` | Este espacio de trabajo ya tiene el número máximo de formularios abiertos |
| `error.400.forms_unknown_field` | 400 | — | `fix_input` | La respuesta contiene un campo que el formulario no tiene |
| `error.400.invalid_ad_id` | 400 | — | `fix_input` | ID de anuncio no válido |
| `error.400.translate.batch_too_large` | 400 | `max_items` | `fix_input` | Un lote admite como máximo {max_items} textos |
| `error.400.translate.batch_too_long` | 400 | `max_chars` | `fix_input` | El lote supera los {max_chars} caracteres en total |
| `error.400.translate.text_required` | 400 | — | `fix_input` | Indica un texto o una lista de textos no vacía |
| `error.400.translate.text_too_long` | 400 | `max_chars` | `fix_input` | El texto supera los {max_chars} caracteres |
| `error.400.translate.unsupported_language` | 400 | `language` | `fix_input` | El idioma {language} no está configurado aquí |
| `error.400.validation_error` | 400 | — | `fix_input` | Error de validación |
| `error.400.verification_failed` | 400 | — | `verify` | La verificación ha fallado |
| `error.400.verification_invalid_factor` | 400 | — | `verify` | Este factor de verificación no está disponible |
| `error.401.unauthorized` | 401 | — | `reauthenticate` | Se requiere autenticación |
| `error.402.payment_required` | 402 | — | `retry` | Se requiere pago |
| `error.403.forbidden` | 403 | — | `retry` | No tienes permiso para realizar esta acción |
| `error.403.forms_forbidden` | 403 | — | `contact_support` | No tienes acceso a este formulario |
| `error.403.network_blocked` | 403 | — | `contact_support` | No se permiten solicitudes desde esta red. |
| `error.403.verification_enrollment_required` | 403 | — | `verify` | Es necesario registrar un factor de verificación. |
| `error.403.verification_required` | 403 | — | `verify` | Se requiere verificación adicional |
| `error.404.ad_not_found` | 404 | — | `retry` | Anuncio no encontrado |
| `error.404.cms_not_found` | 404 | — | `retry` | Página no encontrada |
| `error.404.cms_preview_invalid` | 404 | — | `fix_input` | Este enlace de vista previa no es válido o ha caducado |
| `error.404.cms_revision_not_found` | 404 | — | `retry` | Revisión no encontrada |
| `error.404.forms_not_found` | 404 | — | `verify` | Formulario no encontrado |
| `error.404.forms_submission_not_found` | 404 | — | `verify` | Respuesta no encontrada |
| `error.404.not_found` | 404 | — | `retry` | Recurso solicitado no encontrado |
| `error.404.verification_challenge_not_found` | 404 | — | `verify` | Desafío de verificación no encontrado o caducado |
| `error.405.method_not_allowed` | 405 | — | `retry` | Método no permitido |
| `error.406.not_acceptable` | 406 | — | `retry` | No aceptable |
| `error.408.request_timeout` | 408 | — | `retry` | Tiempo de espera de la solicitud agotado |
| `error.409.cms_delete_published` | 409 | — | `fix_input` | El contenido publicado no se puede eliminar; archívalo |
| `error.409.cms_form_unpublished` | 409 | `form_id` | `fix_input` | Publica el formulario {form_id} antes que la página que lo incluye |
| `error.409.cms_path_taken` | 409 | — | `fix_input` | Otra página ya usa esta dirección |
| `error.409.cms_slug_taken` | 409 | — | `fix_input` | Esta dirección ya está ocupada |
| `error.409.cms_transition_invalid` | 409 | `from`, `to` | `fix_input` | No se puede pasar de {from} a {to} |
| `error.409.cms_variant_exists` | 409 | — | `fix_input` | Ya existe una versión en este idioma |
| `error.409.cms_version_conflict` | 409 | `current` | `retry` | Otra persona guardó esto mientras tanto; recarga para ver la versión {current} |
| `error.409.conflict` | 409 | — | `fix_input` | El recurso ya existe |
| `error.409.forms_submission_cap` | 409 | — | `contact_support` | Este formulario ha alcanzado su límite de respuestas |
| `error.409.forms_version_superseded` | 409 | — | `retry` | El formulario cambió mientras lo rellenabas |
| `error.410.forms_closed` | 410 | — | `contact_support` | Este formulario está cerrado |
| `error.410.gone` | 410 | — | `retry` | El recurso se ha eliminado permanentemente |
| `error.413.forms_body_too_large` | 413 | — | `fix_input` | La respuesta supera el tamaño máximo |
| `error.413.payload_too_large` | 413 | — | `retry` | El cuerpo de la solicitud es demasiado grande |
| `error.415.unsupported_media_type` | 415 | — | `retry` | Tipo de contenido no compatible |
| `error.422.unprocessable_entity` | 422 | — | `wait_and_retry` | Entidad no procesable |
| `error.423.locked` | 423 | — | `wait_and_retry` | El recurso está bloqueado |
| `error.423.verification_locked` | 423 | — | `wait_and_retry` | Demasiados intentos fallidos — verificación bloqueada |
| `error.429.rate_limit` | 429 | `retry_after_minutes` | `wait_and_retry` | Demasiados intentos. Inténtalo de nuevo en {retry_after_minutes} minutos. |
| `error.429.too_many_requests` | 429 | — | `wait_and_retry` | Demasiadas solicitudes. Inténtalo de nuevo más tarde. |
| `error.500.internal` | 500 | — | `contact_support` | Algo salió mal |
| `error.502.translate.provider_unavailable` | 502 | — | `retry` | El servicio de traducción no está disponible |
| `error.503.cms_translation_unavailable` | 503 | — | `wait_and_retry` | La traducción automática no está disponible en este momento |
| `error.503.forms_workspaces_unavailable` | 503 | — | `wait_and_retry` | El servicio de espacios de trabajo no está disponible |
| `error.503.mandate_unavailable` | 503 | — | `retry` | No se puede verificar el mandato del espacio de trabajo |
| `error.503.translate.unavailable` | 503 | — | `retry` | La traducción automática no está disponible aquí |
