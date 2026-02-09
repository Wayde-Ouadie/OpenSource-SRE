"""Configuration management using pydantic-settings."""
import os
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base settings for all services."""
    
    service_name: str = "unknown-service"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    environment: Literal["development", "staging", "production"] = "development"
    
    # Database
    database_url: str = "postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management"
    
    # Service URLs
    incident_mgmt_base_url: str = "http://incident-management:8002"
    oncall_base_url: str = "http://oncall-service:8003"
    notification_base_url: str = "http://notification-service:8004"
    alert_ingestion_base_url: str = "http://alert-ingestion:8001"
    
    # HTTP Client
    http_timeout: float = 5.0
    http_retries: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
