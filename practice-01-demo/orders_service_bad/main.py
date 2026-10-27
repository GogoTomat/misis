"""
Orders Service — ПЛОХОЙ вариант.

Читает таблицу users напрямую из чужой базы данных, в обход
Users Service. Демонстрирует скрытую связность: если Users
поменяет схему таблицы, этот сервис сломается незаметно.
"""
from pathlib import Path
import sqlite3

from fastapi import FastAPI

app = FastAPI(title="Orders Service (BAD: прямой доступ к чужой БД)")

# Тот же файл, что использует users_service — вот в чём и нарушение.
DB_PATH = str(Path(__file__).resolve().parent.parent / "shared.db")


@app.post("/orders")
def create_order(user_id: int, item: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute(
        "SELECT email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if user is None:
        return {"error": "user not found"}
    return {"item": item, "user_email": user["email"]}
