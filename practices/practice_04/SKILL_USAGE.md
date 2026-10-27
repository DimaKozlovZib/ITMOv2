# Отчет по использованию скилла flask-api-check

## Промпт

«в папке practices/practice-4 находится проект проверь его используя скилл flask-api-check»

Примечание: фактический путь проекта в репозитории — `practices/practice_04/project` (см. AGENTS.md).

## Что сделано

- Нашел проект по пути `practices/practice_04/project` и изучил ключевые файлы: `server.py`, шаблоны и `requirements.txt`.
- Подключил скилл `flask-api-check` и применил его подходы: использование `app.test_client()` без запуска внешнего сервера.
- Добавил смоук‑скрипт проверок `practices/practice_04/project/smoke_flask_api_check.py`, который покрывает:
  - `GET /` — статус 200, наличие полей формы и `action=/report`.
  - `POST /report` — редирект `302` на `/thanks` при валидных данных.
  - `GET /thanks` — статус 200, содержит «Спасибо».
  - `GET /reports` — статус 200; после отправки заявки отображаются имя, группа и уровень вайба.
  - `GET /reports/export?format=json` — корректный JSON и заголовки.
  - `GET /reports/export?format=csv` — корректный CSV и заголовки, наличие данных.
  - Фильтр `/reports?vibe_level=high` — заявка видна под фильтром.
- Установил зависимости из `requirements.txt` в виртуальной среде и выполнил смоук‑скрипт; результат: `SMOKE OK`.

## Как запустить проверки локально

1. Создать виртуальную среду и установить зависимости (из корня репозитория):

   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -r practices\practice_04\project\requirements.txt
   ```

2. Запустить смоук‑скрипт:

   ```powershell
   .venv\Scripts\python practices\practice_04\project\smoke_flask_api_check.py
   ```

Ожидаемый вывод: `SMOKE OK`.
