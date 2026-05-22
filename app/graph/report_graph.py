from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    collect_data,
    extract_company,
    insufficient_data,
    synthesize_report,
)
from app.graph.state import ReportState
from app.tools.company import is_profile_not_found
from app.tools.news import NO_NEWS_MSG


def _news_missing(news: list[str] | None) -> bool:
    if not news:
        return True
    if len(news) == 1 and news[0] == NO_NEWS_MSG:
        return True
    return False


def route_after_extract(state: ReportState) -> str:
    if state.get("status") == "insufficient" or not state.get("company_name"):
        return "insufficient_data"
    return "collect_data"


def route_after_collect(state: ReportState) -> str:
    profile_missing = is_profile_not_found(state.get("profile"))
    news_missing = _news_missing(state.get("news"))
    if profile_missing and news_missing:
        return "insufficient_data"
    return "synthesize_report"


@lru_cache
def get_report_graph():
    graph = StateGraph(ReportState)

    graph.add_node("extract_company", extract_company)
    graph.add_node("collect_data", collect_data)
    graph.add_node("synthesize_report", synthesize_report)
    graph.add_node("insufficient_data", insufficient_data)

    graph.add_edge(START, "extract_company")
    graph.add_conditional_edges(
        "extract_company",
        route_after_extract,
        {
            "collect_data": "collect_data",
            "insufficient_data": "insufficient_data",
        },
    )
    graph.add_conditional_edges(
        "collect_data",
        route_after_collect,
        {
            "synthesize_report": "synthesize_report",
            "insufficient_data": "insufficient_data",
        },
    )
    graph.add_edge("synthesize_report", END)
    graph.add_edge("insufficient_data", END)

    return graph.compile()
