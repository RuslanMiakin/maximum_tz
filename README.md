# Market Researcher

MVP AI-исследователя компаний (тестовое задание): сбор данных из внешних API и структурированный отчёт в Markdown. LangGraph + tools + логи — база для расширения в multi-agent (personal director); кратко в разделе ниже.

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

## Связь с multi-agent

Сейчас — срез **company research** по ТЗ. LangGraph — orchestration layer: новые узлы = новые роли, общий state, политики на tools.

| Узел | Роль |
|------|------|
| `extract_company` | Intent, сущность |
| `collect_data` | Внешние источники, `sources_used` |
| `synthesize_report` | Аналитик, только из tool data |
| `insufficient_data` | Нет данных → 422, без галлюцинаций |

Детерминированный `collect_data` — по ТЗ всегда оба tool с `company_name` (не весь промпт). ReAct — для задач с нефиксированным планом; обязательный сбор фактов — фиксированный граф.

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

Краткое обоснование под тестовое задание (Tool Use, реальные API, edge cases).

**FastAPI + HTTP API**  
Явный контракт: валидация, OpenAPI, `422` при нехватке данных. Проще демонстрировать и тестировать, чем только CLI.

**LangGraph**  
Явные стадии (извлечь → собрать → отчёт), ветка `insufficient_data`, общий state — основа для добавления ролевых узлов без смены runtime.

**Deterministic `collect_data` (без ReAct на сборе)**  
ТЗ: осознанный вызов tools и аргумент `company_name` (`Apple`), не весь промпт. Фиксированный вызов обоих tools предсказуемее, чем если LLM сам решает, вызывать ли API. Логи: `Думаю…` → вызовы tools → `Получил ответ…` → `Формирую отчет…`.

**RSS → Tavily для новостей**  
RSS без квоты — основной канал. Tavily при пустой/скудной выдаче (реальный API + fallback по ТЗ).

**yfinance → Wikipedia для профиля**  
Тикер и структурные поля; Wikipedia без ключа (`ru` / `en` по языку имени).

**Препроцессинг цен (sanitize, v1)**  
Цены режутся в tools; в отчёте — качественная динамика, без чисел вне tool data.

**Промпт и structured output**  
Pydantic → Markdown по секциям ТЗ; не менять имя сущности, не подменять бренд, не опираться на общие знания LLM вне payload.

**Что не в scope теста**  
CrewAI, router на множество intents, shared memory, HITL, ACL на tools — следующий этап; здесь один вертикальный срез на LangGraph.

## Ограничения

- Wikipedia: страница может отсутствовать при неточном имени
- RSS/Tavily: нерелевантные заголовки при неоднозначных именах
- Качество отчёта зависит от LLM и внешних источников
- Нет авторизации, БД, кэша
- v1: без числовых цен и капитализации в выходе tools
