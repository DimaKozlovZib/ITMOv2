# Tasks: Модерация доносов (сторона UI)

**Input**: Design documents from `/specs/001-report-moderation-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-routes.md, quickstart.md

**Tests**: не запрашивались в спецификации. Тестовые задачи не генерируются. Проверка выполняется вручную
по `quickstart.md` (задача T030).

**Contract**: `practices/practice_05/contract.md` — единственный источник текстов, кодов и маршрутов.

**Scope**: шаблоны в `practices/practice_04/project/templates/`. Изменения `server.py` ограничены передачей
данных шаблонам и обработкой 400/404/500; валидация, дубликаты, переходы статусов и счётчики остаются за
командой логики (фича 002). Такие задачи помечены «интеграция с логикой».

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно (другой файл, нет зависимости от незавершённых задач)
- **[Story]**: US1–US4 для задач фаз пользовательских историй
- **BLOCKED**: задача ждёт решения R5 (задача T001)

---

## Phase 1: Setup

**Purpose**: подготовка и согласование до изменений

- [X] T001 Получить подтверждение на создание `practices/practice_04/project/templates/not_found.html` и `practices/practice_04/project/templates/error.html` (решение R5 в `specs/001-report-moderation-ui/research.md`). Без подтверждения T005 и T006 не выполняются
- [ ] T002 [P] Проверить базовую линию: запустить `.venv\Scripts\python practices\practice_04\project\server.py` и открыть `/`, `/reports`, `/thanks` в браузере; зафиксировать текущие отличия от `contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: общие тексты и шаблоны ошибок, нужные всем историям

**CRITICAL**: ни одна история не начинается до завершения этой фазы

- [X] T003 Добавить в `practices/practice_04/project/server.py` словарь `ERROR_TEXTS` с восемью кодами и текстами из `practices/practice_05/contract.md`, раздел «Тексты для UI»: `NAME_REQUIRED` → «Укажите имя студента.», `NAME_LENGTH` → «Имя студента: от 2 до 60 символов.», `GROUP_LENGTH` → «Группа: не больше 20 символов.», `DETAILS_REQUIRED` → «Опишите ситуацию.», `DETAILS_LENGTH` → «Описание: от 10 до 1000 символов.», `VIBE_INVALID` → «Выберите уровень из списка.», `DUPLICATE` → «Такой донос уже отправлен. Измените данные и отправьте снова.», `INTERNAL_ERROR` → «Не удалось отправить донос. Попробуйте ещё раз.»
- [X] T004 Добавить в `practices/practice_04/project/server.py` словари `STATUS_LABELS` (`new` → «На рассмотрении», `confirmed` → «Подтверждён», `rejected` → «Отклонён») и `VIBE_LABELS` (`low` → «Низкий», `medium` → «Средний», `high` → «Высокий»)
- [X] T005 [P] BLOCKED (T001): создать `practices/practice_04/project/templates/not_found.html` с параметрами `title` и `message`, наследует `base.html`, содержит ссылки «Вернуться к списку доносов» (на `/reports`) и «Отправить донос» (на `/`)
- [X] T006 [P] BLOCKED (T001): создать `practices/practice_04/project/templates/error.html` с параметром `message` и ссылкой «Вернуться к списку доносов» (на `/reports`), наследует `base.html`

**Checkpoint**: тексты и шаблоны ошибок доступны всем историям

---

## Phase 3: User Story 1 - Отправка доноса с ошибками и повтором (Priority: P1) MVP

**Goal**: форма `/` выводит ошибки под полями и блоки над формой, сохраняет введённые значения

**Independent Test**: отправить пустую форму, получить 422 с текстами под полями, значения сохранены; отправить
дубликат, получить блок над формой

### Implementation for User Story 1

- [X] T007 [US1] В `practices/practice_04/project/templates/index.html` для поля `name` добавить `value="{{ values.name }}"` и `maxlength="60"`; ограничение из data-model: «`name` — строка 2–60 символов»
- [X] T008 [US1] В `practices/practice_04/project/templates/index.html` для поля `group` добавить `value="{{ values.group }}"` и `maxlength="20"`; ограничение: «`group` — строка 0–20 символов, может быть пустой»
- [X] T009 [US1] В `practices/practice_04/project/templates/index.html` для `textarea` `details` вывести `{{ values.details }}` внутри тега; `maxlength` не добавлять; ограничение: «`details` — строка 10–1000 символов»
- [X] T010 [US1] В `practices/practice_04/project/templates/index.html` для `select` `vibe_level` отметить `selected` по `values.vibe_level`, по умолчанию `medium`; ограничение: «`vibe_level`: `low`, `medium`, `high`»
- [X] T011 [US1] В `practices/practice_04/project/templates/index.html` под каждым полем вывести `ERROR_TEXTS[field_errors.<поле>]`, если код есть для поля `name`, `group`, `details`, `vibe_level`
- [X] T012 [US1] В `practices/practice_04/project/templates/index.html` над формой вывести блок для `form_error`: `DUPLICATE` → `ERROR_TEXTS.DUPLICATE`, `INTERNAL_ERROR` → `ERROR_TEXTS.INTERNAL_ERROR`; блок не выводится при пустом `form_error`
- [X] T013 [US1] Интеграция с логикой: в `practices/practice_04/project/server.py` маршрут `POST /report` при ошибках валидации вызывает `render_template("index.html", field_errors=..., values=..., form_error=...)` с HTTP 422; дубликат — 409 с `form_error="DUPLICATE"`; внутренняя ошибка — 500 с `form_error="INTERNAL_ERROR"`; успех — 302 на `/thanks?id={id}` без изменений. Согласовать с фичей 002

