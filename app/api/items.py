import os
import json
import time as _time
import asyncio
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from app.services.stalzone_api import StalzoneAPI
from app.services.items_database import load_items_database
from app.core.database import get_db, SessionLocal
from app.models.price_history_cache import PriceHistoryCache

router = APIRouter(prefix="/api/items", tags=["items"])
api = StalzoneAPI()

# ================== КОНСТАНТЫ ==================
CACHE_TTL_MEMORY = 30
QUICK_LIMIT = 1000
DEEP_LIMIT = 50000

_cache: dict = {}


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
    """Поиск по названию ИЛИ по категории."""
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

        # Извлекаем категорию: /items/artefact/... → 'artefact'
        data_path = item.get("data", "")
        item_category = ""
        if data_path:
            parts = data_path.strip("/").split("/")
            if len(parts) >= 2:
                item_category = parts[1]

        # Фильтр по категории
        if category and item_category != category:
            continue

        name_lines = item.get("name", {}).get("lines", {})
        ru_name = name_lines.get("ru", "")

        # Фильтр по названию
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
    append=True — добавляет только новые (по дате > max_date).
    append=False — полная замена (только для первого захода).
    """
    now = datetime.utcnow()
    max_d = get_max_date(db, item_id) if append else None

    added = 0
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

        row = PriceHistoryCache(
            item_id=item_id,
            price=float(rec.get("price", 0)),
            amount=rec.get("amount", 1),
            date=date_obj,
            qlt=add.get("qlt"),
            ptn=add.get("ptn"),
            bonus_properties=json.dumps(add.get("bonus_properties", []), ensure_ascii=False),
            it_transf_count=add.get("it_transf_count"),
            cached_at=now,
        )
        db.add(row)
        added += 1

    db.commit()
    return added


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
    cat: str = Query("", description="Категория (artefact, weapon, armor, other)"),
    limit: int = Query(20, ge=1, le=100),
):
    if not q and not cat:
        return []
    return search_items_by_name_or_category(q, cat, limit)


@router.get("/{item_id}/info")
async def get_item_info(item_id: str):
    """Возвращает название, иконку и категорию предмета."""
    db = load_items_database()
    if not db:
        return {"id": item_id, "name": item_id, "icon": "", "category": ""}

    for item in db:
        data_path = item.get("data", "")
        file_id = data_path.split("/")[-1].replace(".json", "") if data_path else ""
        if file_id == item_id:
            name_lines = item.get("name", {}).get("lines", {})

            # 🔑 Извлекаем категорию из пути: /items/artefact/biochemical/zyv9.json
            #   data_path → 'items/artefact/biochemical/zyv9.json'
            #   category → 'artefact'
            category = ""
            if data_path:
                parts = data_path.strip("/").split("/")
                if len(parts) >= 2:
                    category = parts[1]  # 'artefact', 'weapon', 'armor', 'other', etc.

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
    limit: int = Query(QUICK_LIMIT, ge=1, le=50000),
    refresh: bool = Query(False, description="Принудительно обновить с API"),
    db: Session = Depends(get_db),
):
    """
    История продаж с накопительным кэшем.
    Данные НЕ УДАЛЯЮТСЯ. Только накапливаются.
    """
    t_start = _time.time()

    def log(msg):
        print(f"[HIST {_time.time()-t_start:6.1f}с] {item_id}: {msg}")

    log(f"СТАРТ, limit={limit}, refresh={refresh}")

    memory_key = f"hist:{item_id}:{limit}"
    now = datetime.utcnow()

    # 1️⃣ In-memory кэш (30 сек)
    if not refresh and memory_key in _cache:
        cached = _cache[memory_key]
        if (now - cached["timestamp"]).total_seconds() < CACHE_TTL_MEMORY:
            log(f"→ память ({len(cached['data'])} записей)")
            return JSONResponse(
                content=cached["data"],
                headers={"Cache-Control": "public, max-age=30"},
            )

    # 2️⃣ SQLite
    cached_count = count_cached(db, item_id)
    log(f"в SQLite {cached_count} записей")

    if cached_count > 0 and not refresh:
        result = load_history_from_cache(db, item_id, limit)
        log(f"ГОТОВО, отдаём {len(result)} (из БД)")

        # Фоновая синхронизация свежих записей
        asyncio.create_task(_sync_new_records(item_id))

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

    save_history_to_cache(db, item_id, records, append=False)
    log(f"сохранено {len(records)} (первый раз)")

    result = load_history_from_cache(db, item_id, limit)
    log(f"ГОТОВО, отдаём {len(result)}")
    _cache[memory_key] = {"data": result, "timestamp": now}
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "public, max-age=30"},
    )


# ================== ФОНОВАЯ СИНХРОНИЗАЦИЯ ==================
async def _sync_new_records(item_id: str):
    """Спрашивает свежие записи и добавляет только те, что новее max_date."""
    db = SessionLocal()
    try:
        max_date = get_max_date(db, item_id)
        if not max_date:
            return

        print(f"[SYNC] {item_id}: проверяем записи новее {max_date.isoformat()}")
        fresh = await api.get_item_history_page(item_id, offset=0, limit=200)

        if not fresh:
            return

        added = save_history_to_cache(db, item_id, fresh, append=True)

        now = datetime.utcnow()
        db.query(PriceHistoryCache).filter(
            PriceHistoryCache.item_id == item_id
        ).update({"cached_at": now})
        db.commit()

        if added > 0:
            print(f"[SYNC] {item_id}: добавлено {added} новых")
        else:
            print(f"[SYNC] {item_id}: новых нет")
    except Exception as e:
        print(f"[SYNC] {item_id}: ошибка {e}")
    finally:
        db.close()


@router.get("/{item_id}/history/deep")
async def get_item_history_deep(
    item_id: str,
    limit: int = Query(DEEP_LIMIT, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    """
    Глубокая загрузка. НЕ БЛОКИРУЕТ — если в БД мало, отдаём что есть,
    а остаток тянем из API в фоне.
    """
    t_start = _time.time()

    def log(msg):
        print(f"[DEEP {_time.time()-t_start:6.1f}с] {item_id}: {msg}")

    log(f"СТАРТ, limit={limit}")

    cached_count = count_cached(db, item_id)
    log(f"в кэше {cached_count}")

    # 🔑 Если в БД есть — отдаём СРАЗУ и запускаем фоновую догрузку
    if cached_count > 0:
        result = load_history_from_cache(db, item_id, limit)
        log(f"ГОТОВО, отдаём {len(result)} (из БД)")

        # 🆕 Если в БД меньше, чем нужно — догружаем остаток в фоне
        if cached_count < limit:
            log(f"в БД меньше чем нужно — запускаем фоновую догрузку до {limit}")
            asyncio.create_task(_deep_fetch_in_background(item_id, limit))
        else:
            log("в БД достаточно данных, фон не нужен")

        return JSONResponse(content=result)

    # БД пуста — первый заход, тянем полностью
    log(f"БД пуста, идём в API за {limit} записей...")
    try:
        records = await api.get_item_history_page(item_id, offset=0, limit=limit)
        log(f"← из API получено {len(records)}")
    except Exception as e:
        log(f"ОШИБКА API: {e}")
        raise HTTPException(status_code=502, detail=f"Ошибка API STALZONE: {e}")

    if records:
        save_history_to_cache(db, item_id, records, append=False)
        log(f"сохранено {len(records)} (первый раз)")

    result = load_history_from_cache(db, item_id, limit)
    log(f"ГОТОВО, отдаём {len(result)}")
    return JSONResponse(content=result)


# 🆕 Фоновая догрузка глубокой истории
async def _deep_fetch_in_background(item_id: str, target_limit: int):
    """Тянет из API до target_limit записей и добавляет в БД."""
    db = SessionLocal()
    try:
        cached_count = count_cached(db, item_id)
        if cached_count >= target_limit:
            print(f"[BG-DEEP] {item_id}: уже {cached_count} >= {target_limit}, пропускаем")
            return

        print(f"[BG-DEEP] {item_id}: тянем {target_limit} (в БД {cached_count})")
        records = await api.get_item_history_page(item_id, offset=0, limit=target_limit)

        if not records:
            print(f"[BG-DEEP] {item_id}: API вернул пусто")
            return

        added = save_history_to_cache(db, item_id, records, append=True)

        # Обновляем cached_at
        now = datetime.utcnow()
        db.query(PriceHistoryCache).filter(
            PriceHistoryCache.item_id == item_id
        ).update({"cached_at": now})
        db.commit()

        print(f"[BG-DEEP] {item_id}: добавлено {added} новых, всего {count_cached(db, item_id)}")
    except Exception as e:
        print(f"[BG-DEEP] {item_id}: ошибка {e}")
    finally:
        db.close()

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