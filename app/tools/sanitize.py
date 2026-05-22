"""v1: убрать ценовые числа из tool output до LLM."""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Замена вместо удаления — сохраняем, что новость про котировки, без уровня
_PRICE_REPLACEMENT = "[динамика котировок]"

# Порядок важен: более специфичные паттерны первыми
_PRICE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:ниже|выше|под|над|около|до|от|below|above|under|over|near|at)\s+"
        r"[\d][\d.,\s]*\s*(?:\$|usd|долл\.?|доллар(?:ов|а|ы)?|US\$)?",
        re.IGNORECASE,
    ),
    re.compile(r"\$[\d][\d.,]*", re.IGNORECASE),
    re.compile(r"[\d][\d.,]*\s*\$", re.IGNORECASE),
    re.compile(
        r"[\d][\d.,]*\s*(?:usd|долл\.?|доллар(?:ов|а|ы)?|руб\.?|₽|eur|€)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:market\s*cap|рыночн(?:ая|ой)\s+капитализаци(?:я|и))"
        r"[^\n]*[\d][\d.,]*",
        re.IGNORECASE,
    ),
]


def strip_price_data(text: str) -> str:
    if not text:
        return text
    original = text
    for pattern in _PRICE_PATTERNS:
        text = pattern.sub(_PRICE_REPLACEMENT, text)
    text = re.sub(r"(?:\[динамика котировок\]\s*){2,}", _PRICE_REPLACEMENT, text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if text != original:
        logger.debug("price_data_stripped", removed_sample=original[:120])
    return text.strip()


def sanitize_news_item(item: str) -> str:
    return strip_price_data(item)


def sanitize_profile_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if "рыночная капитализация" in low or "market cap" in low:
            continue
        lines.append(strip_price_data(line))
    return "\n".join(lines).strip()
