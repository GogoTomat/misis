import asyncio
import time

import asyncpg

from common.db import connect_service, explain

CUSTOMER = 4242
BY_CUSTOMER = "SELECT * FROM orders WHERE customer_id = $1"
BY_CUSTOMER_LAST_MONTH = """
    SELECT * FROM orders
    WHERE customer_id = $1 AND created_at > now() - interval '30 days'
    ORDER BY created_at DESC
"""
BY_DAY = "SELECT count(*) FROM orders WHERE created_at > now() - interval '1 day'"
PENDING = "SELECT id FROM orders WHERE status = 'pending' ORDER BY created_at LIMIT 100"
DELIVERED_SUM = "SELECT sum(total_kopecks) FROM orders WHERE status = 'delivered'"
PENDING_SUM = "SELECT sum(total_kopecks) FROM orders WHERE status = 'pending'"
COVERING = "SELECT status, total_kopecks FROM orders WHERE customer_id = $1"
INSERT_ROWS = 100_000


async def show(conn: asyncpg.Connection, title: str, sql: str, *args) -> None:
    plan, ms = await explain(conn, sql, *args)
    print(f"   {title:<34} {ms:>9.2f} мс   {plan}")


async def drop_indexes(conn: asyncpg.Connection) -> None:
    names = await conn.fetch("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'orders' AND indexname <> 'orders_pkey'
    """)
    for row in names:
        await conn.execute(f"DROP INDEX {row['indexname']}")


async def index_size(conn: asyncpg.Connection, name: str) -> str:
    return await conn.fetchval("SELECT pg_size_pretty(pg_relation_size($1::regclass))", name)


async def insert_batch(conn: asyncpg.Connection, table: str) -> float:
    started = time.perf_counter()
    await conn.execute(f"""
        INSERT INTO {table} (customer_id, status, total_kopecks, created_at)
        SELECT (random() * 99999)::int + 1, 'pending', 1000, now()
        FROM generate_series(1, {INSERT_ROWS})
    """)
    return time.perf_counter() - started


async def main() -> None:
    conn = await connect_service("orders")
    await drop_indexes(conn)
    await conn.execute("ANALYZE orders")

    print("Шаг 1. Поиск заказов покупателя")
    await show(conn, "без индекса", BY_CUSTOMER, CUSTOMER)
    await conn.execute("CREATE INDEX orders_customer_idx ON orders (customer_id)")
    await show(conn, "индекс (customer_id)", BY_CUSTOMER, CUSTOMER)

    print("\nШаг 2. Составной индекс и правило левого префикса")
    await conn.execute("DROP INDEX orders_customer_idx")
    await conn.execute("CREATE INDEX orders_customer_created_idx ON orders (customer_id, created_at)")
    await show(conn, "покупатель за месяц", BY_CUSTOMER_LAST_MONTH, CUSTOMER)
    await show(conn, "только покупатель", BY_CUSTOMER, CUSTOMER)
    await show(conn, "только дата", BY_DAY)

    print("\nШаг 3. Частичный индекс")
    await conn.execute("CREATE INDEX orders_status_created_idx ON orders (status, created_at)")
    await show(conn, "полный (status, created_at)", PENDING)
    print(f"   размер полного индекса:      {await index_size(conn, 'orders_status_created_idx')}")
    await conn.execute("DROP INDEX orders_status_created_idx")
    await conn.execute("CREATE INDEX orders_pending_idx ON orders (created_at) WHERE status = 'pending'")
    await conn.execute("ANALYZE orders")
    await show(conn, "частичный WHERE status='pending'", PENDING)
    print(f"   размер частичного индекса:   {await index_size(conn, 'orders_pending_idx')}")

    print("\nШаг 4. Индекс по колонке с малым числом значений")
    await conn.execute("DROP INDEX orders_pending_idx")
    await conn.execute("CREATE INDEX orders_status_idx ON orders (status)")
    await conn.execute("ANALYZE orders")
    shares = await conn.fetch("SELECT status, round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct FROM orders GROUP BY status ORDER BY pct DESC")
    print("   распределение: " + ", ".join(f"{r['status']} {r['pct']}%" for r in shares))
    await show(conn, "status = 'delivered'", DELIVERED_SUM)
    await show(conn, "status = 'pending'", PENDING_SUM)

    print("\nШаг 5. Покрывающий индекс")
    await show(conn, "составной (customer_id, created_at)", COVERING, CUSTOMER)
    await conn.execute("CREATE INDEX orders_customer_cover_idx ON orders (customer_id) INCLUDE (status, total_kopecks)")
    await conn.execute("VACUUM ANALYZE orders")
    await show(conn, "INCLUDE (status, total_kopecks)", COVERING, CUSTOMER)

    print(f"\nШаг 6. Цена индексов при записи ({INSERT_ROWS} строк)")
    await conn.execute("DROP TABLE IF EXISTS orders_write_test")
    await conn.execute("CREATE TABLE orders_write_test (LIKE orders INCLUDING DEFAULTS INCLUDING IDENTITY)")
    await conn.execute("ALTER TABLE orders_write_test ADD PRIMARY KEY (id)")
    plain = await insert_batch(conn, "orders_write_test")
    for columns in ["customer_id", "status", "created_at", "customer_id, created_at", "status, created_at", "total_kopecks"]:
        await conn.execute(f"CREATE INDEX ON orders_write_test ({columns})")
    await conn.execute("TRUNCATE orders_write_test")
    indexed = await insert_batch(conn, "orders_write_test")
    print(f"   только первичный ключ:       {plain:.2f} с")
    print(f"   первичный ключ + 6 индексов: {indexed:.2f} с  (в {indexed / plain:.1f} раза медленнее)")
    await conn.execute("DROP TABLE orders_write_test")

    await drop_indexes(conn)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
