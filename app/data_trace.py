"""Console trace: where numeric tokens in tool data come from (debug)."""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger("data_trace")

# Паттерн: числа с опциональными , . (цены, капитализация, проценты)
_NUMBER_RE = re.compile(r"\d[\d.,]*")


def _snippet(text: str, needle: str, radius: int = 80) -> str:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return text[start:end].replace("\n", " ")


def _scan_text(label: str, text: str, needles: tuple[str, ...]) -> list[dict]:
    hits: list[dict] = []
    if not text:
        return hits
    all_numbers = sorted(set(_NUMBER_RE.findall(text)), key=len, reverse=True)[:30]
    for needle in needles:
        if needle.lower() in text.lower():
            hits.append(
                {
                    "label": label,
                    "needle": needle,
                    "snippet": _snippet(text, needle),
                    "all_numbers_sample": all_numbers[:15],
                }
            )
    return hits


def log_tool_data_trace(
    *,
    stage: str,
    company_name: str,
    profile: str,
    news: list[str],
    needles: tuple[str, ...] = ("300",),
) -> None:
    """
    Печатает в консоль, есть ли needle (по умолчанию 300) в сырых данных tools.
    Вызывать после collect_data и перед/после synthesize.
    """
    hits: list[dict] = []
    hits.extend(_scan_text("profile", profile, needles))

    for i, item in enumerate(news):
        hits.extend(_scan_text(f"news[{i}]", item, needles))

    profile_numbers = sorted(set(_NUMBER_RE.findall(profile or "")))[:20]

    logger.info(
        "data_trace_scan",
        stage=stage,
        company=company_name,
        profile_len=len(profile or ""),
        news_count=len(news),
        profile_numbers=profile_numbers,
        needle_hits=len(hits),
    )

    if not hits:
        logger.info(
            "data_trace_result",
            stage=stage,
            company=company_name,
            message=f"Needles {needles} NOT found in tool data (profile + news). "
            "If they appear in the report -> likely LLM prior knowledge.",
        )
        return

    for h in hits:
        logger.warning(
            "data_trace_hit",
            stage=stage,
            company=company_name,
            source=h["label"],
            needle=h["needle"],
            snippet=h["snippet"],
            numbers_nearby=h["all_numbers_sample"],
        )


def log_report_numeric_trace(
    *,
    stage: str,
    company_name: str,
    markdown: str,
    needles: tuple[str, ...] = ("300",),
) -> None:
    """Проверка чисел уже в финальном markdown."""
    for needle in needles:
        if needle.lower() in markdown.lower():
            logger.warning(
                "data_trace_report",
                stage=stage,
                company=company_name,
                needle=needle,
                snippet=_snippet(markdown, needle),
                message="Number present in final report markdown",
            )
        else:
            logger.info(
                "data_trace_report",
                stage=stage,
                company=company_name,
                needle=needle,
                found=False,
            )
