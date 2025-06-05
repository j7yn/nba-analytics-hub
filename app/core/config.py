from pydantic import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # app config
    app_name: str = "NBA Edge API"
    app_version: str = "1.0.0"
    debug: bool = False

    # change hosts and the key
    allowed_hosts: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    secret_key: str = "secret-key-here"

    # database - change to postgresql once setup
    database_url: str = "sqlite:///./nba_data.db"
    
    # redis
    redis_url: str = "redis://localhost:6379"
    redis_enabled: bool = True

    # rate limiting
    rate_limit_calls: int = 30
    rate_limit_period: int = 60
    
    # NBA API settings
    api_timeout: int = 30
    max_retries: int = 3
    
    # cache settings
    cache_ttl_minutes: int = 60
    player_cache_ttl_hours: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()