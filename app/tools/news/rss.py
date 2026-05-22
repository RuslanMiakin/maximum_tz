import asyncio
from urllib.parse import quote_plus

import feedparser
import structlog

logger = structlog.get_logger(__name__)


def _parse_rss(company_name: str) -> list[str]:
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(company_name + ' stock')}&hl=ru"
    )
    feed = feedparser.parse(url)
    if getattr(feed, "bozo", False) and not feed.entries:
        raise ValueError(f"RSS parse error: {getattr(feed, 'bozo_exception', 'unknown')}")

    items: list[str] = []
    for entry in feed.entries[:5]:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        published = entry.get("published", "")
        link = entry.get("link", "")
        if not title:
            continue
        block = f"**{title}**"
        if published:
            block += f" ({published})"
        if summary:
            block += f"\n{summary}"
        if link:
            block += f"\n{link}"
        items.append(block)
    return items


async def fetch_google_news_rss(company_name: str) -> list[str]:
    logger.info("news_source=rss", company_name=company_name)
    try:
        items = await asyncio.to_thread(_parse_rss, company_name)
        logger.info("news_rss_done", company_name=company_name, count=len(items))
        return items
    except Exception as e:
        logger.warning("news_rss_failed", company_name=company_name, error=str(e))
        return []
