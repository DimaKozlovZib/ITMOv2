# Feature Specification: Модерация доносов (сторона логики)

**Feature Branch**: не создана (хук git не настроен, `.specify/extensions.yml` отсутствует)

**Created**: 2026-10-22

**Status**: Draft (приведена к `practices/practice_05/contract.md`)

**Input**: User description: "Фича «Модерация доносов», ТОЛЬКО сторона логики. Проект: Flask, данные в памяти (список REPORTS), сейчас поля name, group, details, vibe_level."

**Область действия**: серверная логика и контракт маршрутов в объёме `practices/practice_05/contract.md`.
Вёрстка и тексты экранов здесь не описываются; тексты для UI заданы контрактом и сопоставляются по кодам.
Связанная спецификация UI: `specs/001-report-moderation-ui/spec.md`.

## Исходное состояние

- Заявки хранятся в списке в памяти процесса. Текущие записи содержат `name`, `group`, `details`, `vibe_level`.
- `GET /reports` фильтрует по `vibe_level`, `group` и `q`.
- `GET /reports/export` экспортирует записи в CSV или JSON.
- Успешная отправка `POST /report` даёт 302 на `/thanks`.

Изменения относительно этого состояния отмечены словом «Изменение».

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Создание доноса с валидацией и защитой от дублей (Priority: P1)

Логика принимает донос, проверяет поля, отклоняет некорректные данные и дубликаты. Принятый донос получает
номер и статус `new`.

**Independent Test**: отправить `POST /report` с разными наборами полей и проверить код ответа, содержимое
хранилища и список ошибок.

**Acceptance Scenarios**:

1. **Given** хранилище пусто, **When** приходит `name="Иван"`, `details="Опоздал на пару сегодня"`, `group`
   и `vibe_level` не переданы, **Then** создаётся запись с `status=new`, `vibe_level=medium`, `group=""`;
   ответ 302 с `Location: /thanks?id={id}`.
2. **Given** `name="И"`, **When** отправляется форма, **Then** ответ 422 `VALIDATION_FAILED` с полем
   `{"field": "name", "code": "NAME_LENGTH"}`; запись не создаётся.
3. **Given** `name` и `details` пусты, **When** отправляется форма, **Then** ответ 422 `VALIDATION_FAILED`
   с двумя полями: `NAME_REQUIRED` для `name` и `DETAILS_REQUIRED` для `details`.
4. **Given** запись `name="Иван Петров"`, `details="Опоздал на пару"`, **When** приходит
   `name="  иван   ПЕТРОВ "`, `details="опоздал на пару"`, **Then** ответ 409 `DUPLICATE`; новая запись не создаётся.
5. **Given** та же запись, **When** приходит та же `name` с другим `details`, **Then** запись создаётся.
6. **Given** `vibe_level="extreme"`, **When** отправляется форма, **Then** ответ 422 `VALIDATION_FAILED`
   с полем `{"field": "vibe_level", "code": "VIBE_INVALID"}`.
7. **Given** запись `name="Иван Петров"`, `details="Опоздал на пару"` уже отклонена, **When** приходит та же
   пара, **Then** ответ 409 `DUPLICATE` (ключ включает все статусы).
8. **Given** два одинаковых запроса приходят одновременно, **When** обрабатываются, **Then** ровно один создаёт
   запись, второй получает 409 `DUPLICATE`.

---

### User Story 2 - Смена статуса доноса (Priority: P1)

Модератор переводит донос в `confirmed` или `rejected`. Переход между `confirmed` и `rejected` свободный.
Возврат в `new` запрещён.

**Independent Test**: создать донос, выполнить последовательность смен статуса, проверить ответы и хранилище.

**Acceptance Scenarios**:

1. **Given** донос `id=1` со статусом `new`, **When** `POST /reports/1/status` с `status=confirmed`, **Then**
   статус становится `confirmed`; ответ 303 с `Location: /reports?changed_id=1&changed_to=confirmed`.
