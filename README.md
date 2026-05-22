# Market Researcher

Сервис AI-аналитики компаний: сбор данных из внешних API и формирование структурированного отчёта в Markdown.

## Что делает

- Принимает запрос на естественном языке (`POST /api/v1/reports`)
- Извлекает название сущности и собирает профиль и новости через tools (реальные API, без моков)
- Синтезирует аналитический отчёт на русском (обзор, факторы, прогноз, ограничения данных)
- Обрабатывает edge cases: неизвестная компания, бренд без тикера, неоднозначное имя
- Фильтрует ценовой шум в данных tools до передачи в LLM (v1)

## Архитектура

```
HTTP (FastAPI) → LangGraph → tools → LLM (extract + synthesize)
```

**Узлы графа:**

1. `extract_company` — LLM: имя сущности, `entity_kind`, флаг неоднозначности
2. `collect_data` — детерминированно: `get_company_profile` + `get_financial_news` (`asyncio.gather`)
3. Условный переход: при отсутствии профиля и новостей → `insufficient_data` (HTTP 422)
4. `synthesize_report` — LLM: structured output → Markdown
5. `insufficient_data` — ответ без галлюцинаций

**Tools:**

| Tool | Источники |
|------|-----------|
| `get_company_profile` | yfinance → Wikipedia REST (fallback) |
| `get_financial_news` | Google News RSS → Tavily (fallback) |

Препроцессинг: `app/tools/sanitize.py` — удаление ценовых уровней из профиля и новостей.

Подробная спецификация: [docs/project-spec.md](docs/project-spec.md)

## Стек

- Python 3.11, FastAPI, uvicorn
- LangGraph, langchain-openai (или langchain-anthropic)
- yfinance, httpx, feedparser, tavily-python
- pydantic-settings, structlog

## Запуск локально

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Заполните в `.env` минимум `OPENAI_API_KEY`. Опционально: `TAVILY_API_KEY`, `HTTP_USER_AGENT`.

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Документация API: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

**Пример запроса:**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{"query": "Составь аналитический отчет по компании Apple"}'
```

При занятом порте 8000: `--port 8080`

## Docker

```bash
docker build -t market-researcher .
docker run --rm -p 8000:8000 --env-file .env market-researcher
```

## Evaluation

Скрипт прогоняет граф напрямую (без HTTP), 10 кейсов (публичные компании, бренды, неизвестные сущности):

```bash
python scripts/evaluate.py
```

Проверка: для каждого кейса есть непустой `report_md`. Exit code `0` — все кейсы прошли.

Требуется настроенный LLM API key в `.env`.

## GitHub Actions

Workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) на `push` / `pull_request`:

- **smoke** — установка зависимостей, сборка графа, `docker build`
- **e2e** — `python scripts/evaluate.py` (только если в Secrets репозитория задан `OPENAI_API_KEY`)

Опционально: `TAVILY_API_KEY` для fallback новостей в CI.

## Ключевые инженерные решения

**LangGraph вместо multi-agent (CrewAI и т.п.)**  
Линейный pipeline из 2 tools и одного отчёта. Граф задаёт стадии, ветвление `insufficient_data` и прослеживаемость в логах без лишних агентов.

**Deterministic tool calling**  
LLM не выбирает tools через ReAct. `collect_data` всегда вызывает оба tool с нормализованным `company_name`. LLM только на extract и synthesize.

**RSS → Tavily**  
Основной канал новостей — бесплатный Google News RSS. Tavily — только при пустой или недостаточной выдаче RSS.

**Препроцессинг (sanitize)**  
Ценовые уровни и суммы в заголовках новостей заменяются на `[динамика котировок]` до LLM. Строка market cap убрана из профиля. Снижает перенос «$300» в отчёт; анализ котировок — качественно, в промпте v1.

**Сущности и шум**  
Промпт: сохранение имени сущности как в запросе, фильтр нерелевантных новостей, unknown entity без подмены на известный бренд, запрет внешних знаний вне tool data.

## Ограничения

- Только `en.wikipedia.org` в fallback профиля; имя страницы должно совпадать с запросом
- RSS/Tavily могут возвращать нерелевантные заголовки при неоднозначных именах
- Качество отчёта зависит от LLM и полноты внешних источников
- Нет авторизации, БД, истории запросов, кэша
- v1: без числовых цен и капитализации в выходных данных tools

## Итог

MVP для тестового задания: FastAPI + LangGraph, реальные tools, детерминированный сбор данных, защита от типичных галлюцинаций (сущность, цены, шум). Готов к локальному запуску, Docker и smoke-eval через `scripts/evaluate.py`.
