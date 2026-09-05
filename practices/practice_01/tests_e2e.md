# E2E-проверки

| Сценарий пользователя | Предусловия | Действие | Наблюдаемый результат | Evidence |
|---|---|---|---|---|
| Позитивный | diff 1000 символов, без секретов | POST /api/reviews | 200; JSON summary/risks/checks | OUT‑1 (CASE.md); app/api.py:8‑10; app/review_service.py:16 |
| Негативный | diff 25 000 символов | POST /api/reviews | 413 Payload Too Large | API‑1 (CASE.md) |
| Граничный | LLM отвечает >10 сек | POST /api/reviews | Контролируемый ответ без исключений | REL‑1 (CASE.md); app/review_service.py:15 |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md):
- P1‑02
- Что проверили и исправили сами: синхронизировали сценарии с use case и интеграционными тестами; исключили не подтверждённые шаги.
