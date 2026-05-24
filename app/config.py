from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # FastAPI
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Feishu
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_oauth_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # JWT
    jwt_secret: str = "change-this-to-a-random-string-at-least-32-chars"
    jwt_expiry_hours: int = 168

    # Database
    database_url: str = "sqlite+aiosqlite:///data/app.db"

    # Storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
