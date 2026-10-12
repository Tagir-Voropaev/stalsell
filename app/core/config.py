import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "StalSell")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/stalsell.db")
    STALZONE_API_URL = os.getenv("STALZONE_API_URL", "")
    STALZONE_API_KEY = os.getenv("STALZONE_API_KEY", "")

    # 🔑 JWT-настройки
    SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-change-me")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней


settings = Settings()