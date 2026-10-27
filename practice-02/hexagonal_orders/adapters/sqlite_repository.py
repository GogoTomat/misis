import sqlite3
from domain.models import Order
from domain.ports import OrderRepository


class SqliteOrderRepository(OrderRepository):
    def __init__(self, db_path: str = "orders_hex.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._conn()
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

    def save(self, order: Order) -> Order:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO orders (user_id, item, status) VALUES (?, ?, ?)",
            (order.user_id, order.item, order.status),
        )
        conn.commit()
        order.id = cur.lastrowid
        conn.close()
        return order

    def find_by_id(self, order_id: int) -> Order | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return Order(id=row["id"], user_id=row["user_id"], item=row["item"], status=row["status"])
