from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ecommerce:ecommerce@localhost:5432/ecommerce",
    )
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY") or None
    daily_search_limit: int = int(os.getenv("DAILY_SEARCH_LIMIT", "10"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-6-luna")


settings = Settings()

