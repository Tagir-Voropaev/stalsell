import httpx
import json
import os

# Официальный индексный файл базы предметов STALZONE на GitHub
ITEMS_DB_URL = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru/listing.json"
LOCAL_CACHE = "data/items_cache.json"


async def download_items_database():
    """Скачивает индекс предметов с GitHub и сохраняет локально."""
    print("Скачиваем базу предметов с GitHub...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(ITEMS_DB_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
    
    os.makedirs("data", exist_ok=True)
    
    with open(LOCAL_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"База сохранена. Всего предметов: {len(data)}")
    return data


def load_items_database():
    """Загружает базу из локального кэша."""
    if not os.path.exists(LOCAL_CACHE):
        return None
    
    with open(LOCAL_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_item_name(item_id: str) -> str:
    """
    Возвращает русское название предмета по его ID.
    Ищет по полю 'data', извлекая ID из пути.
    """
    db = load_items_database()
    if not db:
        return item_id
    
    for item in db:
        # Путь к файлу выглядит как '/items/other/qyvk.json'
        # Извлекаем ID: 'qyvk'
        data_path = item.get("data", "")
        if data_path:
            # Берем имя файла без расширения
            file_id = data_path.split("/")[-1].replace(".json", "")
            if file_id == item_id:
                name_obj = item.get("name", {})
                lines = name_obj.get("lines", {})
                return lines.get("ru", item_id)
    
    return item_id


if __name__ == "__main__":
    import asyncio
    asyncio.run(download_items_database())