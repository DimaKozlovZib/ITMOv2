# UI-маршруты: что потребляет шаблоны

Источник: `practices/practice_05/contract.md`. Этот файл описывает только то, что UI получает и отправляет.
Он не дублирует контракт и не вводит новых маршрутов.

## Браузерные маршруты (HTML)

| Метод и путь | Вход от UI | Ответ | Шаблон |
|--------------|------------|-------|--------|
| `GET /` | — | 200 | `index.html` |
| `POST /report` | `name`, `group`, `details`, `vibe_level` | 302 `Location: /thanks?id={id}` | — |
| `POST /report` | то же | 422 с `field_errors`, значения сохранены | `index.html` |
| `POST /report` | то же | 409 `DUPLICATE` | `index.html` (блок над формой) |
| `POST /report` | то же | 500 `INTERNAL_ERROR` | `index.html` (блок над формой) |
| `GET /thanks?id=` | `id` (необязательный) | 200 с номером или `id = null` | `thanks.html` |
| `GET /thanks?id=` | несуществующий или некорректный `id` | 404 | `not_found.html` (R5) |
| `GET /reports?status=&vibe_level=&group=&q=` | фильтры | 200 с `reports`, `total`, `shown`, `filters` | `reports.html` |
| `GET /reports?...` | неверный `status` или `vibe_level` | 400 | `error.html`, текст «Некорректный запрос.» |
| `POST /reports/{id}/status` | `status`, `return_query` | 303 `Location: /reports?changed_id={id}&changed_to={status}&...` | — |
| `POST /reports/{id}/status` | то же | 404 `NOT_FOUND` | `not_found.html` |
| `POST /reports/{id}/status` | то же | 400 `INVALID_STATUS` | `error.html` |
| `POST /reports/{id}/status` | то же | 500 `INTERNAL_ERROR` | `error.html`, текст «Не удалось изменить статус. Попробуйте ещё раз.» |
| `GET /reports/export?format=` | фильтры | файл | ссылки «Скачать CSV/JSON» в `reports.html` |
| любой неизвестный путь | — | 404 | `not_found.html`, текст «Страница не найдена.» |

## Поля, которые шаблоны получают

- `index.html`: `field_errors` (словарь поле → код), `values` (введённые значения), `form_error` (код
  блока: `DUPLICATE`, `INTERNAL_ERROR` или пусто).
- `thanks.html`: `report_id` (целое или `None`).
- `reports.html`: `reports` (список записей), `total`, `shown`, `filters` (`status`, `vibe_level`,
  `group`, `q`, `return_query`), `changed_id`, `changed_to`.
- `not_found.html`: `title`, `message`, ссылки.

Имена переменных — предложение для реализации; контракт фиксирует поведение и HTTP-коды.

## Текст по кодам

Тексты берутся из раздела «Тексты для UI» контракта и не меняются шаблонами. Словарь хранится в `server.py`
(см. `research.md`, R3).

## Экспорт

Ссылки «Скачать CSV» и «Скачать JSON» формируются в `reports.html` из текущих фильтров. UI не обрабатывает
ответ экспорта.
