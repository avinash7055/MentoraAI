"""
Configuration settings for the AI UPSC Mentor application.
Loads settings from environment variables with sensible defaults.
"""
from pydantic import Field
from pydantic_settings import BaseSettings
import os
import logging
from typing import List, Optional

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AI UPSC Mentor"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    RELOAD: bool = Field(default=False)

    # Supabase Database settings
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    SUPABASE_DB_PASSWORD: str = Field(default="")

    # Fallback local database settings (for development)
    DATABASE_URL: str = Field(default="postgresql://postgres:password@localhost:5432/upsc_mentor")
    TEST_DATABASE_URL: str = Field(default="postgresql://postgres:password@localhost:5432/upsc_mentor_test")

    # LLM settings
    LLM_MODEL: str = Field(default="mixtral-8x7b-32768")
    GROQ_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")

    # Vector database settings
    CHROMA_PATH: str = Field(default="./data/chroma")

    # Security
    SECRET_KEY: str = Field(default="")  # Must be set in .env file
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours

    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])

    # API settings
    API_V1_STR: str = Field(default="/api/v1")

    # WhatsApp settings
    WHATSAPP_TOKEN: str = Field(default="")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="")
    WHATSAPP_PHONE_ID: str = Field(default="")
    WHATSAPP_APP_TOKEN: str = Field(default="")
    WHATSAPP_API_VERSION: str = Field(default="v17.0")
    VERIFY_TOKEN: str = Field(default="")

    def get_database_url(self) -> str:
        """Return the appropriate database URL based on environment."""
        if self.SUPABASE_URL and self.SUPABASE_KEY and self.SUPABASE_DB_PASSWORD:
            # Use Supabase database URL with proper password encoding
            from urllib.parse import quote
            project_ref = self.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
            # URL encode the password to handle special characters
            encoded_password = quote(self.SUPABASE_DB_PASSWORD, safe='')
            return f"postgresql://postgres:{encoded_password}@db.{project_ref}.supabase.co:5432/postgres"

        if self.ENVIRONMENT == "test":
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields to be ignored

# Create settings instance
settings = Settings()
