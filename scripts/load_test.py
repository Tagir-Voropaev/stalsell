"""
Тест нагрузки: N одновременных запросов к /history.
Запуск: python -m scripts.load_test
"""
import asyncio
import httpx
import time

# Настройки теста
BASE_URL = "http://localhost:8000"
ITEM_ID = "kqgy"
REQUESTS = 100         # сколько всего запросов
CONCURRENT = 50        # сколько одновременно


async def one_request(client: httpx.AsyncClient, idx: int):
    url = f"{BASE_URL}/api/items/{ITEM_ID}/history?limit=200"
    t0 = time.time()
    try:
        r = await client.get(url, timeout=30)
        elapsed = time.time() - t0
        return {"idx": idx, "status": r.status_code, "elapsed": elapsed}
    except Exception as e:
        elapsed = time.time() - t0
        return {"idx": idx, "status": f"ERR:{type(e).__name__}", "elapsed": elapsed}


async def main():
    print(f"🔥 Тест нагрузки: {REQUESTS} запросов, {CONCURRENT} одновременно")
    print(f"   URL: {BASE_URL}/api/items/{ITEM_ID}/history?limit=200\n")

    async with httpx.AsyncClient() as client:
        # Прогрев — 1 запрос чтобы наполнить кэш
        print("Прогрев...")
        await one_request(client, 0)
        await asyncio.sleep(1)

        # Основной тест
        sem = asyncio.Semaphore(CONCURRENT)

        async def limited(idx):
            async with sem:
                return await one_request(client, idx)

        t_start = time.time()
        results = await asyncio.gather(*[limited(i) for i in range(REQUESTS)])
        total_time = time.time() - t_start

    # Статистика
    ok = [r for r in results if r["status"] == 200]
    errors = [r for r in results if r["status"] != 200]
    times = [r["elapsed"] for r in ok]

    print(f"\n{'='*60}")
    print(f"📊 РЕЗУЛЬТАТЫ")
    print(f"{'='*60}")
    print(f"   Всего запросов:       {REQUESTS}")
    print(f"   ✅ Успешных (200):    {len(ok)}")
    print(f"   ❌ Ошибок:            {len(errors)}")
    print(f"   Общее время:          {total_time:.2f}с")
    print(f"   Запросов/сек:         {REQUESTS / total_time:.1f}")

    if times:
        print(f"\n⏱️  Время ответа (успешные):")
        print(f"   Минимум:              {min(times)*1000:.0f}мс")
        print(f"   Среднее:              {sum(times)/len(times)*1000:.0f}мс")
        print(f"   Максимум:             {max(times)*1000:.0f}мс")

    if errors:
        print(f"\n❗ Ошибки:")
        error_types = {}
        for e in errors:
            t = str(e["status"])
            error_types[t] = error_types.get(t, 0) + 1
        for t, count in error_types.items():
            print(f"   {t}: {count}")


if __name__ == "__main__":
    asyncio.run(main())