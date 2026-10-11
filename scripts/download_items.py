"""Скрипт для скачивания базы предметов STALZONE с GitHub."""
import asyncio
from app.services.items_database import download_items_database

if __name__ == "__main__":
    asyncio.run(download_items_database())