"""
Проверяем /history с additional=true НАПРЯМУЮ через httpx.
Используем правильный OAuth-сервер EXBO (exbo.net).
"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STALZONE_CLIENT_ID")
CLIENT_SECRET = os.getenv("STALZONE_CLIENT_SECRET")

REGION = "ru"
ITEMS = ["kqgy", "qyvk", "zyv9"]

# Правильный OAuth-сервер (отдельно от API!)
OAUTH_URL = "https://exbo.net/oauth/token"

# Основной API
API_URL = "https://eapi.stalcraft.net"


def get_token():
    print(f"🔑 Запрашиваем токен на {OAUTH_URL}...")
    r = httpx.post(
        OAUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    print(f"   Статус: {r.status_code}")
    if r.status_code != 200:
        print(f"   Ответ: {r.text[:300]}")
        r.raise_for_status()
    return r.json()["access_token"]


def check(item_id, token):
    url = f"{API_URL}/{REGION}/auction/{item_id}/history"
    params = {"limit": 5, "additional": "true"}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n{'=' * 70}")
    print(f"  GET {url}?additional=true&limit=5")
    print("=" * 70)
    
    try:
        r = httpx.get(url, headers=headers, params=params, timeout=15)
        print(f"Статус: {r.status_code}")
        
        if r.status_code != 200:
            print(f"Ответ: {r.text[:500]}")
            return
        
        data = r.json()
        print("\n📋 Сырой JSON (первые 2000 символов):")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        
        prices = data.get("prices", [])
        if prices:
            print(f"\n🔍 additional в первой записи:")
            add = prices[0].get("additional", {})
            if add:
                for k, v in add.items():
                    print(f"   {k}: {v}")
            else:
                print("   (пусто)")
        else:
            print("   (нет записей в history)")
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")


def main():
    print(f"CLIENT_ID: {CLIENT_ID}")
    print(f"CLIENT_SECRET: {'✅ есть (' + str(len(CLIENT_SECRET or '')) + ' симв.)' if CLIENT_SECRET else '❌ нет'}")
    
    try:
        token = get_token()
        print(f"✅ Токен: {token[:30]}...")
    except Exception as e:
        print(f"❌ Не удалось получить токен: {e}")
        return
    
    for item_id in ITEMS:
        check(item_id, token)


if __name__ == "__main__":
    main()