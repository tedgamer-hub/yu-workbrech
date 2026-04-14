import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/gaokao_workbench.db")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-this-in-production")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
    import_storage_dir: str = os.getenv("IMPORT_STORAGE_DIR", "./data/imports")


settings = Settings()