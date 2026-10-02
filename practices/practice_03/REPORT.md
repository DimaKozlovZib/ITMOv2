# Отчёт: локальные модели

Отчёт ведёт OpenCode по фактическим результатам команд и вашим сообщениям в чате. Поручите агенту заполнить разделы и показать diff. Выводы студента он записывает после обсуждения; отсутствующие измерения отмечает как невыполненные.

## Окружение

ОС / CPU / GPU / RAM / VRAM / свободный диск: Windows; CPU/GPU см. системный отчёт. Точную конфигурацию фиксируем в ходе проверки.
Версии (см. results/*.txt): opencode 1.18.33; ollama 0.34.4; Python 3.12.x.
Модель: itmo-agent (parent: qwen3.5:4b), формат gguf, quant Q4_K_M.
Фактический контекст (ollama show): до 262144 токенов; агентный профиль запрашивает 65536.
Endpoint: http://localhost:11434/v1 (OpenAI-совместимый клиент к локальному серверу Ollama), локально, без внешних подключений.
Почему выбрана конфигурация: доступная по ресурсам, стабильный запуск локального API, совместимость с OpenCode.

## Сравнение семейств

| Разработчик / модель | Задача | Параметры / формат | Лицензия | Язык / tools | Источник |
|---|---|---|---|---|---|
| Qwen3.5 4B (itmo-agent parent) | Универсальная чат-задача | gguf Q4_K_M | См. карточку модели Qwen (условия от Alibaba/Qwen) | RU/EN, tools | ollama show |
| Qwen2.5 Coder 7B | Кодирование | gguf Q4_K_M | См. карточку модели Qwen (условия от Alibaba/Qwen) | EN, tools | ollama list |

## Воспроизведение

Команды и файлы конфигурации:
- demo/opencode.json: провайдер openai с baseURL http://localhost:11434/v1; модели openai/itmo-agent; агенты local-guide и local-guide-b.
- lab/Modelfile, Modelfile.agent: FROM qwen3.5:4b; параметры контекста (4096/65536).
- lab/system.txt и lab/system_alt.txt — два system prompt для A/B.
Подтверждение локального endpoint и скачанных весов:
Артефакты (текст):
- results/ollama_models.txt (GET /v1/models)
- results/ollama_list.txt (ollama list)
- results/ollama_show_itmo-agent.txt (ollama show itmo-agent)
- results/ollama_ps.txt (ollama ps)
Проверка без сети после подготовки:
Если работали в паре, чей компьютер и почему:
Характеристики устройства (см. results/env.txt):
- OS: Microsoft Windows 10 Home 10.0.19045
- CPU: 12th Gen Intel(R) Core(TM) i5-1235U (10 cores, 12 threads)
- RAM: ~23.68 GB
- GPU/VRAM: см. полный файл env.txt

## Эксперимент

Фактор A/B: system prompt (A: system.txt; B: system_alt.txt). Модель/квантизация/контекст/вход/лимиты/temperature/seed одинаковые.
Неизменные условия: model=itmo-agent; temperature=0.2; seed=42; think=false; num_ctx=4096; num_predict=512.
Контрольный вопрос (API): «Какая CI-система запускает тесты проекта?» на контексте demo/README.md.
Результаты API:
- baseline (без system): склонность к гипотезам о CI (выдумывание).
- A (system.txt): «В предоставленных материалах нет ответа» с основанием.
- B (system_alt.txt): «В предоставленных материалах нет ответа» (строже; короче); wall_seconds ниже.
Детали в results/system_A_s42.json и results/system_B_s42.json.

Пять вопросов (локальный API через Ollama): использованы вопросы из lab/QUESTIONS.md. Эталоны и file:line — practices/practice_03/lab/results/questions_demo.md.
Итоги A/B (сводка):
1. Как запустить тесты? A: make test + Makefile. B: то же, краткий формат. Верно A/B.
2. Пустое имя: A: ValueError("empty name"). B: то же. Верно A/B.
3. unsubscribe: A: отсутствует (ложная предпосылка). B: то же. Верно A/B.
4. CI-система: A: «нет сведений». B: «нет сведений», формат 1)/2). Верно A/B.
5. Сохранность подписок: A: не сохраняются (память процесса). B: то же. Верно A/B.
Артефакты: results/questions_A_q{1..5}.json, results/questions_B_q{1..5}.json.

## Скорость

Холодный старт отдельно: первый запуск длиннее (см. wall_seconds в system_A_s42.json).
Три прогретых повтора и медиана: собраны A_s42_r{1..3}.json и B_s42_r{1..3}.json; точные медианы вычислены скриптом lab/stats_speed.py и сохранены в results/speed_summary.json.
Итог: A — median wall ≈ 15.019s, median decode ≈ 6.597 tok/s; B — median wall ≈ 3.438s, median decode ≈ 7.933 tok/s.
Единицы и метод замера: wall_seconds по перф-таймеру, decode_tokens_per_second = eval_count / (eval_duration сек).
TTFT: не измеряется (ответ не потоковый).

## Вывод

Ошибка или ограничение: без system prompt модель склонна к фантазиям о CI; строгий system устраняет выдумывание.
Как проверили: сравнение baseline vs A/B на одном вопросе (API) с фиксированными параметрами.
Выбранная конфигурация: system_alt.txt — короче, быстрее, без фантазий. Отмечено, что в единичном прогоне B ответ не соблюдал требуемый формат (1)/2)); в финальной конфигурации это учитываем и контролируем.
Что осталось непроверенным: TTFT не оценивался.
