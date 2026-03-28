from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to this file (backend/.env) — works regardless of cwd
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    app_name: str = "ProfBetGeng"
    app_version: str = "0.1.0"
    debug: bool = False
    auth_enabled: bool = True
    batch_enabled: bool = False

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "env_ignore_empty": True,   # empty shell vars don't override .env values
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
