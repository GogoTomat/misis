"""
Users Service — единственный владелец таблицы users.

Держит собственную таблицу в shared.db и отдаёт данные только через
HTTP API. Никто другой не имеет права читать эту таблицу напрямую —
это и демонстрирует пара orders_service_bad / orders_service_good.
"""
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Users Service")

# Абсолютный путь до shared.db в корне проекта — не зависит от того,
# из какой директории запущен uvicorn.
DB_PATH = str(Path(__file__).resolve().parent.parent / "shared.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.on_event("startup")
def init_db() -> None:
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email) VALUES (1, 'anna@example.com')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email) VALUES (2, 'boris@example.com')"
    )
    conn.commit()
    conn.close()


@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": row["id"], "email": row["email"]}
