# Анализ процесса: AS IS и TO BE

## AS IS

Пользователь отправляет HTTP POST на `/api/reviews` с `{"diff": str}`. FastAPI‑обработчик (app/api.py:8‑10) вызывает `review_service.review(payload["diff"])`. В `ReviewService.review` формируется строковый prompt: `"Review this pull request and find problems:\n{diff}"` и напрямую вызывается `llm.generate(prompt)`; возвращается `{"comment": answer}` (app/review_service.py:14‑16).

Ручные операции: проверка и принятие решения человеком — по Context Pack решение всегда принимает человек (CASE.md). Точки задержки: отсутствие таймаута при обращении к LLM (REL‑1) может привести к зависаниям. Потеря структурированности: результат — только `comment`, без `summary/risks/checks` (OUT‑1 нарушен).


## TO BE

Добавить на уровне сервиса: фильтрацию секретов перед формированием prompt (SEC‑1), проверку длины diff до 20 000 символов с ответом 413 (API‑1), таймаут вызова LLM 10 сек с контролируемым ответом (REL‑1), формирование структурированного ответа `{"summary": str, "risks": [...], "checks": [...]}` (OUT‑1). Решение по результату по‑прежнему принимает человек (SCOPE‑1).

```mermaid
flowchart LR
    A[POST /api/reviews<br/>diff] --> B[Валидация размера<br/>API-1]
    B --> C[Редакция секретов<br/>SEC-1]
    C --> D[LLM с timeout 10с<br/>REL-1]
    D --> E[Формат OUT-1:<br/>summary/risks/checks]
    E --> F[Проверка человеком<br/>SCOPE-1]
```

## Разница

| Что меняется | AS IS | TO BE | Как проверим изменение |
|---|---|---|---|
| Формат ответа | `{comment}` | `{summary, risks[<=3], checks}` | Unit на форматтер (OUT‑1) |
| Безопасность prompt | Сырый diff | Секреты вырезаны/замаскированы | Unit с тестовым token (SEC‑1) |
| Ограничение размера | Нет | 413 при >20 000 симв. | Integration с длинным diff (API‑1) |
| Надёжность LLM вызова | Нет timeout | 10с timeout и контролируемый ответ | Integration с эмуляцией таймаута (REL‑1); app/review_service.py:15 |

## Как использовали AI

- Для чего:
- Сформулировать TO BE и разницу из правил CASE.md с привязкой к AS IS.
- Тип промпта: master prompt.
- Строка в [`prompts.md`](prompts.md): P1‑02.
- Что проверили и исправили сами: сверили каждый пункт с evidence `file:line` или id правила; оставили SCOPE‑1 как ограничение.
