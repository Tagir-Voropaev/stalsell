"""Проверяет глубину истории через API STALZONE."""
import httpx
import os
import time
from dotenv import load_dotenv

load_dotenv()


def get_token():
    r = httpx.post("https://exbo.net/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": os.getenv("STALZONE_CLIENT_ID"),
        "client_secret": os.getenv("STALZONE_CLIENT_SECRET"),
    }, timeout=15)
    return r.json()["access_token"]


def main():
    token = get_token()
    item_id = "kqgy"  # Браслет

    print(f"Проверяем глубину API для {item_id}...\n")

    for offset in [0, 5000, 10000, 20000, 30000, 40000, 50000, 75000, 100000]:
        t0 = time.time()
        r = httpx.get(
            f"https://eapi.stalcraft.net/ru/auction/{item_id}/history",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 200, "offset": offset},
            timeout=30,
        )
        elapsed = time.time() - t0
        try:
            count = len(r.json().get("prices", []))
        except Exception:
            count = "?"
        status = "✅" if count == 200 else ("⚠️" if count and count > 0 else "❌ пусто")
        print(f"  offset={offset:>6}  время={elapsed:5.1f}с  записей={count:>4}  {status}")


if __name__ == "__main__":
    main()