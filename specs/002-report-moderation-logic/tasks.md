# Tasks: Модерация доносов (сторона логики)

**Input**: `specs/002-report-moderation-logic/spec.md`
**Prerequisites**: `plan.md` (сейчас шаблон, см. T001), `spec.md`, `practices/practice_05/contract.md` (единственный источник маршрутов, полей, кодов и правил)

**Tests**: в спецификации автоматические тесты не запрошены, поэтому тестовые задачи не генерируются.
Проверка выполняется вручную: сценарии из `spec.md` через встроенный тест-клиент Flask (skill `flask-api-check`) или смоук-проверки из AGENTS.md.

**Scope**: только `practices/practice_04/project/server.py`. Шаблоны в `templates/` в эту фичу не входят
(их ведёт фича 001). Задачи, которые касаются HTML-представления, помечены «интеграция с 001».

**Организация**: задачи сгруппированы по пользовательским историям из `spec.md` (US1–US5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно (другой файл, нет зависимости от незавершённых задач). Все задачи
  этой фичи трогают один файл `server.py`, поэтому [P] почти не используется.
- **[Story]**: US1–US5 для задач историй.

---

## Phase 1: Setup

**Purpose**: подготовка перед изменением кода

- [X] T001 Заполнить `specs/002-report-moderation-logic/plan.md` по шаблону: стек Python 3.11 и Flask (`practices/practice_04/project/requirements.txt`), хранилище — память процесса (список `REPORTS`), структура — `practices/practice_04/project/server.py`. Сейчас файл содержит плейсхолдеры `[FEATURE]`, `[DATE]`, `NEEDS CLARIFICATION`
- [ ] T002 Зафиксировать текущее поведение `server.py` (без правок файлов): `POST /report` с пустыми полями (сейчас flash + redirect на `/`), `GET /reports?vibe_level=extreme` (сейчас игнорируется), `GET /reports/export?format=xml` (сейчас 400 текстом «Unknown format»)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: общая модель и утилиты, нужные всем историям

**CRITICAL**: ни одна история не начинается до завершения этой фазы

- [X] T003 В `practices/practice_04/project/server.py` добавить константы: `STATUSES = ("new", "confirmed", "rejected")`, `VIBES = ("low", "medium", "high")`, `DEFAULT_VIBE = "medium"`. Источник: contract.md, «Единые определения»
- [X] T004 В `practices/practice_04/project/server.py` заменить хранилище: записи получают поля `id` (целое, «уникально в хранилище, назначается при создании», счётчик по возрастанию), `status` (по умолчанию `new`), `created_at` (UTC, формат `YYYY-MM-DDTHH:MM:SSZ`, назначается один раз). Добавить `threading.Lock` для атомарности создания и смены статуса (contract.md, «Дублирование»: «Атомарность обеспечивается сервером»)
- [X] T005 В `practices/practice_04/project/server.py` реализовать `normalize_for_duplicate(name, details) -> tuple`: обрезка краёв, схлопывание последовательностей пробельных символов в один пробел, `casefold()`. `group` и `vibe_level` в ключ не входят (contract.md, «Дублирование»)
- [X] T006 В `practices/practice_04/project/server.py` реализовать `format_record(r) -> dict` с полями ровно `id, name, group, details, vibe_level, status, created_at` (contract.md, «Единые определения»; используется в API и экспорте JSON)
- [X] T007 В `practices/practice_04/project/server.py` реализовать `api_error(code, status, fields=None)`: тело `{"error": {"code": "<КОД>"}}`; для `VALIDATION_FAILED` добавляется `fields: [{"field", "code"}]` (contract.md, «Ошибки и формат ответов»)

**Checkpoint**: модель и утилиты готовы; история US1 может начинаться

---

## Phase 3: User Story 1 - Создание доноса с валидацией и защитой от дублей (Priority: P1) MVP

**Goal**: принимать донос, проверять поля, отклонять дубликаты, выдавать номер и статус `new`

**Independent Test**: `POST /report` с разными наборами полей; проверить код ответа, содержимое `REPORTS` и список `fields`

### Implementation for User Story 1

- [X] T008 [US1] В `practices/practice_04/project/server.py` реализовать `validate_report(form) -> list[dict]`. Обрезка по краям до проверки. Правила (contract.md, «Поля форм и ограничения» и «Ошибки»):
  - `name`: пусто → `NAME_REQUIRED`; длина вне 2–60 → `NAME_LENGTH`
  - `group`: длина больше 20 → `GROUP_LENGTH` (0–20 допустимо)
  - `details`: пусто → `DETAILS_REQUIRED`; длина вне 10–1000 → `DETAILS_LENGTH`
  - `vibe_level`: не из `low`, `medium`, `high` после `lower()` → `VIBE_INVALID`
  Возвращается по одной записи `{"field", "code"}` на каждое неверное поле; все ошибки сразу
- [X] T009 [US1] В `validate_report` (или рядом): пустой или отсутствующий `vibe_level` трактуется как `medium`; `HIGH` принимается как `high`. Источник: spec.md, «Edge Cases»
- [X] T010 [US1] В `practices/practice_04/project/server.py` реализовать `create_report(data) -> (record | None, code | None)` под `Lock`: проверка дубликата по ключу из T005 среди всех записей (включая `rejected`) → `DUPLICATE`; иначе добавить запись с `id`, `status="new"`, `created_at` (contract.md, «Дублирование»: проверка только при создании)
- [X] T011 [US1] В `practices/practice_04/project/server.py` переписать `POST /report`: вызывать `validate_report` → `create_report`. Успех: `302`, `Location: /thanks?id={id}`. Ошибка полей: `422` с `VALIDATION_FAILED` и `fields` (JSON через `api_error`). Дубликат: `409 DUPLICATE`. Непредвиденная ошибка: `500 INTERNAL_ERROR` без изменения хранилища. Удалить старый `flash`-редирект на `/` (интеграция с 001: HTML-перерисовку формы выполняет 001, T013)
- [X] T012 [US1] Проверка по spec.md, User Story 1: пустое хранилище + `name="И"` → 422 `NAME_LENGTH`; пустые `name` и `details` → два поля в `fields`; вторая отправка «иван   ПЕТРОВ» с `details` в другом регистре → 409; тот же `name` с другим `details` → 302

**Checkpoint**: US1 работает независимо: создание, валидация, дубликаты

---

## Phase 4: User Story 2 - Смена статуса доноса (Priority: P1)

**Goal**: переводить донос в `confirmed` или `rejected`; возврат в `new` запрещён; no-op — успех

**Independent Test**: создать донос, выполнить последовательность `POST /reports/{id}/status`, проверить ответы и поля записи

### Implementation for User Story 2

- [X] T013 [US2] В `practices/practice_04/project/server.py` реализовать `change_status(report_id, target) -> code | None` под `Lock`. Порядок проверок (spec.md, «Смена статуса»): сначала значение `target` (неизвестное или `new` → `INVALID_STATUS`), затем существование записи (нет → `NOT_FOUND`). Допустимые переходы (contract.md, «Смена статуса и кнопки в UI»): `new → confirmed|rejected`; `confirmed ↔ rejected`; текущий статус (no-op) — успех без изменений
- [X] T014 [US2] В `practices/practice_04/project/server.py` добавить маршрут `POST /reports/<int:report_id>/status`. Вход: поле формы `status`. Меняется только `status`; `id`, `created_at`, `name`, `group`, `details`, `vibe_level` не трогаются (spec.md, User Story 2, сценарий 8)
- [X] T015 [US2] Успех в маршруте T014 → `303`, `Location: /reports?changed_id={id}&changed_to={status}` (contract.md, «Маршруты и ответы»)
- [X] T016 [US2] Белый список `return_query` в маршруте T014: поле формы `return_query` (строка query-string) разбирается, из него берутся только `status`, `vibe_level`, `group`, `q`; остальные параметры отбрасываются. Значения добавляются к `Location` через `urlencode` (contract.md: «логика добавляет к редиректу только параметры из белого списка»)
- [X] T017 [US2] Ошибки маршрута T014 (contract.md, «Маршруты и ответы»): `400 INVALID_STATUS`, `404 NOT_FOUND`, `500 INTERNAL_ERROR`. Тело JSON через `api_error`; HTML-страницы ошибок для браузера выполняет 001 (интеграция с 001: T025)
- [X] T018 [US2] Проверка по spec.md, User Story 2: `new → confirmed` → 303; `confirmed → confirmed` → 303 без изменения; `new` как цель → 400; `approved` → 400; несуществующий `id=5` → 404; `return_query=status=all&vibe_level=high&foo=bar` → в `Location` остаются только `status` и `vibe_level`

**Checkpoint**: US2 работает независимо от US3–US5

---

## Phase 5: User Story 3 - Фильтрация списка и счётчики (Priority: P2)

**Goal**: фильтры `status`, `vibe_level`, `group`, `q` по AND; счётчики `total`, `shown`, `by_status`

**Independent Test**: набор доносов с разными полями, комбинации фильтров, сравнение `total`/`shown`/`by_status`

### Implementation for User Story 3

- [X] T019 [US3] В `practices/practice_04/project/server.py` реализовать `parse_filters(args) -> (filters, code | None)`. Правила (contract.md, «Фильтры списка и счётчики»):
  - `status`: `all|new|confirmed|rejected`; отсутствует, пусто или `all` — без фильтра; иное значение → `INVALID_STATUS`
  - `vibe_level`: `any|low|medium|high`; отсутствует, пусто или `any` — без фильтра; иное значение → `VIBE_INVALID`
  - `group`: непустая строка (после обрезки) — подстрока без учёта регистра в `group`
  - `q`: непустая строка — подстрока без учёта регистра в `name` или `details`
- [X] T020 [US3] В `practices/practice_04/project/server.py` реализовать `apply_filters(records, filters)` (AND) и `counts(records, filtered)`: `total` — все записи; `shown` — после фильтров; `by_status` — `{new, confirmed, rejected}` по всему хранилищу, нули присутствуют, фильтры не влияют
- [X] T021 [US3] В `practices/practice_04/project/server.py` переписать `GET /reports`: при ошибке фильтра → `400` (`INVALID_STATUS` или `VIBE_INVALID`) через `api_error`; при успехе — записи в порядке `id` по возрастанию, `total`, `shown`, `by_status`, а также значения фильтров. Контекст для существующего `templates/reports.html` сохранить (ключи `reports`, `filters`) и добавить `total`, `shown`, `by_status` (интеграция с 001: T024)
- [X] T022 [US3] В `practices/practice_04/project/server.py` добавить `GET /reports/<int:report_id>`: `200` с `format_record(...)` (контракт: API, JSON); несуществующий номер → `404 NOT_FOUND`
- [X] T023 [US3] Проверка по spec.md, User Story 3: 3 доноса (2 `new`, 1 `confirmed`) → `total=3`, `shown=3`, `by_status={new:2, confirmed:1, rejected:0}`; `status=confirmed` → `shown=1`, `total=3`; `status=pending` → 400; `vibe_level=extreme` → 400; пустое хранилище → нули

**Checkpoint**: US3 работает независимо; счётчики совпадают во всех комбинациях фильтров

---

## Phase 6: User Story 4 - Экспорт (Priority: P2)

**Goal**: экспорт CSV и JSON с теми же фильтрами, что и список

**Independent Test**: экспорт в обоих форматах с фильтром и без; проверка заголовков, BOM и набора полей

### Implementation for User Story 4

- [X] T024 [US4] В `practices/practice_04/project/server.py` переписать `GET /reports/export`: фильтры из T019 применяются до формирования файла; ошибки фильтров → `400` (`INVALID_STATUS`, `VIBE_INVALID`); неверный `format` → `400 INVALID_FORMAT` (JSON через `api_error`). Значение по умолчанию `format` — `csv` (spec.md, User Story 4; контракт значение по умолчанию не задаёт)
- [X] T025 [US4] CSV (contract.md, «Экспорт»): заголовок `id,name,group,vibe_level,status,created_at,details`; строки по `id` по возрастанию; UTF-8 с BOM (`\ufeff`); экранирование через модуль `csv` по RFC 4180; пустой набор — только заголовок
- [X] T026 [US4] Защита от формульной инъекции в CSV: строковые значения, начинающиеся с `=`, `+`, `-`, `@`, табуляции или `\r`, получают префикс `'` (contract.md, «Экспорт»). Применяется только к CSV; JSON не меняется
- [X] T027 [US4] Заголовки CSV-ответа: `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename=reports.csv`
- [X] T028 [US4] JSON-экспорт: массив `format_record(...)` по `id` по возрастанию; пустой набор → `[]`; `Content-Type: application/json; charset=utf-8`; `Content-Disposition: attachment; filename=reports.json`
- [X] T029 [US4] Проверка по spec.md, User Story 4: `format=xml` → 400 `INVALID_FORMAT`; `format=csv&status=pending` → 400 `INVALID_STATUS`; `format=csv&status=rejected` содержит только отклонённые; пустое хранилище → CSV только с заголовком, JSON `[]`

---

## Phase 7: User Story 5 - Просмотр доноса и несуществующие номера (Priority: P3)

**Goal**: предсказуемые ответы для отсутствующих и некорректных номеров и для неизвестных путей

**Independent Test**: запросы к `/thanks` и `/reports/{id}` с номерами, которых нет, и с неверным форматом

### Implementation for User Story 5

- [X] T030 [US5] В `practices/practice_04/project/server.py` переписать `GET /thanks`: без параметра `id` → `200` с `id=null` (контракт: «`{id: null}` при отсутствии параметра»); с `id` — если значение не положительное целое, или записи нет → `404 NOT_FOUND`; иначе `200` с номером (интеграция с 001: T016 выводит HTML)
- [X] T031 [US5] Проверить `GET /reports/<int:report_id>` (T022) на граничные значения: `abc` и `-1` не проходят конвертер маршрута → 404; `0` → 404 через поиск; `99` → 404 `NOT_FOUND` (spec.md, User Story 5)
- [X] T032 [US5] В `practices/practice_04/project/server.py` обработчик `404` для неизвестного пути: ответ `404` без кода ошибки (contract.md: «Неизвестный путь — 404»); стек-трейс и внутренние детали не выводятся. HTML-страницу «Страница не найдена.» выполняет 001
- [X] T033 [US5] Проверка по spec.md, User Story 5: `GET /thanks` без `id` → `id=null`; `GET /thanks?id=99` → 404; `GET /thanks?id=abc` → 404; `GET /thanks?id=0` → 404; `GET /foo` → 404

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T034 Проверить инварианты на всех сценариях: `new + confirmed + rejected = total`; `id`, `created_at`, `name`, `group`, `details`, `vibe_level` не меняются ни в одной операции смены статуса (spec.md, SC-003, SC-006)
- [X] T035 Проверить, что после реализации `git diff` не содержит изменений в `practices/practice_04/project/templates/` (конституция, принцип V: UI только в `templates/`, логика только в `server.py`)
- [X] T036 Проверить, что `practices/practice_04/project/requirements.txt` не изменён (конституция: новые зависимости только при необходимости и с обоснованием)
- [ ] T037 Пройти чек-лист `specs/002-report-moderation-logic/checklists/requirements.md` и отметить пункты, которые стали выполнены после реализации

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: без зависимостей. T001 блокирует планирование, но не код
- **Foundational (Phase 2)**: после Setup; блокирует все истории
- **US1 (Phase 3)**: после Phase 2; MVP
- **US2 (Phase 4)**: после Phase 2; использует `Lock` и `format_record` из T004/T006; от US1 не зависит по коду
- **US3 (Phase 5)**: после Phase 2; `parse_filters` (T019) переиспользуется в US4
- **US4 (Phase 6)**: после T019 и T020 (US3)
- **US5 (Phase 7)**: после T022 (US3) и T014 (US2)
- **Polish (Phase N)**: после всех историй

### Внутри фазы

- Все задачи трогают `server.py`, поэтому выполняются последовательно, в порядке номеров
- Конфликт с фичей 001: та же функция `POST /report`, `GET /reports`, `GET /thanks`. Фичи 001 и 002 нельзя вести параллельно без согласования порядка слияния

### Parallel Opportunities

- Практически нет: один файл. Логику можно писать параллельно с HTML-шаблонами фичи 001 при условии, что контекст шаблонов (ключи `reports`, `filters`, `total`, `shown`, `by_status`, `changed_id`, `changed_to`, `field_errors`, `form_error`) совпадает с контрактом

---

## Implementation Strategy

### MVP (User Story 1)

1. Phase 1 и Phase 2
2. Phase 3 (US1)
3. Проверка T012. Остановиться: создание и дубликаты работают без статусов и списка

### Incremental Delivery

1. Foundation → US1 (MVP)
2. US2 (смена статуса) — без неё модерация не работает
3. US3 (фильтры, счётчики)
4. US4 (экспорт)
5. US5 (крайние случаи) и Polish

---

## Открытые вопросы (блокируют отдельные задачи, не всю фичу)

1. **Выбор API-представления** для `GET /reports`, `GET /reports/{id}`, `POST /reports/{id}/status`. Контракт говорит «API — JSON», но не задаёт способ отличить API от браузера (`Accept`, отдельный префикс или другой признак). Задачи T021, T022, T011, T014 используют JSON по умолчанию, пока не решено
2. **Формат успешного ответа** `POST /reports/{id}/status` для API. Контракт описывает только 303 для браузера (см. предыдущий вывод)
3. **Формат `format` по умолчанию** для экспорта: в spec.md — `csv`, в contract.md не указан. Используется `csv`
4. **Файл `.specify/feature.json`** сейчас указывает на `specs/001-report-moderation-ui`, хотя ранее был записан `002`. Setup-скрипт выбирает фичу по нему. Для текущего запуска использована переменная `SPECIFY_FEATURE_DIRECTORY=specs/002-report-moderation-logic` без записи в файл. Файл не изменён
5. **`setup_tasks.py`** падает с `UnicodeEncodeError` при выводе в cp1251 (ошибка Windows-консоли). Обход: `PYTHONIOENCODING=utf-8`. Сам скрипт не менялся

---

## Notes

- Задачи выполнять по контракту `practices/practice_05/contract.md`; при расхождении со spec.md приоритет у контракта (он согласован и содержит решения по конфликтам)
- Каждая история должна проходить свою проверку независимо
- Отмечать `[x]` только после выполнения проверки из соответствующей задачи
