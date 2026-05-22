#!/usr/bin/env python3
"""
End-to-end smoke evaluation: invokes LangGraph directly (no HTTP).
Run from project root: python scripts/evaluate.py
Requires OPENAI_API_KEY or ANTHROPIC_API_KEY in .env
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.graph.report_graph import get_report_graph
from app.graph.state import ReportState
from app.logging_config import setup_logging

TEST_QUERIES: list[tuple[str, str]] = [
    ("public_apple", "Составь аналитический отчет по компании Apple"),
    ("public_microsoft", "Составь аналитический отчет по компании Microsoft"),
    ("public_tesla", "Составь аналитический отчет по компании Tesla"),
    ("edge_unknown", "Составь отчет по компании Рога и Копыта"),
    ("edge_ambiguous", "Составь отчет по компании Ланком-Прайм"),
    ("brand_nivea", "Составь аналитический отчет по бренду Nivea"),
    ("public_nvidia", "Составь аналитический отчет по компании Nvidia"),
    ("short_query", "Отчет по Amazon"),
    ("cyrillic_brand", "Аналитический отчет по компании Сбербанк"),
    ("edge_gibberish", "Составь отчет по компании XyZqWeRt123"),
]

WIDTH = 52


def _print_final_summary(
    results: list[tuple[str, bool]], passed: int, total: int
) -> None:
    failed = [name for name, ok in results if not ok]
    all_ok = passed == total

    print()
    print("+" + "-" * WIDTH + "+")
    title = f"  FINAL RESULT: {passed}/{total}"
    print("|" + title.center(WIDTH) + "|")
    print("|" + f"  {'ALL PASSED' if all_ok else 'SOME FAILED'}".center(WIDTH) + "|")
    print("+" + "-" * WIDTH + "+")

    print()
    print("  Case results:")
    for name, ok in results:
        mark = "OK  " if ok else "FAIL"
        print(f"    [{mark}] {name}")

    if failed:
        print()
        print(f"  Failed ({len(failed)}): {', '.join(failed)}")

    print()


async def run_case(name: str, query: str, graph) -> bool:
    print(f"\n{'=' * 60}")
    print(f"CASE: {name}")
    print(f"QUERY: {query}")
    print("-" * 60)

    initial: ReportState = {"query": query, "sources_used": []}
    try:
        final = await graph.ainvoke(initial)
    except Exception as e:
        print(f"FAIL — pipeline error: {e}")
        return False

    company = final.get("company_name") or ""
    status = final.get("status") or "ok"
    sources = final.get("sources_used") or []
    markdown = final.get("report_md") or ""
    error = final.get("error") or ""

    ok = bool(markdown and markdown.strip())
    label = "PASS" if ok else "FAIL"

    print(f"STATUS: {status}")
    print(f"COMPANY: {company}")
    print(f"SOURCES: {', '.join(sources) if sources else '(none)'}")
    if error:
        print(f"ERROR: {error}")
    print(f"MARKDOWN LENGTH: {len(markdown)} chars")
    print(f"RESULT: {label} — markdown {'present' if ok else 'missing'}")
    if ok:
        preview = markdown.strip().replace("\n", " ")[:300]
        print(f"PREVIEW: {preview}...")

    return ok


async def main() -> int:
    setup_logging()
    settings = get_settings()

    if settings.llm_provider == "none":
        print("ERROR: Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")
        return 1

    total = len(TEST_QUERIES)
    print("Market Researcher — E2E evaluation (direct graph invoke)")
    print(f"LLM provider: {settings.llm_provider}")
    print(f"Cases: {total}")

    graph = get_report_graph()
    results: list[tuple[str, bool]] = []
    passed = 0

    for name, query in TEST_QUERIES:
        ok = await run_case(name, query, graph)
        results.append((name, ok))
        if ok:
            passed += 1

    _print_final_summary(results, passed, total)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