2. **Given** донос `confirmed`, **When** приходит `status=rejected`, **Then** статус `rejected`, ответ 303.
3. **Given** донос `rejected`, **When** приходит `status=confirmed`, **Then** статус `confirmed`, ответ 303.
4. **Given** донос `confirmed`, **When** приходит `status=confirmed`, **Then** статус не меняется, ответ 303
   (no-op считается успехом).
5. **Given** любой донос, **When** приходит `status=new`, **Then** ответ 400 `INVALID_STATUS`; статус не меняется.
6. **Given** любой донос, **When** приходит `status=approved`, **Then** ответ 400 `INVALID_STATUS`.
7. **Given** донос `id=5` не существует, **When** `POST /reports/5/status` с `status=confirmed`, **Then**
   ответ 404 `NOT_FOUND`.
8. **Given** успешная смена статуса, **Then** меняется только `status`; `id`, `created_at`, `name`, `group`,
   `details`, `vibe_level` не меняются.
9. **Given** `POST /reports/1/status` с `return_query` (см. «Маршруты»), **When** смена успешна, **Then**
   редирект содержит параметры `changed_id`, `changed_to` и только параметры белого списка из `return_query`.

---

### User Story 3 - Фильтрация списка и счётчики (Priority: P2)

Модератор фильтрует список по статусу, уровню, группе и строке поиска одновременно. Счётчики считаются по всему
хранилищу.

**Acceptance Scenarios**:

1. **Given** 3 доноса (2 `new`, 1 `confirmed`), **When** `GET /reports` без параметров, **Then** 3 записи,
   `total=3`, `shown=3`, `by_status={new: 2, confirmed: 1, rejected: 0}`.
2. **Given** те же доносы, **When** `GET /reports?status=confirmed`, **Then** 1 запись, `total=3`, `shown=1`,
   `by_status` не изменился.
3. **Given** `GET /reports?status=new&vibe_level=high&group=it`, **Then** возвращаются только записи, которые
   удовлетворяют всем трём условиям (AND).
4. **Given** фильтры, не совпадающие ни с одной записью, **Then** 200, `reports=[]`, `shown=0`, `total` — общее количество.
5. **Given** пустое хранилище, **When** `GET /reports`, **Then** 200, `reports=[]`, `total=0`, `shown=0`,
   `by_status` с нулями.
6. **Given** `GET /reports?status=pending`, **Then** 400 `INVALID_STATUS`.
7. **Given** `GET /reports?vibe_level=extreme`, **Then** 400 `VIBE_INVALID`.

---

### User Story 4 - Экспорт (Priority: P2)

Модератор выгружает записи в CSV или JSON с теми же фильтрами, что и список.

**Acceptance Scenarios**:

1. **Given** 2 доноса, **When** `GET /reports/export?format=csv`, **Then** 200, CSV с заголовком
   `id,name,group,vibe_level,status,created_at,details` и 2 строками, по `id` по возрастанию.
2. **Given** 2 доноса, **When** `GET /reports/export?format=json`, **Then** 200, JSON-массив из 2 записей.
3. **Given** доносы разных статусов, **When** `GET /reports/export?format=csv&status=rejected`, **Then** в файле
   только отклонённые.
4. **Given** пустое хранилище, **When** экспорт в CSV, **Then** файл содержит только строку заголовка; в JSON `[]`.
5. **Given** `GET /reports/export?format=xml`, **Then** 400 `INVALID_FORMAT`.
6. **Given** `GET /reports/export?format=csv&status=pending`, **Then** 400 `INVALID_STATUS`.

---

### User Story 5 - Просмотр доноса и несуществующие номера (Priority: P3)

**Acceptance Scenarios**:

1. **Given** донос `id=1`, **When** `GET /reports/1`, **Then** 200, JSON-запись.
2. **Given** доноса `id=99` нет, **When** `GET /reports/99`, **Then** 404 `NOT_FOUND`.
3. **Given** `GET /reports/abc`, `GET /reports/0`, `GET /reports/-1`, **Then** 404 `NOT_FOUND`.
4. **Given** `GET /thanks` без `id`, **Then** 200 с `id=null`.
5. **Given** `GET /thanks?id=99` или `GET /thanks?id=abc`, **Then** 404 `NOT_FOUND`.
6. **Given** путь, которого нет (`/foo`), **Then** 404 без кода ошибки; для браузера страница «Страница не найдена.».

