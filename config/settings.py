"""
Configuration module for the School Grades Agent.
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Database (use SQLite by default for portability; override with .env)
    database_url: str = "sqlite:///./school_grades.db"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    # Grades display settings
    # If True, truncate long grade lists by default. The UI can override per-request.
    grades_truncate_default: bool = False
    grades_truncate_limit: int = 10


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


settings = get_settings()
