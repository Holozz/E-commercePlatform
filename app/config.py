from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ecommerce:ecommerce@localhost:5432/ecommerce",
    )
    brave_search_api_key: str | None = os.getenv("BRAVE_SEARCH_API_KEY") or None
    daily_search_limit: int = int(os.getenv("DAILY_SEARCH_LIMIT", "10"))


settings = Settings()

