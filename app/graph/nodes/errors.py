import structlog

from app.graph.state import ReportState
from app.tools.company import NOT_FOUND_MSG, is_profile_not_found
from app.tools.news import NO_NEWS_MSG

logger = structlog.get_logger(__name__)


def _default_error_message(state: ReportState) -> str:
    company_name = state.get("company_name") or "неизвестный объект"
    entity_kind = state.get("entity_kind", "unknown")

    if entity_kind == "brand":
        return (
            f"Недостаточно данных для отчёта по «{company_name}». "
            "Бренд может не иметь отдельного профиля публичной компании; "
            "новости по запросу также не получены. "
            "Попробуйте указать материнскую компанию (например, L'Oréal для Lancôme) "
            "или переформулировать запрос."
        )
    return (
        f"Недостаточно данных для отчёта по «{company_name}». "
        "Профиль и новости недоступны для формирования анализа."
    )


async def insufficient_data(state: ReportState) -> dict:
    company_name = state.get("company_name") or "неизвестный объект"
    error = state.get("error") or _default_error_message(state)

    logger.info("node=insufficient_data", company_name=company_name, error=error)

    profile = state.get("profile") or ""
    news = state.get("news") or []
    parts = [f"# Невозможно составить отчёт\n\n{error}\n"]

    if profile and not is_profile_not_found(profile):
        parts.append(f"\n## Частичные данные (профиль)\n\n{profile}\n")
    elif profile and is_profile_not_found(profile):
        parts.append(f"\n## Контекст профиля\n\n{NOT_FOUND_MSG}\n")

    valid_news = [n for n in news if n != NO_NEWS_MSG]
    if valid_news:
        parts.append("\n## Частичные данные (новости)\n\n")
        parts.extend(f"- {n}\n" for n in valid_news)

    return {
        "report_md": "".join(parts),
        "status": "insufficient",
        "error": error,
    }
