---
name: flask-api-check
description: Проверка API во Flask через встроенный тест-клиент. Быстрые smoke‑проверки статусов, заголовков, JSON/форм‑данных, редиректов, cookies/сессий. Используй при верификации маршрутов без запуска сервера; поддерживаются фабрики приложений, pytest‑fixtures и CLI runner.
---

# Flask API Check

Минимальный, практичный набор приёмов для проверки API во Flask без запуска внешнего сервера. Основная техника — `app.test_client()` из Flask: делаем запросы `client.get/post/...`, валидируем статус, заголовки, JSON/HTML, редиректы, куки/сессии и ошибки.

Основано на актуальной документации Flask (test client, response.json, follow_redirects, app.test_request_context, CLI runner).

## Быстрый старт

1. Получи объект приложения:

```python
# Вариант A: фабрика приложений
from myapp import create_app
app = create_app({
    'TESTING': True,  # включает режим тестирования (упрощает обработку ошибок, отключает CSRF в некоторых расширениях)
})

# Вариант B: модульный app
# from server import app
# app.config.update(TESTING=True)
```

2. Создай тест-клиент и выполни запросы:

```python
client = app.test_client()

# GET со строкой запроса
resp = client.get('/api/ping', query_string={'v': '1'})
assert resp.status_code == 200
assert resp.mimetype == 'application/json'
assert resp.json == {'status': 'ok'}  # эквивалентно resp.get_json()
```

## Базовые паттерны

- GET с query params:

```python
resp = client.get('/items', query_string={'limit': 10})
assert resp.status_code == 200
data = resp.get_json()
assert isinstance(data, list)
```

- POST JSON (автоматически ставит Content-Type: application/json):

```python
payload = {'name': 'Test', 'enabled': True}
resp = client.post('/items', json=payload)
assert resp.status_code in (200, 201)
assert resp.mimetype == 'application/json'
created = resp.json
assert created['name'] == 'Test'
```

- POST формы + проверка редиректа:

```python
resp = client.post('/report', data={'name': 'User', 'details': 'Hi'})
assert resp.status_code == 302
assert resp.headers['Location'].endswith('/thanks')

# Альтернатива: сразу следовать за редиректами
resp = client.post('/report', data={'name': 'User', 'details': 'Hi'}, follow_redirects=True)
assert resp.status_code == 200
assert 'Спасибо' in resp.get_data(as_text=True)
```

- Заголовки и content negotiation:

```python
resp = client.get('/api/data', headers={'Accept': 'application/json'})
assert resp.status_code == 200
assert resp.mimetype == 'application/json'
```

- Загрузка файлов:

```python
from io import BytesIO

data = {
    'file': (BytesIO(b'hello'), 'hello.txt'),
}
resp = client.post('/upload', data=data, content_type='multipart/form-data')
assert resp.status_code == 200
```

- Куки и сессии:

```python
# Логин сохранит cookie в client
resp = client.post('/login', data={'username': 'alice'})
assert resp.status_code in (200, 302)

# Следующий запрос выполняется с той же cookie-jar
resp = client.get('/me')
assert resp.status_code == 200
```

## Ошибки и редиректы

- Явная проверка редиректа: `assert resp.status_code == 302` и `resp.headers['Location']`.
- Для цепочек редиректов используй `follow_redirects=True`.
- Обработчики ошибок (например, 404/405) проверяй через прямые запросы:

```python
resp = client.get('/api/unknown')
assert resp.status_code == 404
```

Если в приложении есть префиксные обработчики (например, для `/api/`), валидируй формат JSON-ошибок и код статуса.

## Тесты, зависящие от контекста запроса

Когда нужно вызвать функцию, обращающуюся к `request`/`session`, но без полного диспетчинга (быстрее), используй `app.test_request_context(...)`:

```python
with app.test_request_context('/user/2/edit', method='POST', data={'name': ''}):
    messages = validate_edit_user()  # функция, обращающаяся к request
assert 'name' in messages
```

Замечание: `before_request` и маршрутизация при таком варианте не выполняются. Для полной проверки вызови реальный маршрут через `client`.

## Pytest: фикстуры

```python
# tests/conftest.py
import pytest
from myapp import create_app

@pytest.fixture
def app():
    app = create_app({'TESTING': True})
    return app

@pytest.fixture
def client(app):
    return app.test_client()
```

Использование:

```python
def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}
```

## CLI команды

Проверяй CLI через `app.test_cli_runner()`:

```python
runner = app.test_cli_runner()
result = runner.invoke(args=['hello'])
assert result.exit_code == 0
assert 'Hello' in result.output
```

## Полезные проверки

- Статус: `assert resp.status_code == 200`.
- Заголовки: `assert resp.headers['Content-Type'].startswith('application/json')`.
- Тип: `assert resp.mimetype == 'application/json'`.
- Тело JSON: `resp.json` или `resp.get_json()`.
- Тело текста/HTML: `resp.get_data(as_text=True)`.
- Локация редиректа: `resp.headers['Location']` или `resp.location`.

## Советы и подводные камни

- Всегда включай `TESTING=True`, чтобы упрощать ошибки и изоляцию.
- Для API без CSRF убедись, что расширения (например, CSRFProtect) корректно настроены для тестов.
- При ошибке парсинга JSON используй `resp.get_data(as_text=True)` для диагностики.
- Не смешивай `json=` и `data=` в одном запросе: выбери одно.
- Для больших тел запроса контролируй лимиты (`MAX_CONTENT_LENGTH`).

## Мини‑смоук план для REST API

1. `GET /health` → 200, JSON `{"status": "ok"}`.
2. `POST /items` с `json={...}` → 201/200, возвращается объект/ID.
3. `GET /items` → 200, список; фильтры через `query_string`.
4. `GET /items/<id>` → 200/404 в зависимости от наличия.
5. Ошибки: несуществующий маршрут → 404 с корректным форматом (JSON/HTML).

Эти проверки закрывают базовую доступность, сериализацию, навигацию и обработку ошибок.
