# Integration-проверки

| Связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| API ↔ ReviewService | Не отклоняется длинный diff | POST /api/reviews с 25 000 символов | HTTP 413 | API‑1 (CASE.md); app/api.py:8‑10 |
| ReviewService ↔ LLM | Подвисает без timeout | Эмулируем задержку LLM >10с | Контролируемый ответ без исключения | REL‑1 (CASE.md); app/review_service.py:15 |
| ReviewService ↔ LLM | Утечка секретов в prompt | Diff с тестовым секретом | prompt [REDACTED] вместо значения секрета | SEC‑1 (CASE.md); app/review_service.py:14 |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md):
- P1‑02
- Что проверили и исправили сами: оформили сценарии только по подтверждённым правилам и наблюдениям из diff.
