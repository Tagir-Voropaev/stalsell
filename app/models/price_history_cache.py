from sqlalchemy import Column, Integer, String, Float, DateTime, Index, Text
from datetime import datetime
from app.core.database import Base


class PriceHistoryCache(Base):
    """Кэш истории продаж предметов для быстрой отдачи."""
    __tablename__ = "price_history_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(50), index=True, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Integer, default=1)
    date = Column(DateTime, nullable=False)
    qlt = Column(Integer, nullable=True)
    ptn = Column(Integer, nullable=True)
    bonus_properties = Column(Text, nullable=True)  # JSON-строка
    it_transf_count = Column(Integer, nullable=True)
    cached_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_item_date", "item_id", "date"),
    )