from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.graph.report_graph import get_report_graph
from app.graph.state import ReportState
from app.logging_config import setup_logging
from app.schemas import ReportRequest, ReportResponse

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    get_report_graph()
    yield


app = FastAPI(
    title="Market Researcher",
    description="AI-аналитика публичных компаний (LangGraph + FastAPI)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "llm_configured": settings.llm_provider != "none",
    }


@app.post("/api/v1/reports", response_model=ReportResponse)
async def create_report(body: ReportRequest):
    settings = get_settings()
    if settings.llm_provider == "none":
        raise HTTPException(
            status_code=503,
            detail="LLM не настроен: укажите OPENAI_API_KEY или ANTHROPIC_API_KEY в .env",
        )

    initial: ReportState = {"query": body.query, "sources_used": []}
    graph = get_report_graph()
    final = await graph.ainvoke(initial)

    company = final.get("company_name") or ""
    sources = final.get("sources_used") or []
    markdown = final.get("report_md") or ""

    if final.get("status") == "insufficient":
        return JSONResponse(
            status_code=422,
            content={
                "detail": final.get("error")
                or "Недостаточно данных для формирования отчёта",
                "markdown": markdown,
                "company": company,
                "sources_used": sources,
            },
        )

    return ReportResponse(
        markdown=markdown,
        company=company,
        sources_used=sources,
    )
