import os
import json
import time as _time
import asyncio
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.services.stalzone_api import StalzoneAPI
from app.services.items_database import load_items_database
from app.core.database import get_db, SessionLocal
from app.models.price_history_cache import PriceHistoryCache

router = APIRouter(prefix="/api/items", tags=["items"])
api = StalzoneAPI()

# ================== КОНСТАНТЫ ==================
CACHE_TTL_MEMORY = 30
QUICK_LIMIT = 1000
DEEP_LIMIT = 20000

_cache: dict = {}

# 🆕 Защита от спама задач синхронизации
_syncing_items: set = set()
_synced_recently: dict = {}
SYNC_COOLDOWN_SECONDS = 300

# 🆕 Ограничение одновременных API-запросов
_api_semaphore: asyncio.Semaphore | None = None


def extract_item_id(data_path: str) -> str:
    return data_path.split("/")[-1].replace(".json", "") if data_path else ""


# ================== ТОРГУЕМЫЕ ПРЕДМЕТЫ ==================
def load_tradable_set() -> set:
    path = "data/tradable_items.json"
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item_id for item_id, info in data.items() if info.get("tradable")}
    except Exception:
        return set()


_tradable_cache = None


def get_tradable_set() -> set:
    global _tradable_cache
    if _tradable_cache is None:
        _tradable_cache = load_tradable_set()
    return _tradable_cache


def search_items_by_name_or_category(query: str, category: str, limit: int = 20):
    db = load_items_database()
    if not db:
        return []

    tradable = get_tradable_set()
    query_lower = query.lower().strip()
    results = []

    for item in db:
        item_id = extract_item_id(item.get("data", ""))
        if tradable and item_id not in tradable:
            continue

        # Категория из пути: /items/artefact/... → 'artefact'
        data_path = item.get("data", "")
        item_category = ""
        if data_path:
            parts = data_path.strip("/").split("/")
            if len(parts) >= 2:
                item_category = parts[1]

        if category and item_category != category:
            continue

        name_lines = item.get("name", {}).get("lines", {})
        ru_name = name_lines.get("ru", "")

        if query_lower and query_lower not in ru_name.lower():
            continue

        if ru_name:
            results.append({
                "id": item_id,
                "name": ru_name,
                "icon": item.get("icon", ""),
                "category": item_category,
            })
            if len(results) >= limit:
                break

    return results


# ================== РАБОТА С SQLITE КЭШЕМ ==================
def count_cached(db: Session, item_id: str) -> int:
    return db.query(func.count(PriceHistoryCache.id)).filter(
        PriceHistoryCache.item_id == item_id
    ).scalar() or 0


def get_cache_last_update(db: Session, item_id: str):
    return db.query(func.max(PriceHistoryCache.cached_at)).filter(
        PriceHistoryCache.item_id == item_id
    ).scalar()


def get_max_date(db: Session, item_id: str):
    return db.query(func.max(PriceHistoryCache.date)).filter(
        PriceHistoryCache.item_id == item_id
    ).scalar()


def save_history_to_cache(db: Session, item_id: str, records: list, append: bool = True):
    """
    Сохраняет записи в SQLite.
    🆕 Использует bulk_insert_mappings — быстрее в 5-10 раз.
    """
    now = datetime.utcnow()
    max_d = get_max_date(db, item_id) if append else None

    rows = []
    seen_dates = set()

    for rec in records:
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

        if append and max_d and date_obj <= max_d:
            continue

        # Защита от дубликатов внутри одного batch
        if date_obj in seen_dates:
            continue
        seen_dates.add(date_obj)

        rows.append({
            "item_id": item_id,
            "price": float(rec.get("price", 0)),
            "amount": rec.get("amount", 1),
            "date": date_obj,
            "qlt": add.get("qlt"),
            "ptn": add.get("ptn"),
            "bonus_properties": json.dumps(add.get("bonus_properties", []), ensure_ascii=False),
            "it_transf_count": add.get("it_transf_count"),
            "cached_at": now,
        })

    if not rows:
        return 0

    db.bulk_insert_mappings(PriceHistoryCache, rows)
    db.commit()
    return len(rows)


