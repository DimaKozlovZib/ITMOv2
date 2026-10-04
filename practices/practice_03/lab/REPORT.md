# REPORT: Сравнение локальных конфигураций (Практика 3)

## Окружение
- ОС: Windows (локальная машина)
- CPU: 12th Gen Intel(R) Core(TM) i5-1235U (10C/12T)
- RAM: 23.68 GB
- GPU: Intel(R) Iris(R) Xe Graphics, VRAM ~2 GB
- Python: 3.11.8
- OpenCode CLI: 1.18.34
- Ollama: 0.34.4 (OpenAI-совместимый эндпоинт http://localhost:11434/v1)
- Модельное семейство: Qwen3 4B Instruct (локальная)
- Квантизация: Q4_K_M (по данным `ollama show`)

## Конфигурации (opencode.json в demo/)
- openai/itmo-local
  - Название: ITMO local 4k (qwen3 4b instruct)
  - Контекст (limit.context): 4096
  - Вывод (limit.output): 1024
  - Reasoning/think: отключен
  - Модель Ollama: itmo-local (qwen3:4b-instruct, Q4_K_M)
  - Параметры (ollama show): temperature=0.7, top_p=0.9, top_k=20, repeat_penalty=1.15, num_predict=512, num_ctx=4096
  - System (в модели): «Отвечай только по фактам… если данных нет — “В предоставленных материалах нет ответа”»
- openai/itmo-agent
  - Название: ITMO local 8k (qwen3 4b instruct)
  - Контекст (limit.context): 8192
  - Вывод (limit.output): 1024
  - Reasoning/think: отключен
  - Модель Ollama: itmo-agent (qwen3:4b-instruct, Q4_K_M)
  - Параметры (ollama show): temperature=0.7, top_p=0.9, top_k=20, repeat_penalty=1.15, num_predict=512, num_ctx=8192
  - System: задаётся агентом (repo-system.txt / repo-system-strict.txt)

Примечание: папка результатов приведена к единому названию: results/itmo-local и results/itmo-agent.

## Методика
- Агент: local-guide (read-only: read/glob/grep), одинаковый промпт для обеих конфигураций
- Контекст в каждом запросе: README.md, Makefile, service.py, test_service.py
- Вопросы: 5 из practices/practice_03/lab/QUESTIONS.md
- Эталоны (GOLD): practices/practice_03/lab/GOLD_ANSWERS.md (не передавались моделям)

## Результаты по вопросам

| № | Вопрос | Эталон | itmo-local | itmo-agent |
|---|---|---|---|---|
| 1 | Как запустить тесты? | make test; python3 -m unittest -v; README.md:6; Makefile:1–3 | Совпадает с эталоном; указаны README.md:6 и Makefile:3 | Совпадает с эталоном; указаны README.md:6 и Makefile:3 |
| 2 | Пустое имя подписчика | ValueError("empty name"); service.py:5–6; тест test_service.py:13–16 | Совпадает; service.py:5–6, test_service.py:13 | Совпадает; service.py:5–6 |
| 3 | Где реализован unsubscribe? | Не реализован; отсутствует в коде | Совпадает; явно указано, что нет совпадений | Совпадает; подтверждён поиск, нет реализации |
| 4 | Какая CI запускает тесты? | Сведений нет | Совпадает; «нет сведений», обоснование по README/Makefile | Совпадает; «нет сведений», обоснование по README/Makefile |
| 5 | Сохраняются ли подписки? | Не сохраняются; in-memory; README.md:2; service.py:1 | Совпадает; ссылки на service.py:1, test_service.py:7, README.md:3 | Совпадает; ссылки на service.py:1, test_service.py:7, README.md:2 |

Итого: обе конфигурации корректно ответили на все 5 вопросов, без галлюцинаций. Ложная предпосылка (unsubscribe) распознана, отсутствие сведений по CI указано корректно, ссылки на строки присутствуют.

## Выводы и выбор конфигурации
- Точность: одинаково высокая на данном наборе вопросов (5/5 корректно у обеих).
- Поведение:
  - itmo-local: использует встроенный строгий system из Modelfile; ответы краткие, «по коду».
  - itmo-agent: опирается на системный промпт агента; также даёт корректные и сдержанные ответы.
- Рекомендация выбора:
  - Для небольшого контекста (быстрые локальные проверки, короткие файлы) — itmo-local (4k).
  - Для задач с большим контекстом/длинными файлами — itmo-agent (8k).

## Проблемы/ограничения
- Папка результатов была с опечаткой (itmo-locale) — исправлено на itmo-local.
- В отчёте не сравнивались метрики скорости/латентности, т.к. не снимались тайминги в автоматическом режиме.

## Приложение: ссылки на артефакты
- Эталоны: practices/practice_03/lab/GOLD_ANSWERS.md
- Ответы моделей:
  - results/itmo-local/Q1.md … Q5.md
  - results/itmo-agent/Q1.md … Q5.md
