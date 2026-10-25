import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # LLM & Embeddings Configuration
    LLM_PROVIDER: str = "gemini"  # "gemini" or "openai"
    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""
    
    # Model selections
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Email Sync Configuration
    EMAIL_IMAP_SERVER: str = "imap.gmail.com"
    EMAIL_IMAP_PORT: int = 993
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""  # App Password
    EMAIL_SYNC_DAYS: int = 14  # Fetch emails from last N days
    EMAIL_MAX_FETCH: int = 15   # Max emails to fetch per sync session

    # Directories
    PROJECTS_KB_DIR: str = str(BASE_DIR / "projects_kb")
    CACHE_DIR: str = str(BASE_DIR / "cache")
    VECTOR_DB_PATH: str = str(BASE_DIR / "cache" / "vector_store.json")
    EMAIL_CACHE_PATH: str = str(BASE_DIR / "cache" / "emails.json")

    # App settings
    SECRET_KEY: str = "butler-agent-secret-key-12345"
    HTTP_PROXY: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Apply proxy settings if configured
if settings.HTTP_PROXY:
    os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
    os.environ["HTTPS_PROXY"] = settings.HTTP_PROXY

# Ensure directories exist
os.makedirs(settings.PROJECTS_KB_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)
