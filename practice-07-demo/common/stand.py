import sys

import httpx

from common.config import ORDERS_URL, PAYMENTS_URL, STOCK_URL
from common.db import connect
from common.schema import CARDS, PRODUCTS


async def drop_prepared() -> None:
    for database in ("orders", "stock", "payments"):
        conn = await connect(database)
        for row in await conn.fetch("SELECT gid FROM pg_prepared_xacts WHERE database = $1", database):
            await conn.execute(f"ROLLBACK PREPARED '{row['gid']}'")
        await conn.close()


async def reset(available: dict[str, int] | None = None) -> None:
    await drop_prepared()
    orders = await connect("orders")
    await orders.execute("TRUNCATE saga_log, sagas, orders, prices")
    await orders.executemany("INSERT INTO prices VALUES ($1, $2)", [(p[0], p[3]) for p in PRODUCTS])
    await orders.close()
    stock = await connect("stock")
    await stock.execute("TRUNCATE processed, reservations, products CASCADE")
    rows = [(p[0], p[1], (available or {}).get(p[0], p[2])) for p in PRODUCTS]
    await stock.executemany("INSERT INTO products VALUES ($1, $2, $3)", rows)
    await stock.close()
    payments = await connect("payments")
    await payments.execute("TRUNCATE processed, payments, cards")
    await payments.executemany("INSERT INTO cards VALUES ($1, $2)", CARDS)
    await payments.close()
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            await client.post(f"{STOCK_URL}/admin/config")
            await client.post(f"{PAYMENTS_URL}/admin/config")
            await client.get(f"{ORDERS_URL}/docs")
        except httpx.TransportError:
            print("Сервисы не отвечают. Во втором окне запустите: python run_services.py")
            sys.exit(1)


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False, timeout=10)
