from typing import Literal, TypedDict

EntityKind = Literal["public_company", "brand", "unknown"]


class ReportState(TypedDict, total=False):
    query: str
    company_name: str
    ticker: str
    entity_kind: EntityKind
    name_ambiguous: bool
    profile: str
    profile_found: bool
    news: list[str]
    report_md: str
    error: str
    sources_used: list[str]
    status: Literal["ok", "insufficient"]