def load_history_from_cache(db: Session, item_id: str, limit: int):
    rows = db.query(PriceHistoryCache).filter(
        PriceHistoryCache.item_id == item_id
    ).order_by(desc(PriceHistoryCache.date)).limit(limit).all()

    result = []
    for row in rows:
        try:
            bonus = json.loads(row.bonus_properties) if row.bonus_properties else []
        except Exception:
            bonus = []
        result.append({
            "price": row.price,
            "amount": row.amount,
            "date": row.date.isoformat(),
            "qlt": row.qlt,
            "ptn": row.ptn,
            "bonus_properties": bonus,
            "it_transf_count": row.it_transf_count,
        })
    return result


# ================== ЭНДПОИНТЫ ==================
@router.get("/search")
async def search_items(
    q: str = Query("", description="Поисковый запрос"),
    cat: str = Query("", description="Категория"),
    limit: int = Query(20, ge=1, le=100),
):
    if not q and not cat:
        return []
    return search_items_by_name_or_category(q, cat, limit)


@router.get("/{item_id}/info")
async def get_item_info(item_id: str):
    db = load_items_database()
    if not db:
        return {"id": item_id, "name": item_id, "icon": "", "category": ""}

    for item in db:
        data_path = item.get("data", "")
        file_id = data_path.split("/")[-1].replace(".json", "") if data_path else ""
        if file_id == item_id:
            name_lines = item.get("name", {}).get("lines", {})

            category = ""
            if data_path:
                parts = data_path.strip("/").split("/")
                if len(parts) >= 2:
                    category = parts[1]

            return {
                "id": item_id,
                "name": name_lines.get("ru", item_id),
                "icon": item.get("icon", ""),
                "category": category,
            }
    return {"id": item_id, "name": item_id, "icon": "", "category": ""}


@router.get("/{item_id}/history")
async def get_item_history(
    item_id: str,
    limit: int = Query(QUICK_LIMIT, ge=1, le=20000),
    refresh: bool = Query(False, description="Принудительно обновить с API"),
    db: Session = Depends(get_db),
):
    """История продаж с тройным кэшированием."""
    t_start = _time.time()

    def log(msg):
        print(f"[HIST {_time.time()-t_start:6.1f}с] {item_id}: {msg}")

    log(f"СТАРТ, limit={limit}, refresh={refresh}")

    memory_key = f"hist:{item_id}:{limit}"
    now = datetime.utcnow()

    # 1️⃣ In-memory кэш
    if not refresh and memory_key in _cache:
        cached = _cache[memory_key]
        if (now - cached["timestamp"]).total_seconds() < CACHE_TTL_MEMORY:
            log(f"→ память ({len(cached['data'])} записей)")
            return JSONResponse(
                content=cached["data"],
                headers={"Cache-Control": "public, max-age=30"},
            )

    # 2️⃣ SQLite через threadpool
    cached_count = await asyncio.to_thread(count_cached, db, item_id)
    log(f"в SQLite {cached_count} записей")

    if cached_count > 0 and not refresh:
        result = await asyncio.to_thread(load_history_from_cache, db, item_id, limit)
        log(f"ГОТОВО, отдаём {len(result)} (из БД)")

        # 🆕 Умный запуск синхронизации
        _schedule_sync_if_needed(item_id)

        _cache[memory_key] = {"data": result, "timestamp": now}
        return JSONResponse(
            content=result,
            headers={"Cache-Control": "public, max-age=30"},
        )

    # 3️⃣ БД пуста — API
    log(f"БД пуста, идём в API за {limit} записей...")
    try:
        records = await api.get_item_history_page(item_id, offset=0, limit=limit)
        log(f"← из API получено {len(records)}")
    except Exception as e:
        log(f"ОШИБКА API: {e}")
        raise HTTPException(status_code=502, detail=f"Ошибка API STALZONE: {e}")

    if not records:
        return JSONResponse(content=[])

    await asyncio.to_thread(save_history_to_cache, db, item_id, records, False)
    log(f"сохранено {len(records)} (первый раз)")

    result = await asyncio.to_thread(load_history_from_cache, db, item_id, limit)
    log(f"ГОТОВО, отдаём {len(result)}")
    _cache[memory_key] = {"data": result, "timestamp": now}
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=30"},
    )


# ================== УПРАВЛЕНИЕ СИНХРОНИЗАЦИЕЙ ==================
def _schedule_sync_if_needed(item_id: str):
    """Запускает фоновую синхронизацию с защитой от спама."""
    now = datetime.utcnow()

    if item_id in _syncing_items:
        return

    last = _synced_recently.get(item_id)
    if last and (now - last).total_seconds() < SYNC_COOLDOWN_SECONDS:
        return

    _syncing_items.add(item_id)
    asyncio.create_task(_sync_new_records(item_id))


