"""
Диагностика STALZONE API: измеряем время ответа на разные лимиты.
Запуск: python -m scripts.diagnose_api
"""
import httpx
import os
import time
from dotenv import load_dotenv

load_dotenv()


def get_token():
    r = httpx.post(
        "https://exbo.net/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("STALZONE_CLIENT_ID"),
            "client_secret": os.getenv("STALZONE_CLIENT_SECRET"),
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def test_limit(token, limit):
    t0 = time.time()
    r = httpx.get(
        "https://eapi.stalcraft.net/ru/auction/kqgy/history",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": limit, "additional": "true"},
        timeout=120,
    )
    elapsed = time.time() - t0
    status = r.status_code
    try:
        count = len(r.json().get("prices", []))
    except Exception:
        count = "?"
    print(f"  limit={limit:5d}  время={elapsed:6.1f}с  статус={status}  записей={count}")
    return elapsed


def main():
    print("1) Получаем OAuth-токен...")
    t0 = time.time()
    token = get_token()
    print(f"   Токен получен за {time.time()-t0:.1f}с\n")

    print("2) Тестируем разные лимиты истории:")
    for limit in [10, 50, 100, 200]:
        try:
            test_limit(token, limit)
        except Exception as e:
            print(f"  limit={limit}  ОШИБКА: {e}")

    print("\n3) Тест с offset (глубокая страница):")
    t0 = time.time()
    try:
        r = httpx.get(
            "https://eapi.stalcraft.net/ru/auction/kqgy/history",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 200, "offset": 800, "additional": "true"},
            timeout=120,
        )
        print(f"  offset=800, limit=200  время={time.time()-t0:.1f}с  статус={r.status_code}")
    except Exception as e:
        print(f"  ОШИБКА: {e}")

    print("\nГотово.")


if __name__ == "__main__":
    main()