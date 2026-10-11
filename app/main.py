from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import items, auth
from app.core.database import engine, Base
from app.models import user, price_history_cache, item_sync
# Создаём таблицы в БД
Base.metadata.create_all(bind=engine)

app = FastAPI(title="StalSell API")

app.include_router(items.router)
app.include_router(auth.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    return {"message": "StalSell API работает. Перейдите на /static/index.html"}