async def _sync_new_records(item_id: str):
    """Забирает свежие записи, добавляет только новые."""
    db = SessionLocal()
    try:
        max_date = await asyncio.to_thread(get_max_date, db, item_id)
        if not max_date:
            return

        print(f"[SYNC] {item_id}: проверяем новее {max_date.isoformat()}")

        global _api_semaphore
        if _api_semaphore is None:
            _api_semaphore = asyncio.Semaphore(5)

        async with _api_semaphore:
            fresh = await api.get_item_history_page(item_id, offset=0, limit=200)

        if not fresh:
            return

        added = await asyncio.to_thread(save_history_to_cache, db, item_id, fresh, True)

        now = datetime.utcnow()
        await asyncio.to_thread(
            db.query(PriceHistoryCache)
            .filter(PriceHistoryCache.item_id == item_id)
            .update,
            {"cached_at": now},
        )
        await asyncio.to_thread(db.commit)

        if added > 0:
            print(f"[SYNC] {item_id}: добавлено {added} новых")
        else:
            print(f"[SYNC] {item_id}: новых нет")
    except Exception as e:
        print(f"[SYNC] {item_id}: ошибка {e}")
    finally:
        db.close()
        _syncing_items.discard(item_id)
        _synced_recently[item_id] = datetime.utcnow()

        # Чистим старые записи раз в 1000 элементов
        if len(_synced_recently) > 1000:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            to_remove = [k for k, v in _synced_recently.items() if v < cutoff]
            for k in to_remove:
                _synced_recently.pop(k, None)


@router.get("/{item_id}/history/deep")
async def get_item_history_deep(
    item_id: str,
    limit: int = Query(DEEP_LIMIT, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    """Глубокая загрузка."""
    t_start = _time.time()

    def log(msg):
        print(f"[DEEP {_time.time()-t_start:6.1f}с] {item_id}: {msg}")

    log(f"СТАРТ, limit={limit}")

    cached_count = await asyncio.to_thread(count_cached, db, item_id)
    log(f"в кэше {cached_count}")

    if cached_count >= limit:
        result = await asyncio.to_thread(load_history_from_cache, db, item_id, limit)
        log(f"ГОТОВО, отдаём {len(result)} (из БД)")
        return JSONResponse(content=result)

    log(f"идём в API за {limit} записей...")
    try:
        records = await api.get_item_history_page(item_id, offset=0, limit=limit)
        log(f"← из API получено {len(records)}")
    except Exception as e:
        log(f"ОШИБКА API: {e}")
        result = await asyncio.to_thread(load_history_from_cache, db, item_id, limit)
        if result:
            return JSONResponse(content=result)
        raise HTTPException(status_code=502, detail=f"Ошибка API STALZONE: {e}")

    if records:
        if cached_count == 0:
            await asyncio.to_thread(save_history_to_cache, db, item_id, records, False)
            log(f"сохранено {len(records)} (первый раз)")
        else:
            added = await asyncio.to_thread(save_history_to_cache, db, item_id, records, True)
            log(f"добавлено {added} новых (из {len(records)})")

    result = await asyncio.to_thread(load_history_from_cache, db, item_id, limit)
    log(f"ГОТОВО, отдаём {len(result)}")
    return JSONResponse(content=result)


@router.get("/{item_id}/lots")
async def get_item_lots(item_id: str, limit: int = Query(200, le=200)):
    cache_key = f"lots:{item_id}:{limit}"
    now = datetime.utcnow()
    if cache_key in _cache:
        cached = _cache[cache_key]
        if (now - cached["timestamp"]).total_seconds() < CACHE_TTL_MEMORY:
            return JSONResponse(content=cached["data"])

    try:
        lots = await api.get_active_lots(item_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка API STALZONE: {e}")

    result = []
    for lot in lots:
        add = lot.get("additional") or {}
        result.append({
            "buyout_price": float(lot.get("buyoutPrice") or 0),
            "start_price":  float(lot.get("startPrice") or 0),
            "amount":       lot.get("amount", 1),
            "start_time":   lot.get("startTime"),
            "end_time":     lot.get("endTime"),
            "qlt": add.get("qlt"),
            "ptn": add.get("ptn"),
            "bonus_properties": add.get("bonus_properties", []),
            "it_transf_count": add.get("it_transf_count"),
        })

    _cache[cache_key] = {"data": result, "timestamp": now}
    return JSONResponse(content=result)