**Checkpoint**: User Story 1 работает независимо: quickstart сценарии 1–5

---

## Phase 4: User Story 2 - Страница благодарности с номером (Priority: P1)

**Goal**: `/thanks` показывает номер доноса; без номера — заглушка; несуществующий номер — экран «Донос не найден»

**Independent Test**: открыть `/thanks?id=<существующий>` (номер выводится), `/thanks` (заглушка), `/thanks?id=99` (404)

### Implementation for User Story 2

- [X] T014 [P] [US2] В `practices/practice_04/project/templates/thanks.html` при заданном `report_id` вывести «Номер доноса: {{ report_id }}.» (текст из спеки UI, экран 2)
- [X] T015 [US2] В `practices/practice_04/project/templates/thanks.html` при `report_id = None` вывести «Номер доноса не указан. Отправьте донос через форму.» и ссылку на `/`
- [X] T016 [US2] Интеграция с логикой: в `practices/practice_04/project/server.py` маршрут `GET /thanks` читает `id` из query, передаёт `report_id` (целое или `None`); при некорректном или несуществующем `id` возвращает 404 с `not_found.html` (зависит от T005)

**Checkpoint**: User Story 2 работает независимо: quickstart сценарий 6

---

## Phase 5: User Story 3 - Модерация списка (Priority: P2)

**Goal**: `/reports` с фильтрами, счётчиком, пустыми состояниями, бейджами статуса, кнопками и блоком после действия

**Independent Test**: создать доносы, сменить статус кнопкой, применить фильтр, проверить счётчик и пустые состояния

### Implementation for User Story 3

- [X] T017 [P] [US3] В `practices/practice_04/project/templates/reports.html` добавить `select` `status` (`name="status"`) с вариантами «Все статусы» (`all`), «На рассмотрении» (`new`), «Подтверждён» (`confirmed`), «Отклонён» (`rejected`); отметить `selected` по `filters.status`. Существующие фильтры `vibe_level`, `group`, `q` сохранить без изменения имён и расположения
- [X] T018 [US3] В `practices/practice_04/project/templates/reports.html` вывести «Показано {{ shown }} из {{ total }}» только при `total > 0`
- [X] T019 [US3] В `practices/practice_04/project/templates/reports.html` заменить текущую проверку `filters.applied` на два состояния: при `total = 0` — «Пока пусто. Оставьте первую заявку на главной странице.» без фильтров и счётчика; при `total > 0` и `shown = 0` — «Нет заявок, подходящих под фильтры.», фильтры и счётчик «Показано 0 из {{ total }}»
- [X] T020 [US3] В `practices/practice_04/project/templates/reports.html` для каждой записи вывести «№{{ r.id }}», `r.name`, `r.group` только если не пусто, бейдж уровня (существующий `pill`), `r.details` с переносами строк, бейдж статуса текстом `STATUS_LABELS[r.status]`
- [X] T021 [US3] В `practices/practice_04/project/templates/reports.html` для каждой записи вывести две отдельные формы `method="post"` на `/reports/{{ r.id }}/status`: «Подтвердить» (`status=confirmed`) и «Отклонить» (`status=rejected`); в каждой скрытое поле `return_query` с текущими фильтрами (`{{ {...} | urlencode }}`); кнопка с `disabled`, если `r.status` совпадает с её статусом
- [X] T022 [US3] В `practices/practice_04/project/templates/reports.html` вверху списка вывести блок при заданном `changed_id`: «Статус доноса №{{ changed_id }}: «{{ STATUS_LABELS[changed_to] }}».»; при неизвестном `changed_to` блок не выводится
- [X] T023 [US3] В `practices/practice_04/project/templates/reports.html` обновить ссылки «Экспорт CSV» и «Экспорт JSON»: `/reports/export?format=csv` и `/reports/export?format=json` плюс текущие фильтры (`status`, `vibe_level`, `group`, `q`)
- [X] T024 [US3] Интеграция с логикой: в `practices/practice_04/project/server.py` маршрут `GET /reports` передаёт `reports`, `total`, `shown`, `filters` (`status`, `vibe_level`, `group`, `q`), `changed_id`, `changed_to`; неверные `status` или `vibe_level` возвращают 400 с `error.html` (зависит от T006)
- [X] T025 [US3] Интеграция с логикой: в `practices/practice_04/project/server.py` маршрут `POST /reports/{id}/status` читает `status` и `return_query`, перенаправляет 303 на `/reports?changed_id={id}&changed_to={status}` плюс параметры фильтра из белого списка (`status`, `vibe_level`, `group`, `q`); ошибки: 400 с `error.html`, 404 с `not_found.html`, 500 с `error.html` и текстом «Не удалось изменить статус. Попробуйте ещё раз.»

