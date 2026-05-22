import asyncio
from urllib.parse import quote

import httpx
import structlog
import yfinance as yf

from app.config import get_settings
from app.http_headers import get_http_headers
from app.tools.sanitize import sanitize_profile_text


def _has_cyrillic(text: str) -> bool:
    return any("\u0400" <= c <= "\u04FF" for c in text)

logger = structlog.get_logger(__name__)

PROFILE_NOT_FOUND_MARKER = "[PROFILE_UNAVAILABLE]"

NOT_FOUND_MSG = (
    f"{PROFILE_NOT_FOUND_MARKER}\n"
    "Бренд не представлен как отдельная компания в финансовых базах данных, "
    "так как может входить в состав более крупной группы. "
    "Используйте отраслевой контекст и новости сегмента; не утверждайте, что сущность "
    "«отсутствует в базах» — отдельный тикер/профиль публичной компании может не существовать."
)


def is_profile_not_found(profile: str | None) -> bool:
    if not profile or not profile.strip():
        return True
    p = profile.strip()
    return (
        PROFILE_NOT_FOUND_MARKER in p
        or "не представлен как отдельная компания" in p
        or "не найдена ни в yfinance" in p.lower()
    )


# Частые алиасы для yfinance (тикер надёжнее названия)
_TICKER_ALIASES: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    "samsung": "005930.KS",
    "loreal": "OR.PA",
    "l'oreal": "OR.PA",
}


def _resolve_ticker(company_name: str) -> str | None:
    key = company_name.strip().lower()
    if key in _TICKER_ALIASES:
        return _TICKER_ALIASES[key]
    if key.isupper() and 1 <= len(key) <= 6:
        return key
    try:
        search = yf.Search(company_name, max_results=1)
        quotes = getattr(search, "quotes", None) or []
        if quotes:
            symbol = quotes[0].get("symbol")
            if symbol:
                return symbol
    except Exception as e:
        logger.warning("yfinance_search_failed", company=company_name, error=str(e))
    return None


def _fetch_yfinance_profile(company_name: str) -> tuple[str | None, str | None]:
    """Sync: returns (profile_text, ticker) or (None, None)."""
    ticker_symbol = _resolve_ticker(company_name) or company_name
    try:
        info = yf.Ticker(ticker_symbol).info
    except Exception as e:
        logger.warning("yfinance_ticker_failed", ticker=ticker_symbol, error=str(e))
        return None, None

    if not info or not info.get("longBusinessSummary") and not info.get("shortName"):
        return None, None

    summary = info.get("longBusinessSummary") or info.get("shortName") or ""
    if not summary.strip():
        return None, None

    parts = [
        f"Компания: {info.get('longName') or info.get('shortName') or company_name}",
        f"Тикер: {info.get('symbol') or ticker_symbol}",
        f"Сектор: {info.get('sector', 'н/д')}",
        f"Отрасль: {info.get('industry', 'н/д')}",
        f"Страна: {info.get('country', 'н/д')}",
        f"Сотрудники: {info.get('fullTimeEmployees', 'н/д')}",
        f"Сайт: {info.get('website', 'н/д')}",
        "",
        summary,
    ]
    return sanitize_profile_text("\n".join(parts)), info.get("symbol") or ticker_symbol


async def _fetch_wikipedia(company_name: str) -> str | None:
    use_ru = _has_cyrillic(company_name)
    lang = "ru" if use_ru else "en"
    page = quote(company_name.strip().replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page}"
    logger.info("wikipedia_request", company_name=company_name, lang=lang, url=url)

    settings = get_settings()
    headers = get_http_headers()
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("wikipedia_failed", company=company_name, lang=lang, error=str(e))
        return None

    extract = data.get("extract")
    if not extract:
        return None
    title = data.get("title", company_name)
    wiki = f"Компания: {title}\nИсточник: Wikipedia ({lang})\n\n{extract}"
    return sanitize_profile_text(wiki)


async def get_company_profile(company_name: str) -> tuple[str, str | None, str]:
    """
    Returns (profile_text, ticker_or_none, source_tag).
    source_tag: yfinance | wikipedia | not_found
    """
    logger.info("calling get_company_profile", company_name=company_name)

    profile, ticker = await asyncio.to_thread(_fetch_yfinance_profile, company_name)
    if profile:
        logger.info("get_company_profile_done", source="yfinance", company_name=company_name)
        return profile, ticker, "yfinance"

    wiki = await _fetch_wikipedia(company_name)
    if wiki:
        logger.info("get_company_profile_done", source="wikipedia", company_name=company_name)
        return wiki, None, "wikipedia"

    logger.info("get_company_profile_not_found", company_name=company_name)
    return NOT_FOUND_MSG, None, "not_found"
