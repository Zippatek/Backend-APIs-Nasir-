"""
Configuration settings for Propabridge Listings Service
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/propabridge")
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    
    # External Services
    user_service_url: str = os.getenv("USER_SERVICE_URL", "http://localhost:8000/api/v1")
    user_service_api_key: str = os.getenv("USER_SERVICE_API_KEY", "")
    
    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    
    # API
    api_version: str = os.getenv("API_VERSION", "v1")
    api_title: str = os.getenv("API_TITLE", "Propabridge Listings API")
    api_description: str = os.getenv("API_DESCRIPTION", "Property listing management")
    api_docs_url: str = os.getenv("API_DOCS_URL", "/docs")
    api_redoc_url: str = os.getenv("API_REDOC_URL", "/redoc")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    cors_allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    cors_allow_methods: List[str] = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PATCH,DELETE,OPTIONS").split(",")
    cors_allow_headers: List[str] = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization").split(",")
    
    # Listing Configuration
    max_images_per_listing: int = int(os.getenv("MAX_IMAGES_PER_LISTING", "10"))
    max_image_size_mb: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
    allowed_image_formats: List[str] = os.getenv("ALLOWED_IMAGE_FORMATS", "jpg,jpeg,png,webp").split(",")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
