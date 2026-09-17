Plan: I will follow the prompt’s 6-step constraint to identify missing rules, classify each for unit suitability, then append unit-eligible rows to tests_unit.md for any missing unit rules (expected: QA-1, SCOPE-1, OBS-1). After that, I will update the file accordingly.
Proceeding to update tests_unit.md by appending rows for QA-1, SCOPE-1, and OBS-1.
← Patched practices/practice_01/tests_unit.md
| Требование или правило | Что проверяем изолированно | Вход | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| SEC-1 | Редактирование секретов в prompt | diff с token=abc123 и -----BEGIN PRIVATE KEY----- | В prompt все секреты заменены на [REDACTED] | SEC-1; app/review_service.py:14–16 |
| OUT-1 | Формирование структуры ответа | ответ LLM: произвольный текст | JSON содержит summary, ≤3 risks, checks | OUT-1; app/review_service.py:15–16 |
| QA-1 | Валидация рисков: включаются только подтверждённые | diff без упоминаний; risks: один без evidence/ссылки на правило | Неподтверждённый риск отклонён; остаются только риски с file,line,evidence и ссылкой на diff/правило | QA-1; CASE.md:69 |
| SCOPE-1 | Отсутствие действий (только совет) | произвольный diff; ответ LLM, предлагающий «автоприменить патч» | Результат содержит только summary, ≤3 risks, checks; нет полей/инструкций для действий (actions/merge/patch) | SCOPE-1; CASE.md:60–61,68 |
| OBS-1 | Формат логов без утечки данных | diff с секретом и ответ модели; фиктивные request_id и длительность | В лог пишутся только request_id, длительность и статус; нет содержимого diff и ответа модели | OBS-1; CASE.md:70 |

## Как использовали AI

Строка в [prompts.md](prompts.md): P1-02 I updated tests_unit.md by appending unit-level checks for the remaining repository rules that can be validated in isolation. Summary of changes:
Added QA-1: Ensures only risks confirmed by diff or repository rules are included. Input simulates an unconfirmed risk; expected result is rejection of that risk.
Added SCOPE-1: Verifies the service outputs only advisory content without action-triggering fields or instructions. Input simulates an LLM proposing to auto-apply a patch; expected result excludes any actionable fields.
Added OBS-1: Validates logging format to prevent data leakage. Input mentions diff with secret and model response; expected result is logging only request_id, duration, and status without payloads. I intentionally did not add API-1 and REL-1 in unit tests because they are already covered by integration/load tests and are not unit-isolated per the current artifacts