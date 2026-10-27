"""
Быстрые смоук‑проверки Flask‑приложения через app.test_client().

Покрывает минимальные требования из README/AGENTS.md:
- GET / — форма отображается
- POST /report — 302 Location: /thanks
- GET /thanks — 200 и текст благодарности
- GET /reports — список заявок отображается
- Экспорт /reports/export?format=csv|json — корректные заголовки и форматы
"""

from typing import Any, Dict, List

from server import app  # приложение определено модульно


def assert_contains(text: str, *needles: str) -> None:
    for n in needles:
        assert n in text, f"Ожидали найти '{n}' в ответе, но не нашли"


def run_smoke() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()

    # 1) GET /
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert_contains(html, "Имя студента", "Описание", "/report")

    # 2) POST /report — минимально валидные поля
    resp = client.post(
        "/report",
        data={
            "name": "Test User",
            "details": "Hello from smoke",
            # необязательные:
            "group": "K3140",
            "vibe_level": "high",
        },
    )
    assert resp.status_code == 302
    assert resp.headers.get("Location", "").endswith("/thanks")

    # 3) GET /thanks
    resp = client.get("/thanks")
    assert resp.status_code == 200
    assert "Спасибо" in resp.get_data(as_text=True)

    # 4) GET /reports — должна появиться заявка
    resp = client.get("/reports")
    assert resp.status_code == 200
    reports_html = resp.get_data(as_text=True)
    assert_contains(reports_html, "Заявки", "Test User", "K3140", "высокий")

    # 5) Экспорт JSON
    resp = client.get("/reports/export", query_string={"format": "json"})
    assert resp.status_code == 200
    assert resp.mimetype.startswith("application/json")
    data = resp.get_json()
    assert isinstance(data, list) and len(data) >= 1
    assert data[-1]["name"] == "Test User"

    # 6) Экспорт CSV (проверяем заголовки и содержимое)
    resp = client.get("/reports/export", query_string={"format": "csv"})
    assert resp.status_code == 200
    assert resp.mimetype.startswith("text/csv")
    csv_text = resp.get_data(as_text=True)
    # Может начинаться с BOM, поэтому проверяем подстроки
    assert "name,group,vibe_level,details" in csv_text
    assert "Test User" in csv_text and "K3140" in csv_text

    # 7) Фильтры /reports (смоук: фильтр по vibe_level)
    resp = client.get("/reports", query_string={"vibe_level": "high"})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Test User" in html


if __name__ == "__main__":
    run_smoke()
    print("SMOKE OK")
