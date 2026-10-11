"""Смотрим сырой ответ API для активных лотов."""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STALZONE_CLIENT_ID")
CLIENT_SECRET = os.getenv("STALZONE_CLIENT_SECRET")
REGION = "ru"
ITEM_ID = "kqgy"


def get_token():
    r = httpx.post(
        "https://exbo.net/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    token = get_token()
    print(f"✅ Токен получен")

    url = f"https://eapi.stalcraft.net/{REGION}/auction/{ITEM_ID}/lots"
    params = {"limit": 3, "additional": "true"}
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\nGET {url}?additional=true&limit=3\n")
    r = httpx.get(url, headers=headers, params=params, timeout=15)
    print(f"Статус: {r.status_code}\n")

    if r.status_code != 200:
        print(f"Ошибка: {r.text}")
        return

    data = r.json()
    print("📋 Полный сырой JSON (первые 3000 символов):")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])

    # Разбор ключей первого лота
    lots = data.get("lots", [])
    if lots:
        print(f"\n🔍 Ключи первого лота:")
        for k, v in lots[0].items():
            val_str = str(v)
            if len(val_str) > 100:
                val_str = val_str[:100] + "..."
            print(f"   {k}: {val_str}")


if __name__ == "__main__":
    main()