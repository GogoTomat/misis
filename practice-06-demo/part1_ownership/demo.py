import asyncio

import asyncpg

from common.config import dsn
from common.db import connect_service

REPORT_FROM_TABLE = "SELECT count(*), sum(total) FROM legacy_orders"
REPORT_FROM_VIEW = "SELECT count(*), sum(total) FROM orders_public.order_summary"


async def try_report(title: str, conn: asyncpg.Connection, sql: str) -> None:
    try:
        count, total = await conn.fetchrow(sql)
        print(f"   {title}: заказов {count}, сумма {total}")
    except asyncpg.PostgresError as error:
        print(f"   {title}: {type(error).__name__} — {str(error).splitlines()[0]}")


async def reset_legacy(orders: asyncpg.Connection) -> None:
    await orders.execute("DROP SCHEMA IF EXISTS orders_public CASCADE")
    await orders.execute("DROP TABLE IF EXISTS legacy_orders")
    await orders.execute("CREATE TABLE legacy_orders (id int PRIMARY KEY, total int NOT NULL)")
    await orders.execute("INSERT INTO legacy_orders VALUES (1, 1200), (2, 3400), (3, 990)")


async def main() -> None:
    print("Шаг 1. Каждый сервис ходит в свою базу своим пользователем")
    orders = await connect_service("orders")
    count = await orders.fetchval("SELECT count(*) FROM orders")
    print(f"   orders_svc → база orders: {count} заказов")
    try:
        await connect_service("orders", "catalog")
    except asyncpg.PostgresError as error:
        print(f"   orders_svc → база catalog: {type(error).__name__} — {str(error).splitlines()[0]}")

    print("\nШаг 2. Общая база: отчёты читают таблицу заказов напрямую")
    await reset_legacy(orders)
    await try_report("reports до миграции", orders, REPORT_FROM_TABLE)
    await orders.execute("ALTER TABLE legacy_orders RENAME COLUMN total TO total_kopecks")
    print("   orders: ALTER TABLE legacy_orders RENAME COLUMN total TO total_kopecks")
    await try_report("reports после миграции", orders, REPORT_FROM_TABLE)

    print("\nШаг 3. Контракт: отчёты получают представление, а не таблицу")
    await reset_legacy(orders)
    await orders.execute("CREATE SCHEMA orders_public")
    await orders.execute("CREATE VIEW orders_public.order_summary AS SELECT id, total FROM legacy_orders")
    await orders.execute("GRANT CONNECT ON DATABASE orders TO reports_svc")
    await orders.execute("GRANT USAGE ON SCHEMA orders_public TO reports_svc")
    await orders.execute("GRANT SELECT ON orders_public.order_summary TO reports_svc")
    reports = await asyncpg.connect(dsn("reports_svc", "reports_svc", "orders"))
    await try_report("reports → таблица", reports, REPORT_FROM_TABLE)
    await try_report("reports → представление", reports, REPORT_FROM_VIEW)
    await orders.execute("ALTER TABLE legacy_orders RENAME COLUMN total TO total_kopecks")
    print("   orders: ALTER TABLE legacy_orders RENAME COLUMN total TO total_kopecks")
    await try_report("reports → представление", reports, REPORT_FROM_VIEW)
    definition = await orders.fetchval("SELECT pg_get_viewdef('orders_public.order_summary'::regclass, true)")
    print("   Определение представления теперь:")
    for line in definition.strip().splitlines():
        print(f"      {line}")

    await reports.close()
    await orders.close()


if __name__ == "__main__":
    asyncio.run(main())
