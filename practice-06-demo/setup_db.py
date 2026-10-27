import asyncio

from common.config import SERVICES
from common.db import connect_admin, connect_service

ORDERS_ROWS = 1_000_000


async def recreate_databases() -> None:
    conn = await connect_admin()
    try:
        for service in SERVICES:
            await conn.execute(f"DROP DATABASE IF EXISTS {service} WITH (FORCE)")
        for role in [f"{s}_svc" for s in SERVICES] + ["reports_svc"]:
            await conn.execute(f"DROP ROLE IF EXISTS {role}")
            await conn.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{role}'")
        for service in SERVICES:
            await conn.execute(f"CREATE DATABASE {service} OWNER {service}_svc")
            await conn.execute(f"REVOKE CONNECT ON DATABASE {service} FROM PUBLIC")
            await conn.execute(f"GRANT CONNECT ON DATABASE {service} TO {service}_svc")
            print(f"База {service}: владелец {service}_svc, остальным подключение запрещено")
    finally:
        await conn.close()


async def seed_orders() -> None:
    conn = await connect_service("orders")
    try:
        await conn.execute("""
            CREATE TABLE orders (
                id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                customer_id   int         NOT NULL,
                status        text        NOT NULL,
                total_kopecks bigint      NOT NULL,
                created_at    timestamptz NOT NULL
            )
        """)
        await conn.execute(f"""
            INSERT INTO orders (customer_id, status, total_kopecks, created_at)
            SELECT (random() * 99999)::int + 1,
                   CASE WHEN r < 0.01 THEN 'pending'
                        WHEN r < 0.90 THEN 'delivered'
                        ELSE 'cancelled' END,
                   (random() * 1000000)::bigint + 100,
                   now() - random() * interval '365 days'
            FROM (SELECT random() AS r FROM generate_series(1, {ORDERS_ROWS})) AS s
        """)
        await conn.execute("VACUUM ANALYZE orders")
        count = await conn.fetchval("SELECT count(*) FROM orders")
        print(f"Таблица orders: {count} строк")
    finally:
        await conn.close()


async def main() -> None:
    await recreate_databases()
    await seed_orders()
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
