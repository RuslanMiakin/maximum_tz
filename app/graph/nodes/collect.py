import asyncio

import structlog

from app.graph.state import ReportState
from app.tools.company import get_company_profile, is_profile_not_found
from app.tools.news import get_financial_news

logger = structlog.get_logger(__name__)


async def collect_data(state: ReportState) -> dict:
    company_name = state.get("company_name") or ""
    if not company_name:
        return {"profile": "", "news": [], "sources_used": [], "profile_found": False}

    logger.info("node=collect_data", step="start", company_name=company_name)
    logger.info(
        "Думаю... Вызываю get_company_profile и get_financial_news",
        company_name=company_name,
    )

    profile_task = get_company_profile(company_name)
    news_task = get_financial_news(company_name)
    (profile, ticker, profile_source), (news, news_sources) = await asyncio.gather(
        profile_task, news_task
    )

    final_ticker = state.get("ticker") or ticker
    profile_found = not is_profile_not_found(profile)

    sources: list[str] = []
    if profile_source == "yfinance":
        sources.append("yfinance")
    elif profile_source == "wikipedia":
        sources.append("wikipedia")

    sources.extend(news_sources)

    logger.info(
        "node=collect_data",
        step="done",
        profile_found=profile_found,
        profile_len=len(profile),
        news_count=len(news),
        sources=sources,
    )
    logger.info("Получил ответ от tools", company_name=company_name)

    out: dict = {
        "profile": profile,
        "news": news,
        "sources_used": list(dict.fromkeys(sources)),
        "profile_found": profile_found,
    }
    if final_ticker:
        out["ticker"] = final_ticker
    return out
