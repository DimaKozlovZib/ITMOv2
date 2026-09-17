I will search for existing files in practices/practice02 and review tests_integration.md to plan a minimal update that adds an SEC-1 integration test scenario, along with documenting alternatives and rationale in a new file under practice02 as needed.
✱Glob "practices/practice_02/**/*" (19 matches)
→Read practices\practice_02\tree_of_thoughts\experiment.md 
I will add a new SEC-1 integration scenario row to practices/practice01/tests_integration.md and document three alternatives with a reasoned choice in practices/practice02/tree_of_thoughts/experiment.md, keeping changes minimal and consistent with existing evidence references.
← Patched practices/practice_01/tests_integration.md
| Связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| API → ReviewService | Нет лимита 20k | Отправить diff длиной 21k | HTTP 413 и сообщение о лимите | API-1; app/api.py:8–10 |
| ReviewService → LLM | Нет таймаута и обработки | Смоделировать LLM, отвечающий >10с | Контролируемый ответ по REL-1 (без подвисания) | REL-1; app/review_service.py:14–16 |

| ReviewService → LLM | Секреты не редактируются на границе (SEC-1) | Передать diff с тестовыми секретами (`token=abc123`, `-----BEGIN PRIVATE KEY-----`) и использовать мок LLM-«эхо», возвращающий полученный prompt | В ответе (эхо prompt) секреты заменены на [REDACTED]; при нарушении SEC-1 тест фиксирует утечку | SEC-1; app/review_service.py:14–16 |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): P1-02
- Что проверили и исправили сами: добавили проверки связей, соотнесли с API-1 и REL-1.
- Что проверили и исправили сами: добавили проверки связей, соотнесли с API-1 и REL-1; дополнительно добавили интеграционную проверку SEC-1 на границе ReviewService → LLM (идея обоснована в practices/practice_02/tree_of_thoughts/experiment.md).
→Read practices\practice_02\tree_of_thoughts\prompt.md 
← Patched practices/practice_02/tree_of_thoughts/experiment.md

- Решение, для которого нужны альтернативы: как оформить в `tests_integration.md` проверку правила SEC-1 (редактирование секретов). Сейчас SEC-1 проверяется только на уровне unit (`tests_unit.md`, внутреннее формирование prompt), а на уровне integration никто не проверяет саму границу «ReviewService → LLM» — то, что реально пересекает эту границу в исходящем запросе.
- Критерии выбора: не дублирует дословно unit-тест SEC-1; проверяет именно то, что пересекает границу компонентов, а не внутренний вызов функции; воспроизводима без реального внешнего LLM (через мок/перехват исходящего запроса); укладывается в существующий формат таблицы `tests_integration.md` (Связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Evidence).

## Запрос
## Запрос

```

```

## Внешне описанные альтернативы

| Альтернатива | Плюсы | Минусы | Оценка по критериям |
|---|---|---|---|
| A. Mock-LLM «эхо» (перехват prompt) на границе ReviewService → LLM | Простая реализация; точно проверяет, что выходит наружу; не требует реального LLM | Может выглядеть близко к unit, если не запускать через API; нужно аккуратно зафиксировать формат «ожидаем [REDACTED]» | (1) Не дублирует: да — проверяем исходящий запрос; (2) Граница: да; (3) Без LLM: да; (4) В таблицу: да |
| B. HTTP-адаптер-«прокси» между ReviewService и LLM, логирующий тело запроса | Имитация реальной сетевой границы; удобно расширять на другие проверки (таймауты, заголовки) | Сложнее: нужен тестовый прокси/сервер; риск утечки в логах требует маскирования в самом тесте | (1) Не дублирует: да; (2) Граница: да (сетевой уровень); (3) Без LLM: да (прокси+заглушка); (4) В таблицу: да |
| C. Контрактный тест адаптера LLM с инъекцией «вредного» диффа и инспекцией сформированного payload на слое транспорта | Проверяет не только строку prompt, но и сериализацию/формирование transport-пакета | Требует явного уровня адаптера; избыточно для учебного примера без транспорта | (1) Не дублирует: частично; (2) Граница: да, если есть адаптер; (3) Без LLM: да; (4) В таблицу: да |

```
## Выбор

- Выбранная альтернатива: A. Mock-LLM «эхо».
- Почему: минимальная сложность при точной проверке именно исходящего prompt на границе ReviewService → LLM; полностью воспроизводима без внешнего LLM и хорошо укладывается в текущую структуру tests_integration.md.
- Как проверим: подставляем заглушку LLM, которая возвращает входящий prompt как ответ; отправляем через API diff с тестовыми секретами (`token=abc123`, `-----BEGIN PRIVATE KEY-----`). Ожидаем, что в «эхо»-ответе секреты заменены на [REDACTED]. Если редактирование отключить/сломать, «эхо» вернёт исходные секреты — тест зафиксирует утечку.

```

## Что изменили в исходном артефакте

- Файл и раздел: practices/practice_01/tests_integration.md — таблица проверок.
- Изменение: добавлена строка «ReviewService → LLM | Секреты не редактируются на границе (SEC-1) | ... | В ответе (эхо prompt) секреты заменены на [REDACTED] | SEC-1; app/review_service.py:14–16».
- Что отклонили: альтернативы B и C как более сложные для учебного примера; их можно рассмотреть на этапе e2e/стейджинг.
→Read practices\practice_01\tests_integration.md 
↳ Loaded practices\practice_01\CONTEXT.md
Made the SEC-1 integration check concrete and documented the decision process.
Changes:
- practices/practice_01/tests_integration.md
- Added a new row to cover SEC-1 at the ReviewService → LLM boundary using a mock “echo” LLM:
- How: send a diff containing test secrets (token=abc123, -----BEGIN PRIVATE KEY-----) and use an echo mock that returns the received prompt.
- Expected: secrets are replaced with REDACTED; if SEC-1 is broken, the test observes leakage.
- Updated the AI usage note to reference the ToT rationale.
- practices/practice_02/tree_of_thoughts/experiment.md
- Wrote three externally described alternatives for SEC-1 integration testing with pros/cons and evaluation:
- A. Mock-LLM “echo” intercepting prompt at ReviewService → LLM
- B. HTTP proxy adapter logging outbound request body
- C. Contract test at the LLM adapter/transport layer
- Chose Alternative A as minimal and precise for this repo; explained how it detects a failure.
- Recorded what was changed in tests_integration.md and why B/C were deferred.
Resulting integration table now includes SEC-1 without duplicating the unit test and stays reproducible without a real LLM.