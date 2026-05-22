from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings


def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    if settings.openai_api_key:
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
    if settings.anthropic_api_key:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise RuntimeError(
                "ANTHROPIC_API_KEY задан, но пакет langchain-anthropic не установлен. "
                "Установите: pip install langchain-anthropic"
            ) from e
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )
    raise RuntimeError(
        "Не задан LLM API ключ. Укажите OPENAI_API_KEY или ANTHROPIC_API_KEY в .env"
    )