---

### Edge Cases

- `name`: 1 символ → `NAME_LENGTH`; 2 и 60 → допустимо; 61 → `NAME_LENGTH`.
- `group`: 0 и 20 символов → допустимо; 21 → `GROUP_LENGTH`.
- `details`: 9 символов → `DETAILS_LENGTH`; 10 и 1000 → допустимо; 1001 → `DETAILS_LENGTH`.
- Строка из одних пробелов после обрезки пустая: `NAME_REQUIRED` или `DETAILS_REQUIRED`.
- Внутренние пробелы и переносы строк в `details` сохраняются.
- Значения с HTML (`<b>текст</b>`) сохраняются как введены; экранирование выполняет UI при выводе.
- Если `vibe_level` не передан, записи присваивается `medium`.

## Requirements *(mandatory)*

### Модель данных

| Поле | Тип | Правила | По умолчанию |
|------|-----|---------|--------------|
| `id` | целое | уникально в хранилище, назначается при создании | — |
| `name` | строка | обязательно; 2–60 символов после обрезки | — |
| `group` | строка | необязательно; 0–20 символов после обрезки | `""` |
| `details` | строка | обязательно; 10–1000 символов после обрезки | — |
| `vibe_level` | перечисление | `low`, `medium`, `high` | `medium` |
| `status` | перечисление | `new`, `confirmed`, `rejected` | `new` |
| `created_at` | дата-время | назначается при создании, не меняется | — |

Изменение: поля `id`, `status`, `created_at` добавляются. Хранилище в памяти процесса; данные не
переживают перезапуск (контекст платформы практики 4).

### Правила валидации (создание)

Значения обрезаются по краям до проверки.

| Поле | Условие | Код поля |
|------|---------|----------|
| `name` | пусто | `NAME_REQUIRED` |
| `name` | длина вне 2–60 | `NAME_LENGTH` |
| `group` | длина больше 20 | `GROUP_LENGTH` |
| `details` | пусто | `DETAILS_REQUIRED` |
| `details` | длина вне 10–1000 | `DETAILS_LENGTH` |
| `vibe_level` | не из `low`, `medium`, `high` | `VIBE_INVALID` |

Ошибки возвращаются в `fields` (по одной записи на каждое неверное поле).

### Защита от дублей

**Ключ**: пара (`name`, `details`), нормализованная так:
1. Обрезка пробелов по краям.
2. Последовательности пробельных символов заменяются одним пробелом.
3. `casefold` по Unicode.

`group` и `vibe_level` в ключ не входят.

- Область проверки: все записи, включая `rejected`.
- Проверка только при создании; смена статуса дубликаты не создаёт.
- Проверка и сохранение атомарны: два одинаковых запроса не создают две записи.
- Результат: 409 `DUPLICATE`.

### Смена статуса

| Из \ В | `new` | `confirmed` | `rejected` |
|--------|-------|-------------|------------|
| `new` | нет | да | да |
| `confirmed` | нет | no-op (успех) | да |
| `rejected` | нет | да | no-op (успех) |

- Неизвестное значение и `new` в качестве цели: 400 `INVALID_STATUS`.
- No-op возвращает успех 303 без изменения данных.
- Меняется только `status`.

### Фильтрация списка

Параметры `GET /reports`, объединяются через AND:

| Параметр | Значения | Поведение |
|----------|----------|-----------|
| `status` | `all`, `new`, `confirmed`, `rejected` | отсутствует, пусто или `all` — без фильтра; иначе точное совпадение |
| `vibe_level` | `any`, `low`, `medium`, `high` | отсутствует, пусто или `any` — без фильтра; иначе точное совпадение |
| `group` | непустая строка | подстрока без учёта регистра в `group` |
| `q` | непустая строка | подстрока без учёта регистра в `name` или `details` |

