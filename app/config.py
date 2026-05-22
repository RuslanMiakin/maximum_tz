from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    tavily_api_key: str | None = None
    min_news_count: int = 1
    log_level: str = "INFO"
    http_user_agent: str = (
        "MarketResearcherBot/1.0 (contact: dev@localhost; "
        "https://github.com/example/market-researcher)"
    )
    http_timeout_seconds: float = 10.0

    @property
    def llm_provider(self) -> str:
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        return "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()
