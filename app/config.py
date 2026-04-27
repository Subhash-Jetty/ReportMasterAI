"""
Configuration settings for ReportMaster AI.
Loads environment variables and provides application-wide settings.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    # Model Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))

    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Paths
    data_dir: Path = BASE_DIR / "data" / "manuals"
    index_dir: Path = BASE_DIR / "data" / "index"
    static_dir: Path = BASE_DIR / "static"

    class Config:
        env_file = ".env"
        extra = "allow"


# Singleton settings instance
settings = Settings()
