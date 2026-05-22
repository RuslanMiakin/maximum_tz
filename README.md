# Market Researcher

AI-сервис аналитики публичных компаний: сбор данных из реальных API и формирование Markdown-отчёта.

**Стек:** FastAPI, LangGraph, deterministic tool calling, OpenAI (или Anthropic), yfinance, Google News RSS, Tavily (fallback).

## Быстрый старт

```bash
cd W:\maximum
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Заполните OPENAI_API_KEY в .env
uvicorn app.main:app --reload
```

Если `WinError 10013` — порт 8000 занят. Освободите его или запустите на другом:

```bash
uvicorn app.main:app --reload --port 8080
```

Проверка занятости (Windows): `netstat -ano | findstr ":8000"`

- Swagger: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

### Пример запроса

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reports ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"Составь аналитический отчет по компании Apple\"}"
```

## Архитектура

| Слой | Решение |
|------|---------|
| HTTP | FastAPI — `POST /api/v1/reports`, `GET /health` |
| Оркестрация | LangGraph — узлы `extract_company` → `collect_data` → `synthesize_report` / `insufficient_data` |
| Tools | Детерминированный вызов в `collect_data` (без ReAct) |
| Профиль | yfinance → Wikipedia |
| Новости | **Google News RSS** (основной) → **Tavily** (fallback) |
| LLM | Только извлечение компании и синтез отчёта |

Подробнее: [docs/project-spec.md](docs/project-spec.md)

## Переменные окружения

См. [.env.example](.env.example):

- `OPENAI_API_KEY` — обязателен для LLM (или `ANTHROPIC_API_KEY` + `pip install langchain-anthropic`)
- `TAVILY_API_KEY` — опционально, fallback новостей при пустом RSS
- `HTTP_USER_AGENT` — для Wikipedia REST (опишите бота и **реальный** email)

## Почему такой выбор

- **LangGraph**, а не CrewAI — линейный отчёт и 2 tools; граф даёт явные стадии и ветку `insufficient_data`.
- **Deterministic tools** — предсказуемые аргументы (`company_name`, не весь промпт), проще логи и тесты.
- **RSS → Tavily** — бесплатный основной канал; Tavily только при пустой/скудной выдаче RSS.

## Логи

В консоли structlog: `node=extract_company`, `calling get_company_profile`, `news_source=rss`, `news_source=tavily`, `Формирую отчет...`
