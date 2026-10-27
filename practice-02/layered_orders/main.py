import sqlite3
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Orders (Layered)")

DB_PATH = "orders.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created'
        )"""
    )
    conn.commit()
    conn.close()


_init_db()


class OrdersDB:
    def save(self, user_id: int, item: str) -> int:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO orders (user_id, item) VALUES (?, ?)", (user_id, item)
        )
        conn.commit()
        order_id = cur.lastrowid
        conn.close()
        return order_id

    def find_by_id(self, order_id: int):
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None


orders_db = OrdersDB()


def place_order(user_id: int, item: str) -> int:
    """Бизнес-правило: нельзя оформить заказ без товара."""
    if not item:
        raise ValueError("item is required")
    return orders_db.save(user_id, item)


def get_order(order_id: int) -> dict:
    order = orders_db.find_by_id(order_id)
    if order is None:
        raise ValueError("order not found")
    # бизнес-правило: скрываем внутренний статус 'created' от клиента,
    # показываем человекочитаемый — этой логики НЕТ в layer bridging ниже
    order["status_label"] = "Обрабатывается" if order["status"] == "created" else order["status"]
    return order


@app.post("/orders")
def create_order(user_id: int, item: str):
    try:
        order_id = place_order(user_id, item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"order_id": order_id}


@app.get("/orders/{order_id}")
def read_order(order_id: int):
    try:
        return get_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@app.get("/orders/{order_id}/raw")
def read_order_raw(order_id: int):
    row = orders_db.find_by_id(order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    return row  # никакого status_label, бизнес-правило не применено
