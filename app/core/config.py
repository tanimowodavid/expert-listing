from functools import lru_cache
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Property Listings API"
    database_url: str = os.environ.get("DATABASE_URL", "")
    


@lru_cache
def get_settings() -> Settings:
    return Settings()