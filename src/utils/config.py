from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    DATABASE_URL: str 
    app_id: str
    client_id: str
    client_secret: str
    api_key: str
    api_secret: str
    redirect_uri:str 
    redis_url: str
    jwt_secret_key:str
    jwt_algo:str 
    access_token_expiry:int
    refresh_token_expiry:int
    frontend_url:str
    bearer_token:str
    celery_beat_interval:int
    encryption_key:str

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",  # Adjusted to point to the root directory
        env_file_encoding="utf-8",
    )

config = Config()

class Settings:
    PROJECT_NAME: str = "Xmarks"
    PROJECT_VERSION: str = "0.0.1"
    PROJECT_DESCRIPTION: str = "API for Xmarks; the ultimate premium bookmark managment system for X (former twitter)"
    API_V1_PREFIX: str = "/api/v1"
