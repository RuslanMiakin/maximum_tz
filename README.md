# Market Researcher

MVP AI-исследователя компаний (тестовое задание): сбор данных из внешних API и структурированный отчёт в Markdown. Тот же каркас (LangGraph + tools + наблюдаемость) — зачаток оркестрации для **personal director / multi-agent** сценариев венчурного фонда; ниже — как это стыкуется с продуктом, не только с ТЗ.

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
| `get_company_profile` | yfinance → Wikipedia REST (en/ru по языку имени, fallback) |
| `get_financial_news` | Google News RSS → Tavily (fallback) |

Препроцессинг: `app/tools/sanitize.py` — удаление ценовых уровней из профиля и новостей.

Подробная спецификация: [docs/project-spec.md](docs/project-spec.md)

## Связь с multi-agent (венчурный фонд)

В тестовом задании — один сценарий «company research». В продукте фонда это **один capability-срез** более широкой системы: оркестратор + ролевые агенты + общее состояние + политики на tools.

**Что уже заложено в этом репозитории (паттерны под прод):**

| Слой в MVP | Роль в multi-agent фонда |
|------------|-------------------------|
| `extract_company` (LLM) | Router / intent: кого анализируем, бренд vs эмитент, неоднозначность |
| `collect_data` (детерминированные tools) | Data agents: обязательные внешние источники с audit (`sources_used`) |
| `synthesize_report` (LLM + schema) | Analyst agent: вывод только из payload, structured output |
| `insufficient_data` + HTTP 422 | Governance: не галлюцинировать при слабых данных, эскалация / отказ |

**Эволюция под венчурный фонгд (устно / roadmap, не в scope теста):**

```
Сейчас:     запрос → extract → collect (profile + news) → synthesize | insufficient

Фонд v1:    router → [ResearchAgent | PortfolioAgent | MeetingPrepAgent | …]
            → shared state / memory → synthesis → HITL при низкой уверенности

Фонд v2:    права на tools по роли, кэш, event-driven задачи, полный trace в observability
```

- **Фиксированный граф на compliance-шагах** (сбор фактов, due diligence) — предсказуемость, аудит, правильные аргументы в API.
- **ReAct / LLM-tool-loop** — для exploratory задач (широкий поиск, уточняющие вопросы), не вместо обязательного пайплайна сбора данных.
- Текущий `collect_data` — не «отказ от multi-agent», а **policy layer**: для сценария «профиль + новости по сущности» оба tool вызываются всегда, как в ТЗ; router в v1 фонда решает, *какой* сценарий запустить.

## Стек

- Python 3.11, FastAPI, uvicorn
- LangGraph
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
- **e2e** — `python scripts/evaluate.py` (только если в Secrets задан `OPENAI_API_KEY`)

**Важно:** файл `.env` в git не попадает (см. `.gitignore`). На GitHub переменные задаются через **Secrets**, не через коммит `.env`:

| Secret | Обязателен | Назначение |
|--------|------------|------------|
| `OPENAI_API_KEY` | да (для e2e) | LLM |
| `TAVILY_API_KEY` | нет | fallback новостей |

В job **e2e** workflow создаёт `.env` на раннере из Secrets и дублирует переменные в `env:` — так же читает `pydantic-settings` и `load_dotenv` в `evaluate.py`.

**Docker:** `.env` в образ не копируется. Передача при запуске:

```bash
docker run --rm -p 8000:8000 --env-file .env market-researcher
```

## Почему выбран такой подход

Обоснование под **ТЗ** и под **роль архитектора agentic-системы в фонде** (надёжность важнее «чистого ReAct» в демо).

**FastAPI + HTTP API**  
Явный контракт: валидация, OpenAPI, `422` при нехватке данных. Для фонда тот же слой — gateway к оркестратору (сейчас один endpoint `reports`, дальше — роутинг по intent).

**LangGraph как orchestration layer**  
Граф = явные стадии, ветвления и общий state — база для multi-agent: новые узлы = новые роли (research, portfolio, calendar), без смены runtime. CrewAI/несколько чат-агентов на **два** data-tool в тесте дали бы лишнюю latency и шум в логах без выигрыша по ТЗ.

**Deterministic `collect_data` (не ReAct на сборе данных)**  
ТЗ: после извлечения сущности всегда `get_company_profile` и `get_financial_news`, аргумент — `company_name` (`Apple`), не весь промпт. В проде фонда тот же принцип на обязательных шагах (факты, compliance). ReAct уместен там, где план **не** фиксирован; здесь — осознанный, повторяемый pipeline + trace в консоли (`Думаю…` → вызовы tools → `Получил ответ…` → `Формирую отчет…`).

**RSS → Tavily для новостей**  
RSS бесплатен и без квоты — основной канал. Tavily только при пустой/скудной выдаче: экономия лимита и соответствие ТЗ (реальный API + fallback).

**yfinance → Wikipedia для профиля**  
Публичные компании закрываются тикером и структурными полями. Wikipedia — fallback без ключа; для кириллицы в запросе используется `ru.wikipedia.org`, для латиницы — `en.wikipedia.org` (без транслитерации имён).

**Препроцессинг цен в tools (sanitize, v1)**  
Заголовки RSS часто содержат уровни цен (`$300`), модель переносила их в отчёт. В v1 цены режутся в tools, в отчёте — качественная динамика; в промпте запрет чисел вне tool data.

**Промпт и structured output**  
Отчёт через Pydantic → Markdown: стабильные секции по ТЗ. Отдельные правила: не менять имя сущности, не подменять бренд на известный, не использовать общие знания LLM вне payload, фильтр нерелевантных новостей.

**Что сознательно не делал в этом репозитории**  
Отдельные чат-агенты CrewAI, router на 5+ intents, shared memory, HITL UI, ACL на tools — следующий этап продукта фонда; в тесте — один вертикальный срез (company research) на том же LangGraph.