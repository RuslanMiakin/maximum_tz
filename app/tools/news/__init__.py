import structlog

from app.config import get_settings
from app.tools.news.rss import fetch_google_news_rss
from app.tools.news.tavily import fetch_tavily_news

logger = structlog.get_logger(__name__)

NO_NEWS_MSG = "Новости не найдены."


async def get_financial_news(company_name: str) -> tuple[list[str], list[str]]:
    """
    RSS first, Tavily fallback.
    Returns (news_items, source_tags for sources_used).
    """
    logger.info("calling get_financial_news", company_name=company_name)
    settings = get_settings()
    sources: list[str] = []

    items = await fetch_google_news_rss(company_name)
    if items:
        sources.append("google_news_rss")

    if len(items) >= settings.min_news_count:
        logger.info("get_financial_news_done", source="rss", count=len(items))
        return items[:5], sources

    reason = "empty_rss" if not items else "insufficient_results"
    tavily_items = await fetch_tavily_news(company_name, reason=reason)
    if tavily_items:
        if "google_news_rss" not in sources and items:
            sources.append("google_news_rss")
        sources.append("tavily")
        merged = (items + tavily_items)[:5]
        logger.info("get_financial_news_done", source="tavily", count=len(merged))
        return merged, sources

    if items:
        logger.info("get_financial_news_partial", count=len(items))
        return items, sources or ["google_news_rss"]

    logger.info("get_financial_news_not_found", company_name=company_name)
    return [NO_NEWS_MSG], sources
