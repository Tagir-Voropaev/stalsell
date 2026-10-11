# 🎮 StalSell — История аукциона STALZONE

Сервис для просмотра истории продаж предметов на аукционе STALZONE.

![StalSell](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

## ✨ Возможности

- 📊 **Интерактивный график** истории продаж (Plotly)
- 🔍 **Умный поиск** с автокомплитом
- 🎨 **Фильтры** по редкости и уровню заточки
- 💾 **SQLite-кэш** — повторные запросы мгновенные
- 🌐 **Автоматический парсер** — данные обновляются 24/7
- 🔐 **Авторизация** — регистрация и вход
- 📱 **Адаптивный дизайн** — работает на телефоне

## 🛠 Технологии

| Слой | Стек |
|---|---|
| **Backend** | FastAPI, SQLAlchemy, SQLite, httpx |
| **Frontend** | Vanilla JS, Plotly, Bootstrap Icons |
| **API** | STALZONE API (OAuth 2.0) |
| **Данные** | SQLite (WAL-mode), JSON-кэш |

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/твой_ник/stalsell.git
cd stalsell