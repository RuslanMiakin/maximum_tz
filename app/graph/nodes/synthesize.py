import structlog

from app.data_trace import log_report_numeric_trace, log_tool_data_trace
from app.graph.state import ReportState
from app.llm import get_chat_model
from app.prompts.synthesize import SYNTHESIZE_SYSTEM_PROMPT
from app.schemas.report import CompanyReport
from app.tools.company import is_profile_not_found
from app.tools.news import NO_NEWS_MSG

logger = structlog.get_logger(__name__)


def _build_user_payload(state: ReportState) -> str:
    query = state.get("query") or ""
    company_name = state.get("company_name") or ""
    profile = state.get("profile") or ""
    news = state.get("news") or []
    entity_kind = state.get("entity_kind", "unknown")
    name_ambiguous = state.get("name_ambiguous", False)
    profile_found = state.get("profile_found", not is_profile_not_found(profile))

    valid_news = [n for n in news if n and n != NO_NEWS_MSG]
    news_block = (
        "\n\n".join(f"---\n{item}" for item in valid_news)
        if valid_news
        else "(no news items retrieved)"
    )
    news_quality = (
        "limited"
        if not valid_news or len(valid_news) < 2
        else "adequate"
    )
    profile_status = "available" if profile_found else "unavailable"

    return (
        f"User query: {query}\n"
        f"Entity (normalized): {company_name}\n"
        f"entity_kind: {entity_kind}\n"
        f"name_ambiguous: {name_ambiguous}\n"
        f"profile_status: {profile_status}\n"
        f"News data quality: {news_quality} ({len(valid_news)} items)\n\n"
        f"## Company profile (raw)\n{profile or '(empty)'}\n\n"
        f"## Financial news (raw)\n{news_block}"
    )


async def synthesize_report(state: ReportState) -> dict:
    company_name = state.get("company_name") or "Unknown"

    logger.info("node=synthesize_report", step="start", company_name=company_name)
    logger.info("Формирую отчет...", company_name=company_name)

    profile = state.get("profile") or ""
    news = state.get("news") or []
    log_tool_data_trace(
        stage="before_llm",
        company_name=company_name,
        profile=profile,
        news=news,
    )

    llm = get_chat_model().with_structured_output(CompanyReport)
    report: CompanyReport = await llm.ainvoke(
        [
            ("system", SYNTHESIZE_SYSTEM_PROMPT),
            ("human", _build_user_payload(state)),
        ]
    )

    markdown = report.to_markdown()
    log_report_numeric_trace(
        stage="after_llm",
        company_name=company_name,
        markdown=markdown,
    )
    log_tool_data_trace(
        stage="compare_tool_vs_report",
        company_name=company_name,
        profile=profile,
        news=news,
    )
    logger.info("node=synthesize_report", step="done", company_name=company_name)

    return {
        "report_md": markdown,
        "status": "ok",
    }
