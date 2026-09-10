# E2E-проверки

| Сценарий пользователя | Предусловия | Действие | Наблюдаемый результат | Evidence |
|---|---|---|---|---|
| Позитивный | API доступен; diff 5k | POST /api/reviews {diff} | 200 OK; JSON с `summary`, ≤3 `risks`, `checks` | OUT-1; app/api.py:8–10 |
| Негативный | diff 21k | POST /api/reviews {diff} | 413 Payload Too Large | API-1 |
| Граничный | LLM отвечает >10с | POST /api/reviews {diff} | Контролируемая ошибка, не зависает >10с | REL-1 |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): P1-02
- Что проверили и исправили сами: увязали e2e с правило‑ориентированными изменениями.
