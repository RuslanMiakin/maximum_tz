import asyncio

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


def _search_tavily(company_name: str) -> list[str]:
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(
        query=f"{company_name} financial news",
        max_results=5,
        search_depth="basic",
    )
    results = response.get("results") or []
    items: list[str] = []
    for r in results:
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()
        url = r.get("url", "")
        if not title:
            continue
        block = f"**{title}**"
        if content:
            block += f"\n{content}"
        if url:
            block += f"\n{url}"
        items.append(block)
    return items


async def fetch_tavily_news(company_name: str, reason: str) -> list[str]:
    logger.info(
        "news_source=tavily",
        company_name=company_name,
        reason=reason,
    )
    try:
        items = await asyncio.to_thread(_search_tavily, company_name)
        logger.info("news_tavily_done", company_name=company_name, count=len(items))
        return items
    except Exception as e:
        logger.warning("news_tavily_failed", company_name=company_name, error=str(e))
        return []