Неверный `status` → 400 `INVALID_STATUS`; неверный `vibe_level` → 400 `VIBE_INVALID`.
Изменение: раньше неизвестный `vibe_level` игнорировался, теперь 400.

### Счётчики

- `total` — все записи; фильтры не влияют.
- `shown` — записи после фильтров.
- `by_status` — количества `new`, `confirmed`, `rejected` по всему хранилищу; фильтры не влияют.
- Инвариант: `new + confirmed + rejected = total`.

### Маршруты

| Метод и путь | Вход | Успех | Ошибки |
|--------------|------|-------|--------|
| `GET /` | — | форма | — |
| `POST /report` | `name`, `group`, `details`, `vibe_level` | 302 → `/thanks?id={id}` | 422 `VALIDATION_FAILED`; 409 `DUPLICATE`; 500 `INTERNAL_ERROR` |
| `GET /thanks` | `id` (необязательный) | 200: `{id}`; без параметра `{id: null}` | 404 `NOT_FOUND` при несуществующем или некорректном `id` |
| `GET /reports` | `status`, `vibe_level`, `group`, `q` | 200: список, `total`, `shown`, `by_status` | 400 `INVALID_STATUS`, `VIBE_INVALID` |
| `GET /reports/{id}` | путь `id` | 200: JSON-запись (только API) | 404 `NOT_FOUND` |
| `POST /reports/{id}/status` | `status`, `return_query` (необязательный) | 303 → `/reports?changed_id={id}&changed_to={status}` + параметры белого списка из `return_query` | 400 `INVALID_STATUS`; 404 `NOT_FOUND`; 500 `INTERNAL_ERROR` |
| `GET /reports/export` | `format`, `status`, `vibe_level`, `group`, `q` | 200: CSV или JSON | 400 `INVALID_FORMAT`, `INVALID_STATUS`, `VIBE_INVALID` |

- `return_query`: логика берёт из него только `status`, `vibe_level`, `group`, `q`; остальные параметры отбрасываются.
- Неизвестный путь: 404 (браузер — страница «Страница не найдена.»).

Изменение: `GET /reports/{id}`, `POST /reports/{id}/status` и `GET /reports/export` — расширения, согласованы
контрактом для следующего этапа.

### Формат ошибок

Представления по контракту:

- **API** (JSON):
  - Общий случай: `{"error": {"code": "<КОД>"}}`.
  - 422: `{"error": {"code": "VALIDATION_FAILED", "fields": [{"field": "name", "code": "NAME_LENGTH"}]}}`.
- **Браузер** (HTML): те же HTTP-коды; для `POST /report` 422 — перерисовка формы с введёнными значениями
  (значения берутся из `request.form`).

Коды верхнего уровня: `VALIDATION_FAILED` (422), `DUPLICATE` (409), `INVALID_STATUS` (400),
`VIBE_INVALID` (400), `INVALID_FORMAT` (400), `NOT_FOUND` (404), `INTERNAL_ERROR` (500).
Коды полей внутри `fields`: `NAME_REQUIRED`, `NAME_LENGTH`, `GROUP_LENGTH`, `DETAILS_REQUIRED`,
`DETAILS_LENGTH`, `VIBE_INVALID`.

Тексты сообщений логика не возвращает. Соответствие кодов текстам задано в контракте и применяется UI.

### Экспорт

- Маршрут: `GET /reports/export?format=csv|json`. Фильтры как у `GET /reports`. Порядок: по `id` по возрастанию.
- **CSV**:
  - Заголовок: `id,name,group,vibe_level,status,created_at,details`.
  - UTF-8 с BOM; `Content-Type: text/csv; charset=utf-8`; `Content-Disposition: attachment; filename=reports.csv`.
  - Экранирование по RFC 4180.
  - Значения, начинающиеся с `=`, `+`, `-`, `@`, табуляции или `\r`, получают префикс `'`.
- **JSON**:
  - Массив записей с полями модели.
  - `Content-Type: application/json; charset=utf-8`; `Content-Disposition: attachment; filename=reports.json`.

### Ключевые сущности

