import asyncio

import asyncpg

from common.db import connect
from common.log import log, title
from common.stand import reset


async def prepare(conn: asyncpg.Connection, sql: str, args: tuple, gid: str, who: str) -> None:
    await conn.execute("BEGIN")
    await conn.execute(sql, *args)
    await conn.execute(f"PREPARE TRANSACTION '{gid}'")
    log(who, f"PREPARE TRANSACTION '{gid}' — «да», строки заблокированы")


async def prepared(database: str) -> list[str]:
    conn = await connect(database)
    rows = await conn.fetch("SELECT gid FROM pg_prepared_xacts WHERE database = $1", database)
    await conn.close()
    return [r["gid"] for r in rows]


async def book_available() -> int:
    conn = await connect("stock")
    value = await conn.fetchval("SELECT available FROM products WHERE id = 'book'")
    await conn.close()
    return value


async def two_phase(order_id: str, crash: bool) -> None:
    orders, stock = await connect("orders"), await connect("stock")
    await prepare(
        orders,
        "INSERT INTO orders (id, customer, product_id, qty, amount, card, status) VALUES ($1, 'anna', 'book', 2, 2400, '-', 'CONFIRMED')",
        (order_id,), f"{order_id}-orders", "orders db",
    )
    await prepare(
        stock, "UPDATE products SET available = available - 2 WHERE id = 'book'", (), f"{order_id}-stock", "stock db"
    )
    if crash:
        log("coordinator", "оба ответили «да» — координатор падает, решение не разослано")
        await orders.close()
        await stock.close()
        return
    log("coordinator", "оба ответили «да» → решение COMMIT")
    await orders.execute(f"COMMIT PREPARED '{order_id}-orders'")
    await stock.execute(f"COMMIT PREPARED '{order_id}-stock'")
    log("coordinator", "COMMIT PREPARED на обоих участниках")
    await orders.close()
    await stock.close()


async def try_update(who: str) -> None:
    conn = await connect("stock")
    await conn.execute("SET lock_timeout = '2s'")
    log(who, "UPDATE products SET available = available - 1 WHERE id = 'book' ...")
    try:
        await conn.execute("UPDATE products SET available = available - 1 WHERE id = 'book'")
        log(who, "обновил")
    except asyncpg.LockNotAvailableError:
        log(who, "ждал 2 с и сдался: строка заблокирована подготовленной транзакцией")
    await conn.close()


async def main() -> None:
    await reset()

    title("1. Двухфазный коммит: обе фазы прошли")
    await two_phase("o-2pc-1", crash=False)
    log("demo", f"книг на складе: {await book_available()}")

    title("2. Координатор упал между фазами")
    await two_phase("o-2pc-2", crash=True)
    log("demo", f"подготовленные транзакции: orders {await prepared('orders')}, stock {await prepared('stock')}")
    log("demo", f"книг на складе по-прежнему: {await book_available()}")
    await try_update("checkout")
    log("demo", "соединения координатора закрыты, но транзакции живы и держат блокировки")

    title("3. Администратор доводит транзакцию вручную")
    for database in ("orders", "stock"):
        conn = await connect(database)
        for gid in await prepared(database):
            await conn.execute(f"COMMIT PREPARED '{gid}'")
            log("admin", f"COMMIT PREPARED '{gid}'")
        await conn.close()
    await try_update("checkout")
    log("demo", f"книг на складе: {await book_available()}")


if __name__ == "__main__":
    asyncio.run(main())
