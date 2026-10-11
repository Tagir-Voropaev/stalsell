import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = os.getenv("APP_NAME", "StalSell")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/stalsell.db")
    STALZONE_API_URL = os.getenv("STALZONE_API_URL", "")
    STALZONE_API_KEY = os.getenv("STALZONE_API_KEY", "")

settings = Settings()