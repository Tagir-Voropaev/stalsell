"""
Сравниваем поля в lots() и price_history() при additional=True.
Цель: понять, где API отдаёт качество и уровень заточки.
"""
import asyncio
import json
from app.services.stalzone_api import StalzoneAPI


ITEM_ID = "qyvk"  # "Вспышка" — популярный, много активных лотов


def dump_record(label, record):
    print(f"--- {label} ---")
    # Универсальный дамп: для Pydantic и для обычных объектов
    if hasattr(record, "model_dump"):
        data = record.model_dump()
    elif hasattr(record, "__dict__"):
        data = record.__dict__
    else:
        data = str(record)
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Обрезаем длинные значения
            val_str = str(value)
            if len(val_str) > 120:
                val_str = val_str[:120] + "..."
            print(f"  {key}: {val_str}")
    else:
        print(f"  {data}")
    print()


async def main():
    api = StalzoneAPI()
    auction = api.client.auction(ITEM_ID)
    
    # =========================================================
    # ЧАСТЬ 1: Активные лоты с additional=True
    # =========================================================
    print("=" * 70)
    print("  АКТИВНЫЕ ЛОТЫ (lots) — additional=True")
    print("=" * 70)
    try:
        lots = await auction.lots(limit=3, additional=True)
        print(f"Получено лотов: {len(lots)}\n")
        for i, lot in enumerate(lots, 1):
            dump_record(f"Лот #{i}", lot)
    except Exception as e:
        print(f"Ошибка: {type(e).__name__}: {e}\n")
    
    # =========================================================
    # ЧАСТЬ 2: История продаж с additional=True
    # =========================================================
    print("=" * 70)
    print("  ИСТОРИЯ ПРОДАЖ (price_history) — additional=True")
    print("=" * 70)
    try:
        history = await auction.price_history(limit=3, additional=True)
        print(f"Получено записей: {len(history)}\n")
        for i, rec in enumerate(history, 1):
            dump_record(f"Продажа #{i}", rec)
    except Exception as e:
        print(f"Ошибка: {type(e).__name__}: {e}\n")
    
    # =========================================================
    # ИТОГ
    # =========================================================
    print("=" * 70)
    print("  ИТОГ")
    print("=" * 70)
    print("Если в 'Лотах' есть quality/level, а в 'Истории' — нет,")
    print("значит, заточку можно показывать только у активных лотов.")


if __name__ == "__main__":
    asyncio.run(main())