from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        examples=["Составь аналитический отчет по компании Apple"],
    )


class ReportResponse(BaseModel):
    markdown: str
    company: str
    sources_used: list[str]
