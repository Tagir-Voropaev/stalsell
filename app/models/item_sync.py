from sqlalchemy import Column, String, DateTime, Integer
from datetime import datetime
from app.core.database import Base


class ItemSync(Base):
    """Отслеживает последнее обновление каждого предмета."""
    __tablename__ = "item_sync"

    item_id = Column(String(50), primary_key=True)
    last_sync = Column(DateTime, default=datetime.utcnow, nullable=False)
    sync_count = Column(Integer, default=0)
    last_added = Column(Integer, default=0)  # Сколько новых записей при последнем sync