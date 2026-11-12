# Errors — Русский

`111` error keys. Canonical texts live in the code (`register_service_errors`); localized texts in `translations/errors.ru.json`.

| Код | Статус | Параметры | Действие | Текст |
|---|---|---|---|---|
| `error.400.bad_request` | 400 | — | `fix_input` | Некорректный запрос |
| `error.400.captcha_invalid` | 400 | — | `retry` | Проверка капчи не пройдена. Пожалуйста, попробуйте ещё раз. |
| `error.400.captcha_required` | 400 | — | `retry` | Требуется токен капчи. |
| `error.400.cms_block_type_unknown` | 400 | `type` | `fix_input` | Неизвестный тип блока: {type} |
| `error.400.cms_blocks_invalid` | 400 | `detail` | `fix_input` | Блок содержимого заполнен неверно: {detail} |
| `error.400.cms_blocks_too_large` | 400 | `max_blocks`, `max_bytes` | `fix_input` | На странице слишком много содержимого (не больше {max_blocks} блоков и {max_bytes} байт) |
| `error.400.cms_form_unknown` | 400 | `form_id` | `fix_input` | Формы {form_id} не существует |
| `error.400.cms_locale_unknown` | 400 | — | `fix_input` | Этот язык не включён |
| `error.400.cms_menu_invalid` | 400 | `detail` | `fix_input` | Меню заполнено неверно: {detail} |
| `error.400.cms_object_expected` | 400 | — | `fix_input` | Это поле должно быть объектом |
| `error.400.cms_parent_invalid` | 400 | — | `fix_input` | Сюда эту страницу поместить нельзя |
| `error.400.cms_path_reserved` | 400 | — | `fix_input` | Этот адрес зарезервирован для блога |
| `error.400.cms_publish_at_invalid` | 400 | — | `fix_input` | Выберите время публикации в будущем |
| `error.400.cms_redirect_invalid` | 400 | — | `fix_input` | Перенаправление задано неверно |
| `error.400.cms_site_unknown` | 400 | — | `fix_input` | Неизвестный сайт |
| `error.400.cms_slug_invalid` | 400 | — | `fix_input` | Адрес может содержать только буквы, цифры и дефисы |
| `error.400.cms_tag_unknown` | 400 | — | `fix_input` | Неизвестный тег |
| `error.400.cms_template_unknown` | 400 | — | `fix_input` | Неизвестный шаблон страницы |
| `error.400.cms_tree_too_deep` | 400 | `max_depth` | `fix_input` | Страницы можно вкладывать не глубже {max_depth} уровней |
| `error.400.cms_url_unsafe` | 400 | — | `fix_input` | Такую ссылку использовать нельзя |
| `error.400.description_too_long` | 400 | `max_length` | `fix_input` | Описание должно содержать не более {max_length} символов |
| `error.400.description_too_short` | 400 | `min_length` | `fix_input` | Описание должно содержать не менее {min_length} символов |
| `error.400.expected_list` | 400 | — | `fix_input` | Ожидался список элементов |
| `error.400.feature_above_maximum` | 400 | `feature` | `fix_input` | Значение характеристики «{feature}» больше максимально допустимого |
| `error.400.feature_below_minimum` | 400 | `feature` | `fix_input` | Значение характеристики «{feature}» меньше минимально допустимого |
| `error.400.feature_invalid_config` | 400 | `feature` | `fix_input` | Некорректная конфигурация характеристики «{feature}» |
| `error.400.feature_invalid_format` | 400 | `feature` | `fix_input` | Недопустимый формат значения характеристики «{feature}» |
| `error.400.feature_invalid_rules` | 400 | `feature` | `fix_input` | Некорректные правила для характеристики «{feature}» |
| `error.400.feature_invalid_type` | 400 | `feature` | `fix_input` | Недопустимый тип значения характеристики «{feature}» |
| `error.400.feature_mandatory_missing` | 400 | `feature` | `fix_input` | Характеристика «{feature}» обязательна |
| `error.400.feature_not_allowed` | 400 | `feature` | `fix_input` | Характеристика «{feature}» здесь недопустима |
| `error.400.feature_not_in_options` | 400 | `feature` | `fix_input` | Значение характеристики «{feature}» не входит в список допустимых |
| `error.400.feature_unknown` | 400 | `feature` | `fix_input` | Неизвестная характеристика «{feature}» |
| `error.400.feature_unknown_type` | 400 | `feature` | `fix_input` | Неизвестный тип характеристики «{feature}» |
| `error.400.field.blank` | 400 | `field` | `fix_input` | Поле «{field}» не может быть пустым |
| `error.400.field.does_not_exist` | 400 | `field` | `fix_input` | «{field}» не существует |
| `error.400.field.invalid` | 400 | `field` | `fix_input` | Поле «{field}» содержит недопустимое значение |
| `error.400.field.invalid_choice` | 400 | `field` | `fix_input` | Недопустимый вариант для поля «{field}» |
| `error.400.field.max_length` | 400 | `field`, `max_length` | `fix_input` | Поле «{field}» должно содержать не более {max_length} символов |
| `error.400.field.max_value` | 400 | `field`, `max_value` | `fix_input` | Значение поля «{field}» должно быть не больше {max_value} |
| `error.400.field.min_length` | 400 | `field`, `min_length` | `fix_input` | Поле «{field}» должно содержать не менее {min_length} символов |
| `error.400.field.min_value` | 400 | `field`, `min_value` | `fix_input` | Значение поля «{field}» должно быть не меньше {min_value} |
| `error.400.field.null` | 400 | `field` | `fix_input` | Поле «{field}» не может быть null |
| `error.400.field.required` | 400 | `field` | `fix_input` | Поле «{field}» обязательно |
| `error.400.field.unique` | 400 | `field` | `fix_input` | Значение поля «{field}» должно быть уникальным |
| `error.400.forms_answers_not_object` | 400 | — | `fix_input` | Ответы должны быть объектом с ключами-слагами полей |
| `error.400.forms_duplicate_slug` | 400 | `slug` | `fix_input` | Слаг поля {slug} встречается более одного раза |
| `error.400.forms_empty_schema` | 400 | — | `fix_input` | Чтобы опубликовать форму, в ней должно быть хотя бы одно поле |
| `error.400.forms_invalid_retention` | 400 | — | `fix_input` | Индивидуальный срок хранения можно только сократить относительно модульного |
| `error.400.forms_invalid_schema` | 400 | — | `fix_input` | Схема формы некорректна |
| `error.400.forms_invalid_state` | 400 | — | `fix_input` | Неизвестное состояние формы |
| `error.400.forms_kind_not_allowed` | 400 | `kind` | `fix_input` | Поле типа {kind} нельзя использовать в форме |
| `error.400.forms_no_draft` | 400 | — | `fix_input` | Нечего публиковать: черновик отсутствует |
| `error.400.forms_no_recipients` | 400 | — | `fix_input` | Для этой формы не настроен ни один получатель уведомлений |
| `error.400.forms_not_published` | 400 | — | `fix_input` | У формы ещё нет опубликованной версии |
| `error.400.forms_too_many_fields` | 400 | — | `fix_input` | В форме больше полей, чем допускает ограничение |
| `error.400.forms_too_many_open` | 400 | — | `contact_support` | В этом рабочем пространстве уже открыто предельное число форм |
| `error.400.forms_unknown_field` | 400 | — | `fix_input` | В ответе есть поле, которого нет в форме |
| `error.400.invalid_ad_id` | 400 | — | `fix_input` | Недопустимый идентификатор объявления |
| `error.400.translate.batch_too_large` | 400 | `max_items` | `fix_input` | В одном запросе допускается не более {max_items} текстов |
| `error.400.translate.batch_too_long` | 400 | `max_chars` | `fix_input` | Суммарная длина текстов превышает {max_chars} символов |
| `error.400.translate.text_required` | 400 | — | `fix_input` | Укажите либо текст, либо непустой список текстов |
| `error.400.translate.text_too_long` | 400 | `max_chars` | `fix_input` | Текст длиннее {max_chars} символов |
| `error.400.translate.unsupported_language` | 400 | `language` | `fix_input` | Язык {language} здесь не настроен |
| `error.400.validation_error` | 400 | — | `fix_input` | Ошибка валидации |
| `error.400.verification_failed` | 400 | — | `verify` | Проверка не пройдена |
| `error.400.verification_invalid_factor` | 400 | — | `verify` | Этот способ подтверждения недоступен |
| `error.401.unauthorized` | 401 | — | `reauthenticate` | Требуется аутентификация |
| `error.402.payment_required` | 402 | — | `retry` | Требуется оплата |
| `error.403.forbidden` | 403 | — | `retry` | У вас нет прав для выполнения этого действия |
| `error.403.forms_forbidden` | 403 | — | `contact_support` | У вас нет доступа к этой форме |
| `error.403.network_blocked` | 403 | — | `contact_support` | Запросы из этой сети не разрешены. |
| `error.403.verification_enrollment_required` | 403 | — | `verify` | Требуется регистрация фактора подтверждения. |
| `error.403.verification_required` | 403 | — | `verify` | Требуется дополнительная проверка |
| `error.404.ad_not_found` | 404 | — | `retry` | Объявление не найдено |
| `error.404.cms_not_found` | 404 | — | `retry` | Страница не найдена |
| `error.404.cms_preview_invalid` | 404 | — | `fix_input` | Ссылка на предпросмотр недействительна или устарела |
| `error.404.cms_revision_not_found` | 404 | — | `retry` | Версия не найдена |
| `error.404.forms_not_found` | 404 | — | `verify` | Форма не найдена |
| `error.404.forms_submission_not_found` | 404 | — | `verify` | Ответ не найден |
| `error.404.not_found` | 404 | — | `retry` | Запрошенный ресурс не найден |
| `error.404.verification_challenge_not_found` | 404 | — | `verify` | Запрос на подтверждение не найден или истёк |
| `error.405.method_not_allowed` | 405 | — | `retry` | Метод не разрешён |
| `error.406.not_acceptable` | 406 | — | `retry` | Недопустимый формат ответа |
| `error.408.request_timeout` | 408 | — | `retry` | Время ожидания запроса истекло |
| `error.409.cms_delete_published` | 409 | — | `fix_input` | Опубликованное нельзя удалить — отправьте в архив |
| `error.409.cms_form_unpublished` | 409 | `form_id` | `fix_input` | Сначала опубликуйте форму {form_id}, а затем страницу, которая её встраивает |
| `error.409.cms_path_taken` | 409 | — | `fix_input` | Этот адрес уже занят другой страницей |
| `error.409.cms_slug_taken` | 409 | — | `fix_input` | Этот адрес уже занят |
| `error.409.cms_transition_invalid` | 409 | `from`, `to` | `fix_input` | Нельзя перейти из состояния {from} в {to} |
| `error.409.cms_variant_exists` | 409 | — | `fix_input` | Версия на этом языке уже есть |
| `error.409.cms_version_conflict` | 409 | `current` | `retry` | Кто-то сохранил это раньше вас; обновите, чтобы увидеть версию {current} |
| `error.409.conflict` | 409 | — | `fix_input` | Ресурс уже существует |
| `error.409.forms_submission_cap` | 409 | — | `contact_support` | Форма достигла предела числа ответов |
| `error.409.forms_version_superseded` | 409 | — | `retry` | Форма изменилась, пока вы её заполняли |
| `error.410.forms_closed` | 410 | — | `contact_support` | Эта форма закрыта |
| `error.410.gone` | 410 | — | `retry` | Ресурс был безвозвратно удалён |
| `error.413.forms_body_too_large` | 413 | — | `fix_input` | Ответ превышает предельный размер |
| `error.413.payload_too_large` | 413 | — | `retry` | Тело запроса слишком большое |
| `error.415.unsupported_media_type` | 415 | — | `retry` | Неподдерживаемый тип данных |
| `error.422.unprocessable_entity` | 422 | — | `wait_and_retry` | Невозможно обработать данные запроса |
| `error.423.locked` | 423 | — | `wait_and_retry` | Ресурс заблокирован |
| `error.423.verification_locked` | 423 | — | `wait_and_retry` | Слишком много неудачных попыток — подтверждение заблокировано |
| `error.429.rate_limit` | 429 | `retry_after_minutes` | `wait_and_retry` | Слишком много попыток. Повторите попытку через {retry_after_minutes} мин. |
| `error.429.too_many_requests` | 429 | — | `wait_and_retry` | Слишком много запросов. Пожалуйста, повторите попытку позже. |
| `error.500.internal` | 500 | — | `contact_support` | Что-то пошло не так |
| `error.502.translate.provider_unavailable` | 502 | — | `retry` | Сервис перевода недоступен |
| `error.503.cms_translation_unavailable` | 503 | — | `wait_and_retry` | Машинный перевод сейчас недоступен |
| `error.503.forms_workspaces_unavailable` | 503 | — | `wait_and_retry` | Сервис рабочих пространств недоступен |
| `error.503.mandate_unavailable` | 503 | — | `retry` | Не удалось проверить доступ к рабочему пространству |
| `error.503.translate.unavailable` | 503 | — | `retry` | Машинный перевод здесь недоступен |
