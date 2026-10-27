import asyncio

import asyncpg

from common.config import service_dsn

ATTEMPTS = 20
THINK_TIME = 0.01


async def reset(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS customers")
        await conn.execute("""
            CREATE TABLE customers (
                id    int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                email text NOT NULL,
                name  text NOT NULL
            )
        """)


async def register_check_then_insert(conn: asyncpg.Connection, email: str) -> int:
    exists = await conn.fetchval("SELECT count(*) FROM customers WHERE email = $1", email)
    if exists:
        return 409
    await asyncio.sleep(THINK_TIME)
    await conn.execute("INSERT INTO customers (email, name) VALUES ($1, 'Анна')", email)
    return 201


async def register_with_constraint(conn: asyncpg.Connection, email: str) -> int:
    try:
        await conn.execute("INSERT INTO customers (email, name) VALUES ($1, 'Анна')", email)
        return 201
    except asyncpg.UniqueViolationError:
        return 409


async def storm(pool: asyncpg.Pool, handler, emails: list[str]) -> dict[int, int]:
    async def one(email: str) -> int:
        async with pool.acquire() as conn:
            return await handler(conn, email)

    codes = await asyncio.gather(*(one(e) for e in emails))
    return {code: codes.count(code) for code in sorted(set(codes))}


async def rows(pool: asyncpg.Pool) -> list[str]:
    async with pool.acquire() as conn:
        return [r["email"] for r in await conn.fetch("SELECT email FROM customers ORDER BY id")]


async def main() -> None:
    pool = await asyncpg.create_pool(service_dsn("users"), min_size=ATTEMPTS, max_size=ATTEMPTS)
    same = ["anna@example.com"] * ATTEMPTS

    print(f"Шаг 1. {ATTEMPTS} одновременных регистраций, проверка в коде: SELECT, затем INSERT")
    await reset(pool)
    codes = await storm(pool, register_check_then_insert, same)
    print(f"   ответы: {codes}")
    print(f"   строк с anna@example.com в базе: {len(await rows(pool))}")

    print("\nШаг 2. Уникальный индекс и обработка UniqueViolationError")
    await reset(pool)
    async with pool.acquire() as conn:
        await conn.execute("CREATE UNIQUE INDEX customers_email_key ON customers (email)")
    codes = await storm(pool, register_with_constraint, same)
    print(f"   ответы: {codes}")
    print(f"   строк в базе: {len(await rows(pool))}")

    print("\nШаг 3. Тот же индекс и разный регистр")
    await reset(pool)
    async with pool.acquire() as conn:
        await conn.execute("CREATE UNIQUE INDEX customers_email_key ON customers (email)")
    codes = await storm(pool, register_with_constraint, ["anna@example.com", "Anna@Example.com"])
    print(f"   индекс (email): ответы {codes}, в базе {await rows(pool)}")
    await reset(pool)
    async with pool.acquire() as conn:
        await conn.execute("CREATE UNIQUE INDEX customers_email_lower_key ON customers (lower(email))")
    codes = await storm(pool, register_with_constraint, ["anna@example.com", "Anna@Example.com"])
    print(f"   индекс (lower(email)): ответы {codes}, в базе {await rows(pool)}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
