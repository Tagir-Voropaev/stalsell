"""
Фоновый парсер истории продаж.

Стратегия:
- Раз в 15 минут: топ-100 активных предметов
- Раз в час: средние (по алфавиту, ~500)
- Раз в день: все остальные

Запуск:
    python -m scripts.background_parser           # бесконечный цикл
    python -m scripts.background_parser --once    # один проход
    python -m scripts.background_parser --top 100 # только топ-100
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, Base
from app.models.item_sync import ItemSync
from app.models.price_history_cache import PriceHistoryCache
from app.services.stalzone_api import StalzoneAPI
from app.services.items_database import load_items_database

# Инициализация БД
Base.metadata.create_all(bind=engine)

# ================== НАСТРОЙКИ ==================
HOT_INTERVAL_MIN = 15       # Топ-100 — раз в 15 минут
WARM_INTERVAL_MIN = 60      # Средние — раз в час
COLD_INTERVAL_HOURS = 24    # Холодные — раз в сутки
HOT_COUNT = 100             # Сколько считаем «горячими»
WARM_COUNT = 500            # Сколько считаем «средними»
REQUESTS_PER_SECOND = 4     # Не более 4 запросов/сек к API
PAGE_LIMIT = 200            # Свежих записей за раз


def extract_item_id(data_path: str) -> str:
    return data_path.split("/")[-1].replace(".json", "") if data_path else ""


def load_tradable_items():
    """Загружает все торгуемые предметы."""
    db_items = load_items_database()
    if not db_items:
        print("❌ База предметов не найдена. Запусти: python -m scripts.download_items")
        return []

    tradable_path = "data/tradable_items.json"
    tradable = set()
    if os.path.exists(tradable_path):
        import json
        with open(tradable_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            tradable = {k for k, v in data.items() if v.get("tradable")}

    items = [extract_item_id(it.get("data", "")) for it in db_items]
    return [i for i in items if i and (not tradable or i in tradable)]


def get_priority_list(all_items: list, db) -> list:
    """
    Возвращает список предметов, отсортированный по приоритету:
    1. Горячие (никогда не обновлялись + активные)
    2. Средние (давно обновлялись)
    3. Холодные (обновлялись давно, но были малоактивны)
    """
    now = datetime.utcnow()

    # Получаем инфу о последнем sync для всех
    syncs = {s.item_id: s for s in db.query(ItemSync).all()}

    def priority(item_id):
        s = syncs.get(item_id)
        if not s:
            # Никогда не синкали — высший приоритет
            return (0, item_id)
        age_min = (now - s.last_sync).total_seconds() / 60
        if s.last_added > 5:
            # Активный предмет — обновляем часто
            return (1 if age_min > HOT_INTERVAL_MIN else 99, item_id)
        elif s.last_added > 0:
            # Средний — раз в час
            return (2 if age_min > WARM_INTERVAL_MIN else 99, item_id)
        else:
            # Холодный — раз в сутки
            return (3 if age_min > COLD_INTERVAL_HOURS * 60 else 99, item_id)

    return sorted(all_items, key=priority)


async def sync_item(api: StalzoneAPI, item_id: str, db) -> int:
    """Синхронизирует один предмет. Возвращает число новых записей."""
    try:
        fresh = await api.get_item_history_page(item_id, offset=0, limit=PAGE_LIMIT)

        added = 0
        if fresh:
            # Проверяем, что нового
            from sqlalchemy import func
            max_date = db.query(func.max(PriceHistoryCache.date)).filter(
                PriceHistoryCache.item_id == item_id
            ).scalar()

            now = datetime.utcnow()
            for rec in fresh:
                add = rec.get("additional") or {}
                time_val = rec.get("time")
                if not time_val:
                    continue

                try:
                    if isinstance(time_val, str):
                        date_obj = datetime.fromisoformat(time_val.replace("Z", "+00:00"))
                        if date_obj.tzinfo:
                            date_obj = date_obj.replace(tzinfo=None)
                    else:
                        date_obj = time_val
                except Exception:
                    continue

                if max_date and date_obj <= max_date:
                    continue

                row = PriceHistoryCache(
                    item_id=item_id,
                    price=float(rec.get("price", 0)),
                    amount=rec.get("amount", 1),
                    date=date_obj,
                    qlt=add.get("qlt"),
                    ptn=add.get("ptn"),
                    bonus_properties=__import__("json").dumps(
                        add.get("bonus_properties", []), ensure_ascii=False
                    ),
                    it_transf_count=add.get("it_transf_count"),
                    cached_at=now,
                )
                db.add(row)
                added += 1

            db.commit()

        # Обновляем запись в item_sync
        s = db.query(ItemSync).filter(ItemSync.item_id == item_id).first()
        if not s:
            s = ItemSync(item_id=item_id)
            db.add(s)
        s.last_sync = datetime.utcnow()
        s.sync_count = (s.sync_count or 0) + 1
        s.last_added = added
        db.commit()

        return added

    except Exception as e:
        print(f"  ❌ {item_id}: {e}")
        return -1


async def main():
    args = sys.argv[1:]
    once = "--once" in args
    top_only = "--top" in args

    print("=" * 60)
    print("🚀 Фоновый парсер истории продаж")
    print("=" * 60)

    all_items = load_tradable_items()
    print(f"📦 Торгуемых предметов: {len(all_items)}\n")

    if top_only:
        all_items = all_items[:int(args[args.index("--top") + 1])] if "--top" in args and args.index("--top") + 1 < len(args) else all_items[:100]
        print(f"⚙️  Режим --top: {len(all_items)} предметов\n")

    api = StalzoneAPI()
    db = SessionLocal()

    delay = 1.0 / REQUESTS_PER_SECOND

    try:
        while True:
            # Сортируем по приоритету
            priority_items = get_priority_list(all_items, db)

            # Берём только те, что ПОРА обновлять
            now = datetime.utcnow()
            syncs = {s.item_id: s for s in db.query(ItemSync).all()}

            to_sync = []
            for item_id in priority_items:
                s = syncs.get(item_id)
                if not s:
                    to_sync.append(item_id)
                    continue
                age_min = (now - s.last_sync).total_seconds() / 60
                # Определяем интервал
                if s.last_added > 5:
                    interval = HOT_INTERVAL_MIN
                elif s.last_added > 0:
                    interval = WARM_INTERVAL_MIN
                else:
                    interval = COLD_INTERVAL_HOURS * 60

                if age_min >= interval:
                    to_sync.append(item_id)

            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} — предметов к обновлению: {len(to_sync)}")
            print(f"   (hot: {HOT_INTERVAL_MIN}м, warm: {WARM_INTERVAL_MIN}м, cold: {COLD_INTERVAL_HOURS}ч)")

            if not to_sync:
                print("   Всё актуально, ждём 5 минут...")
                if once: break
                await asyncio.sleep(300)
                continue

            total_added = 0
            processed = 0

            for item_id in to_sync:
                added = await sync_item(api, item_id, db)
                if added >= 0:
                    total_added += added
                    processed += 1

                    if processed % 50 == 0:
                        print(f"   Прогресс: {processed}/{len(to_sync)} (добавлено: {total_added})")

                # Пауза между запросами
                await asyncio.sleep(delay)

            print(f"✅ Цикл завершён: обработано {processed}, добавлено {total_added} новых записей")

            if once:
                break

            # Ждём до следующего цикла
            print("💤 Ждём 5 минут до следующего цикла...\n")
            await asyncio.sleep(300)

    except KeyboardInterrupt:
        print("\n\n🛑 Остановка парсера...")
    finally:
        db.close()
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())