- **Донос**: запись с полями модели. Создаётся логикой; меняет только `status`.
- **Статус**: `new`, `confirmed`, `rejected`.
- **Ключ дубликата**: производное значение от `name` и `details`, не хранится отдельно.

## Success Criteria *(mandatory)*

- **SC-001**: Граничные значения длин (1, 2, 60, 61 для имени; 20, 21 для группы; 9, 10, 1000, 1001 для описания)
  проверяются с ожидаемым результатом в 100% проверок.
- **SC-002**: Две отправки, различающиеся только регистром, пробелами или переносами строк в `name` и `details`,
  никогда не создают две записи в 100% проверок.
- **SC-003**: `total`, `shown`, `by_status` совпадают с данными во всех комбинациях фильтров в 100% проверок.
- **SC-004**: Для отсутствующего номера и неверного статуса ответ соответствует таблице маршрутов в 100% проверок.
- **SC-005**: CSV начинается с BOM и открывается с кириллицей в 100% проверок.
- **SC-006**: После создания `id`, `created_at`, `name`, `group`, `details`, `vibe_level` не меняются ни в одной операции.

## Assumptions

- Хранилище — память процесса (контракт, раздел «Контекст»); потеря данных при перезапуске ожидаема.
- Контроль доступа отсутствует; `GET /reports` и `GET /reports/{id}` отдают `details` любому (контракт, «Безопасность»).
- Экранирование выводимых значений выполняет UI.

## Решения контракта

Все шесть открытых вопросов предыдущей версии спеки закрыты контрактом (`practices/practice_05/contract.md`):

1. Ключ дубликата включает `rejected` — контракт, «Дублирование».
2. Неверный `vibe_level` в фильтре → 400 — контракт, «Фильтры».
3. Защита CSV от формульной инъекции — контракт, «Экспорт».
4. `GET /reports/{id}` и `POST /reports/{id}/status` согласованы — контракт, «Маршруты».
5. Смена статуса → 303 для браузера; JSON-ответа на успех контракт не задаёт.
6. Представления `GET /reports`: HTML для браузера, структура данных для API — контракт, «Маршруты».

## Что я ожидаю от UI

**UI отправляет:**
- `POST /report`: `name`, `group`, `details`, `vibe_level` (select; по умолчанию `medium`). `group` с `maxlength="20"`,
  `name` с `maxlength="60"`; `details` без `maxlength`.
- `POST /reports/{id}/status`: `status` (`confirmed` или `rejected`) и скрытое поле `return_query` с текущими фильтрами.
  Номер берётся из пути.
- `GET /thanks?id={id}`: номер, полученный после создания.
- `GET /reports`: `status` (`all` или отсутствует), `vibe_level` (`any` или отсутствует), `group`, `q`.
- `GET /reports/export?format=csv|json`: текущие фильтры.

**UI получает и показывает:**
- 422 `VALIDATION_FAILED`: коды из `fields[].code` выводятся под полями; значения полей остаются в форме (берутся из запроса).
- 409 `DUPLICATE`: блок над формой; значения сохраняются.
- 500 `INTERNAL_ERROR`: блок над формой.
- 302 на `/thanks?id={id}`: переход.
- `GET /thanks` без `id` или с `id=null`: текст-заглушка; 404: страница «Донос не найден».
- `GET /reports`: список, `total`, `shown`, `by_status`. Пустой список — `total=0`; пустой фильтр — `total>0` и `shown=0`.
- 303 после смены статуса: сообщение по `changed_id` и `changed_to` (нейтральный текст из контракта); фильтры восстанавливаются из параметров белого списка.
- 404 для номера: страница «Донос не найден».
- 400 `INVALID_STATUS`, `VIBE_INVALID`, `INVALID_FORMAT`: страница «Некорректный запрос.».
- Неизвестный путь: страница «Страница не найдена.».

**UI выставляет:**
- Текущая кнопка статуса выводится с `disabled`. Логика no-op не запрещает, но UI его не инициирует.
- Все значения, приходящие из логики, экранируются.
- Счётчики и признаки пустоты UI вычисляет по `total` и `shown`; проверки длины и дубликатов UI не делает, сервер окончателен.
