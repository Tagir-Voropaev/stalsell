"""
Быстрый сканер торгуемых предметов.
Использует параллельные запросы (до N одновременных).

Результат → data/tradable_items.json
Возобновляется с места остановки.
Флаги:
    --force          Перепроверить всё с нуля
    --item <id>      Проверить один предмет
    --concurrent N   Число параллельных запросов (по умолчанию 8)
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.items_database import load_items_database
from app.services.stalzone_api import StalzoneAPI

PROGRESS_FILE = "data/tradable_items.json"
SAVE_EVERY = 100              # сохраняем прогресс каждые N предметов
DEFAULT_CONCURRENT = 8        # одновременных запросов
BATCH_SIZE = 32               # размер пачки для обработки


def extract_item_id(data_path: str) -> str:
    return data_path.split("/")[-1].replace(".json", "") if data_path else ""


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(progress: dict):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


async def check_item(api: StalzoneAPI, item_id: str, sem: asyncio.Semaphore) -> dict:
    """Проверяет один предмет. Использует семафор для ограничения параллельности."""
    async with sem:
        result = {"tradable": False, "history_count": 0, "lots_count": 0}

        # Сначала история
        try:
            history = await api.get_item_history(item_id, limit=1)
            if history:
                result["history_count"] = len(history)
                result["tradable"] = True
                return result
        except Exception as e:
            if "429" in str(e):
                raise  # пробрасываем — обработаем наверху

        # Если истории нет — проверяем активные лоты
        try:
            lots = await api.get_active_lots(item_id, limit=1)
            if lots:
                result["lots_count"] = len(lots)
                result["tradable"] = True
        except Exception as e:
            if "429" in str(e):
                raise

        return result


async def process_batch(api, item_ids, sem, progress, stats):
    """Обрабатывает пачку предметов параллельно."""
    async def safe_check(iid):
        try:
            res = await check_item(api, iid, sem)
            return iid, res, None
        except Exception as e:
            return iid, None, str(e)

    tasks = [safe_check(iid) for iid in item_ids]
    results = await asyncio.gather(*tasks)

    for iid, res, err in results:
        if err:
            if "429" in err:
                # Rate limit — вернём в очередь, повторим позже
                stats["rate_limited"] += 1
                continue
            progress[iid] = {"tradable": False, "error": err[:100]}
            stats["errors"] += 1
        else:
            progress[iid] = res
            if res["tradable"]:
                stats["tradable"] += 1
        stats["processed"] += 1


async def main():
    args = sys.argv[1:]
    force = "--force" in args
    single_item = None
    concurrent = DEFAULT_CONCURRENT

    if "--item" in args:
        idx = args.index("--item")
        if idx + 1 < len(args):
            single_item = args[idx + 1]
    if "--concurrent" in args:
        idx = args.index("--concurrent")
        if idx + 1 < len(args):
            try:
                concurrent = int(args[idx + 1])
            except ValueError:
                pass

    print("📦 Загружаем базу предметов...")
    db_items = load_items_database()
    if not db_items:
        print("❌ База не найдена. Запусти: python -m scripts.download_items")
        return

    all_items = [extract_item_id(it.get("data", "")) for it in db_items]
    all_items = [i for i in all_items if i]
    print(f"   Всего предметов: {len(all_items)}")

    progress = load_progress()

    if single_item:
        to_check = [single_item] if single_item in all_items else []
        if not to_check:
            print(f"❌ Предмет '{single_item}' не найден")
            return
    else:
        if force:
            to_check = all_items
            print("⚠️  Режим --force: перепроверяем ВСЁ")
        else:
            to_check = [i for i in all_items if i not in progress]
            print(f"🔄 Уже проверено: {len(progress)}")
            print(f"⏳ Осталось проверить: {len(to_check)}")

    if not to_check:
        print("✅ Все предметы уже проверены!")
        print_summary(progress)
        return

    print(f"\n🔑 Инициализируем API (параллельно: {concurrent})...")
    api = StalzoneAPI()

    # Прогрев токена — чтобы не было гонки при первом батче
    await api._get_token()

    # Семафор
    sem = asyncio.Semaphore(concurrent)

    # Статистика
    stats = {
        "processed": 0,
        "tradable": 0,
        "errors": 0,
        "rate_limited": 0,
    }
    start_time = time.time()
    last_save = 0

    print(f"\n⏱️  Стартуем...\n")

    # Разбиваем на батчи
    batches = [to_check[i:i + BATCH_SIZE] for i in range(0, len(to_check), BATCH_SIZE)]

    try:
        for batch_idx, batch in enumerate(batches):
            try:
                await process_batch(api, batch, sem, progress, stats)
            except Exception as e:
                if "429" in str(e):
                    print(f"\n⏸️  Rate limit, пауза 60с...")
                    await asyncio.sleep(60)
                    # Повторяем батч
                    await process_batch(api, batch, sem, progress, stats)
                else:
                    print(f"\n⚠️  Ошибка батча: {e}")

            # Прогресс
            processed = stats["processed"]
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = len(to_check) - processed
            eta = remaining / rate if rate > 0 else 0
            percent = processed / len(to_check) * 100 if to_check else 100

            bar = make_bar(percent)
            print(f"\r{bar} {percent:5.1f}% | "
                  f"✅ {stats['tradable']:4d} | "
                  f"❌ {stats['errors']:3d} | "
                  f"⚡ {rate:.1f}/с | "
                  f"⏱️  {format_time(eta)}",
                  end="", flush=True)

            # Сохранение раз в SAVE_EVERY предметов
            if processed - last_save >= SAVE_EVERY:
                save_progress(progress)
                last_save = processed

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано. Сохраняем...")
        save_progress(progress)
        print(f"✅ Проверено в этой сессии: {stats['processed']}")
        return

    save_progress(progress)
    print()

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Готово за {format_time(elapsed)}")
    print(f"   Проверено: {stats['processed']}")
    print(f"   Торгуется: {stats['tradable']}")
    print(f"   Ошибок: {stats['errors']}")
    print(f"{'='*60}")

    print_summary(progress)


def print_summary(progress: dict):
    total = len(progress)
    if not total:
        return
    tradable = sum(1 for v in progress.values() if v.get("tradable"))
    not_tradable = total - tradable

    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего в базе: {total}")
    print(f"   ✅ Торгуется: {tradable} ({tradable/total*100:.1f}%)")
    print(f"   ❌ Не торгуется: {not_tradable} ({not_tradable/total*100:.1f}%)")
    print(f"\n💾 Файл: {PROGRESS_FILE}")


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}с"
    if seconds < 3600:
        return f"{seconds/60:.1f}м"
    return f"{seconds/3600:.1f}ч"


def make_bar(percent: float, width: int = 30) -> str:
    filled = int(width * percent / 100)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


if __name__ == "__main__":
    asyncio.run(main())