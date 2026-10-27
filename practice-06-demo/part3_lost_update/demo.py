import asyncio
import random
import time

import asyncpg

from common.config import service_dsn

STOCK = 10
BUYERS = 50
THINK_TIME = 0.005


async def reset(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS sales")
        await conn.execute("DROP TABLE IF EXISTS stock")
        await conn.execute("""
            CREATE TABLE stock (
                product_id int PRIMARY KEY,
                quantity   int NOT NULL CHECK (quantity >= 0),
                version    int NOT NULL DEFAULT 0
            )
        """)
        await conn.execute("CREATE TABLE sales (id serial PRIMARY KEY, product_id int, buyer int)")
        await conn.execute("INSERT INTO stock (product_id, quantity) VALUES (1, $1)", STOCK)


async def naive(conn: asyncpg.Connection, buyer: int, stats: dict) -> bool:
    async with conn.transaction():
        quantity = await conn.fetchval("SELECT quantity FROM stock WHERE product_id = 1")
        if quantity < 1:
            return False
        await asyncio.sleep(THINK_TIME)
        await conn.execute("UPDATE stock SET quantity = $1 WHERE product_id = 1", quantity - 1)
        await conn.execute("INSERT INTO sales (product_id, buyer) VALUES (1, $1)", buyer)
        return True


async def conditional_update(conn: asyncpg.Connection, buyer: int, stats: dict) -> bool:
    async with conn.transaction():
        await asyncio.sleep(THINK_TIME)
        row = await conn.fetchrow(
            "UPDATE stock SET quantity = quantity - 1 WHERE product_id = 1 AND quantity >= 1 RETURNING quantity"
        )
        if row is None:
            return False
        await conn.execute("INSERT INTO sales (product_id, buyer) VALUES (1, $1)", buyer)
        return True


async def select_for_update(conn: asyncpg.Connection, buyer: int, stats: dict) -> bool:
    async with conn.transaction():
        quantity = await conn.fetchval("SELECT quantity FROM stock WHERE product_id = 1 FOR UPDATE")
        if quantity < 1:
            return False
        await asyncio.sleep(THINK_TIME)
        await conn.execute("UPDATE stock SET quantity = $1 WHERE product_id = 1", quantity - 1)
        await conn.execute("INSERT INTO sales (product_id, buyer) VALUES (1, $1)", buyer)
        return True


async def optimistic(conn: asyncpg.Connection, buyer: int, stats: dict) -> bool:
    while True:
        async with conn.transaction():
            quantity, version = await conn.fetchrow("SELECT quantity, version FROM stock WHERE product_id = 1")
            if quantity < 1:
                return False
            await asyncio.sleep(THINK_TIME)
            result = await conn.execute(
                "UPDATE stock SET quantity = $1, version = version + 1 WHERE product_id = 1 AND version = $2",
                quantity - 1, version,
            )
            if result == "UPDATE 1":
                await conn.execute("INSERT INTO sales (product_id, buyer) VALUES (1, $1)", buyer)
                return True
        stats["retries"] += 1
        await asyncio.sleep(random.uniform(0, THINK_TIME))


async def serializable(conn: asyncpg.Connection, buyer: int, stats: dict) -> bool:
    while True:
        try:
            async with conn.transaction(isolation="serializable"):
                quantity = await conn.fetchval("SELECT quantity FROM stock WHERE product_id = 1")
                if quantity < 1:
                    return False
                await asyncio.sleep(THINK_TIME)
                await conn.execute("UPDATE stock SET quantity = $1 WHERE product_id = 1", quantity - 1)
                await conn.execute("INSERT INTO sales (product_id, buyer) VALUES (1, $1)", buyer)
                return True
        except asyncpg.SerializationError:
            stats["retries"] += 1
            await asyncio.sleep(random.uniform(0, THINK_TIME))


STRATEGIES = [
    ("прочитать-проверить-записать", naive),
    ("условный UPDATE", conditional_update),
    ("SELECT … FOR UPDATE", select_for_update),
    ("оптимистическая (version)", optimistic),
    ("SERIALIZABLE + повтор", serializable),
]


async def run(pool: asyncpg.Pool, strategy) -> tuple[int, int, int, int, float]:
    await reset(pool)
    stats = {"retries": 0}

    async def buyer(number: int) -> bool:
        async with pool.acquire() as conn:
            return await strategy(conn, number, stats)

    started = time.perf_counter()
    results = await asyncio.gather(*(buyer(n) for n in range(BUYERS)))
    elapsed = time.perf_counter() - started
    async with pool.acquire() as conn:
        quantity = await conn.fetchval("SELECT quantity FROM stock WHERE product_id = 1")
        sold = await conn.fetchval("SELECT count(*) FROM sales")
    return sum(results), sold, quantity, stats["retries"], elapsed


async def main() -> None:
    print(f"На складе {STOCK} штук, одновременно покупают {BUYERS} человек\n")
    print(f"{'способ':<30} {'продано':>8} {'остаток':>8} {'повторов':>9} {'время':>8}")
    pool = await asyncpg.create_pool(service_dsn("catalog"), min_size=BUYERS, max_size=BUYERS)
    try:
        for name, strategy in STRATEGIES:
            _, sold, quantity, retries, elapsed = await run(pool, strategy)
            print(f"{name:<30} {sold:>8} {quantity:>8} {retries:>9} {elapsed:>6.2f} с")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
