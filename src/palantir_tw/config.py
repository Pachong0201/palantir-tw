from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PALANTIR_TW_", extra="ignore")

    database_url: str = "sqlite:///./data/palantir_tw.db"
    deepseek_api_key: str = ""
    data_dir: Path = Path("./data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