**Checkpoint**: User Story 3 работает независимо: quickstart сценарии 7–11, 14

---

## Phase 6: User Story 4 - Донос не найден и общие страницы (Priority: P3)

**Goal**: 404 для номера выводит «Донос не найден», для неизвестного пути — «Страница не найдена.»

**Independent Test**: `/reports/99/status` с `status=confirmed` → «Донос не найден»; `/foo` → «Страница не найдена.»

### Implementation for User Story 4

- [X] T026 [US4] Интеграция с логикой: в `practices/practice_04/project/server.py` обработчик 404 для неизвестного пути рендерит `not_found.html` с `title="Страница не найдена."`; для маршрутов с номером — с `title="Донос не найден"` и текстом «Донос с номером {id} не найден.» при положительном целом `id`, либо «Запрошенный донос не найден.» при некорректном
- [ ] T027 [US4] Проверить в браузере с отключённым JavaScript, что `not_found.html` и `error.html` показывают заголовки и ссылки из спеки (экраны 4 и 5)

**Checkpoint**: User Story 4 работает независимо: quickstart сценарии 6 (404), 13

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: проверки, общие для всех историй

- [X] T028 [P] Проверить отсутствие `|safe` и `autoescape` в `practices/practice_04/project/templates/*.html` и отсутствие `<script>` (FR-004, FR-015)
- [ ] T029 [P] Проверить, что все тексты из шаблонов совпадают с `practices/practice_05/contract.md` и помечены в `specs/001-report-moderation-ui/spec.md` как «Тексты вне контракта», если их нет в контракте
- [ ] T030 Пройти все сценарии `specs/001-report-moderation-ui/quickstart.md` (1–14) вручную и зафиксировать результаты

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: без зависимостей. T001 блокирует T005, T006 и через них T016, T024–T026
- **Foundational (Phase 2)**: зависит от Setup; блокирует все истории
- **User Stories (Phase 3+)**: зависят от Foundational
  - US1 (P1) независима после Foundational
  - US2 (P1) независима, кроме T016 (нужен T005)
  - US3 (P2) независима, кроме T024 и T025 (нужны T006)
  - US4 (P3) зависит от T005 и T006
- **Polish (Phase N)**: после нужных историй

### Story Dependencies

- Истории могут идти параллельно: US1 затрагивает `index.html`, US2 — `thanks.html`, US3 — `reports.html`
- Интеграционные задачи (`server.py`) T013, T016, T024, T025, T026 сходятся в одном файле. Их делать
  последовательно и согласовать с фичей 002

### Parallel Opportunities

- T002, T005, T006 (разные файлы), T014 (отдельный файл от US3)
- T017, T028, T029

---

## Implementation Strategy

### MVP (User Story 1 only)

1. T001 (подтверждение R5, не блокирует US1)
2. Phase 2: T003, T004 (T005, T006 можно отложить)
3. Phase 3: T007–T013
4. **STOP и VALIDATE**: quickstart сценарии 1–5

### Incremental Delivery

1. Setup + Foundational → тексты и словари готовы
2. US1 → форма с ошибками (MVP)
3. US2 → благодарность с номером
4. US3 → список и модерация
5. US4 → страницы ошибок
6. Polish → проверки и quickstart

---

## Notes

- Расхождение в спеке UI: для текста на `/thanks` экран 2 даёт «Номер доноса: {id}.», а сценарий US2 —
  «Донос принят. Номер доноса: {номер}.». Задача T014 использует текст из таблицы экрана 2. Решение
  требует подтверждения
- `server.py` в спеке UI помечен как не затрагиваемый, а план предусматривает минимальные изменения
  маршрутов. Все задачи с `server.py` помечены «интеграция с логикой»
- Тексты вне контракта (спека UI, раздел «Тексты вне контракта») подлежат подтверждению до T029
- Атрибут `required` у полей формы из текущего шаблона остаётся открытым пунктом спеки UI
