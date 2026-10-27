import asyncio
import random

import asyncpg

from common.config import service_dsn

SEED_ROWS = 2000
PHASE_SECONDS = 1.5
WORKERS_PER_VERSION = 3
BATCH = 500

VERSIONS = {
    "v1": {"writes": ["total"], "reads": "total"},
    "v2": {"writes": ["total", "total_kopecks"], "reads": "total"},
    "v3": {"writes": ["total", "total_kopecks"], "reads": "total_kopecks"},
    "v4": {"writes": ["total_kopecks"], "reads": "total_kopecks"},
}


async def reset(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS mig_orders")
        await conn.execute("CREATE TABLE mig_orders (id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY, total bigint NOT NULL)")
        await conn.execute(f"INSERT INTO mig_orders (total) SELECT 100 FROM generate_series(1, {SEED_ROWS})")


async def worker(pool: asyncpg.Pool, version: str, stop: asyncio.Event, stats: dict) -> None:
    spec = VERSIONS[version]
    columns = ", ".join(spec["writes"])
    values = ", ".join(f"${i + 1}" for i in range(len(spec["writes"])))
    insert = f"INSERT INTO mig_orders ({columns}) VALUES ({values})"
    select = f"SELECT {spec['reads']} FROM mig_orders WHERE id = $1"
    while not stop.is_set():
        try:
            async with pool.acquire() as conn:
                await conn.execute(insert, *[100] * len(spec["writes"]))
                value = await conn.fetchval(select, random.randint(1, SEED_ROWS))
            stats[version]["ok"] += 1
            if value is None:
                stats[version]["null"] += 1
        except asyncpg.PostgresError as error:
            stats[version]["errors"] += 1
            stats[version]["last_error"] = str(error).splitlines()[0]
        await asyncio.sleep(0.01)


async def backfill(pool: asyncpg.Pool) -> str:
    updated = 0
    async with pool.acquire() as conn:
        while True:
            result = await conn.execute(f"""
                UPDATE mig_orders SET total_kopecks = total
                WHERE id IN (SELECT id FROM mig_orders WHERE total_kopecks IS NULL LIMIT {BATCH})
            """)
            count = int(result.split()[-1])
            if count == 0:
                return f"перенесено {updated} строк порциями по {BATCH}"
            updated += count


async def phase(pool: asyncpg.Pool, title: str, versions: list[str], migration) -> None:
    stats = {v: {"ok": 0, "errors": 0, "null": 0, "last_error": ""} for v in versions}
    stop = asyncio.Event()
    tasks = [asyncio.create_task(worker(pool, v, stop, stats)) for v in versions for _ in range(WORKERS_PER_VERSION)]
    await asyncio.sleep(PHASE_SECONDS / 3)
    if isinstance(migration, str):
        async with pool.acquire() as conn:
            await conn.execute(migration)
        description = migration
    elif migration is None:
        description = "—"
    else:
        description = await migration(pool)
    await asyncio.sleep(PHASE_SECONDS * 2 / 3)
    stop.set()
    await asyncio.gather(*tasks)
    print(f"{title}")
    print(f"   миграция: {description}")
    for version in versions:
        s = stats[version]
        line = f"   {version}: операций {s['ok']:>4}, ошибок {s['errors']:>4}, прочитано NULL {s['null']:>3}"
        if s["last_error"]:
            line += f"  ← {s['last_error']}"
        print(line)


async def main() -> None:
    pool = await asyncpg.create_pool(service_dsn("orders"), min_size=10, max_size=20)

    print("=== Наивно: переименование колонки во время работы v1 ===\n")
    await reset(pool)
    await phase(pool, "Работает v1, выкатываем RENAME", ["v1"], "ALTER TABLE mig_orders RENAME COLUMN total TO total_kopecks")

    print("\n=== Expand and contract ===\n")
    await reset(pool)
    await phase(pool, "1. Расширение (работает v1)", ["v1"], "ALTER TABLE mig_orders ADD COLUMN total_kopecks bigint")
    await phase(pool, "2. Выкатка v2: пишет в обе (v1 и v2 одновременно)", ["v1", "v2"], None)
    await phase(pool, "3. Перенос данных (работает только v2)", ["v2"], backfill)
    await phase(pool, "4. Выкатка v3: читает новую, пишет в обе (v2 и v3)", ["v2", "v3"], None)
    await phase(pool, "5. Снимаем NOT NULL со старой (работает только v3)", ["v3"], "ALTER TABLE mig_orders ALTER COLUMN total DROP NOT NULL")
    await phase(pool, "6. Выкатка v4: только новая колонка (v3 и v4)", ["v3", "v4"], None)
    await phase(
        pool,
        "7. Сужение (работает только v4)",
        ["v4"],
        "ALTER TABLE mig_orders DROP COLUMN total, ALTER COLUMN total_kopecks SET NOT NULL",
    )

    print("\n=== Шаги в неправильном порядке ===\n")
    await reset(pool)
    await phase(pool, "Расширение (работает v1)", ["v1"], "ALTER TABLE mig_orders ADD COLUMN total_kopecks bigint")
    await phase(pool, "v3 выкатили до переноса данных (v1 и v3)", ["v1", "v3"], None)
    await phase(pool, "v4 выкатили, не сняв NOT NULL со старой (v3 и v4)", ["v3", "v4"], None)

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
