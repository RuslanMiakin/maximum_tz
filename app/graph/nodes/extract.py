import re
from typing import Literal

import structlog
from pydantic import BaseModel, Field

from app.graph.state import ReportState
from app.llm import get_chat_model
from app.prompts.ambiguity import ENTITY_IDENTITY_RULES

logger = structlog.get_logger(__name__)

EXTRACT_SYSTEM_PROMPT = f"""Extract the market entity from the user query.

Return:
- company_name: the entity name EXACTLY as the user wrote it (same language, spelling, hyphens). Examples:
  - user wrote "Ланком-Прайм" → company_name must be "Ланком-Прайм", NOT "Lancome" or "L'Oréal"
  - user wrote "Apple" → "Apple"
  - Strip only surrounding quotes and report boilerplate ("составь отчет по компании ..."), not the entity itself
- ticker: stock ticker only if the user clearly named a listed public company, else null
- entity_kind: "public_company" | "brand" | "unknown"
- name_ambiguous: true if the name could refer to multiple organizations or is uncommon/unclear

{ENTITY_IDENTITY_RULES}

Do NOT include words like "составь отчет" in company_name. Never change the entity string."""


class ExtractedCompany(BaseModel):
    company_name: str = Field(
        description="Entity name EXACTLY as in user query, e.g. Apple or Ланком-Прайм — never substituted"
    )
    ticker: str | None = Field(default=None, description="Ticker if public company")
    entity_kind: Literal["public_company", "brand", "unknown"] = Field(
        default="unknown",
        description="brand vs public_company",
    )
    name_ambiguous: bool = Field(
        default=False,
        description="True if entity identity is unclear or could match multiple organizations",
    )


def _heuristic_extract(query: str) -> ExtractedCompany | None:
    patterns = [
        r"(?:по компании|компани[ияею]|бренду)\s+[\"«]?([^\"».?!]+)[\"»]?",
        r"(?:company|brand|about)\s+[\"«]?([^\"».?!]+)[\"»]?",
        r"(?:отчет|отчёт|report)\s+(?:по|for|about)\s+[\"«]?([^\"».?!]+)[\"»]?",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) >= 2:
                kind: Literal["public_company", "brand", "unknown"] = (
                    "brand" if "бренд" in query.lower() else "unknown"
                )
                return ExtractedCompany(company_name=name, entity_kind=kind)
    return None


async def extract_company(state: ReportState) -> dict:
    query = state["query"]
    logger.info("node=extract_company", step="start", query=query)
    logger.info("Думаю...")

    extracted: ExtractedCompany | None = None
    try:
        llm = get_chat_model().with_structured_output(ExtractedCompany)
        extracted = await llm.ainvoke(
            [
                ("system", EXTRACT_SYSTEM_PROMPT),
                ("human", query),
            ]
        )
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("extract_llm_failed", error=str(e))
        extracted = _heuristic_extract(query)

    if extracted is None:
        extracted = _heuristic_extract(query)

    if extracted is None or not extracted.company_name.strip():
        logger.info("node=extract_company", step="failed")
        return {
            "company_name": "",
            "error": "Не удалось определить объект анализа из запроса.",
            "status": "insufficient",
        }

    company_name = extracted.company_name.strip()
    ticker = (extracted.ticker or "").strip() or None
    logger.info(
        "node=extract_company",
        step="done",
        company_name=company_name,
        ticker=ticker,
        entity_kind=extracted.entity_kind,
    )
    result: dict = {
        "company_name": company_name,
        "entity_kind": extracted.entity_kind,
        "name_ambiguous": extracted.name_ambiguous,
    }
    if ticker:
        result["ticker"] = ticker
    return result
