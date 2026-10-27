import asyncio
import time

import asyncpg

from common.config import REPLICA_PORT
from common.db import connect_service

POLL = 0.1


async def read_name(conn: asyncpg.Connection) -> str:
    return await conn.fetchval("SELECT name FROM profiles WHERE id = 1")


async def current_lsn(primary: asyncpg.Connection) -> str:
    return await primary.fetchval("SELECT pg_current_wal_lsn()::text")


async def wait_for_lsn(replica: asyncpg.Connection, lsn: str) -> None:
    while not await replica.fetchval("SELECT pg_last_wal_replay_lsn() >= $1::text::pg_lsn", lsn):
        await asyncio.sleep(POLL)


async def rename(primary: asyncpg.Connection, name: str) -> float:
    await primary.execute("UPDATE profiles SET name = $1 WHERE id = 1", name)
    return time.perf_counter()


async def main() -> None:
    primary = await connect_service("users")
    replica = await connect_service("users", port=REPLICA_PORT)

    await primary.execute("DROP TABLE IF EXISTS profiles")
    await primary.execute("CREATE TABLE profiles (id int PRIMARY KEY, name text NOT NULL)")
    await primary.execute("INSERT INTO profiles VALUES (1, 'Аня')")
    print("Подготовка: таблица profiles создана на лидере, ждём реплику...")
    started = time.perf_counter()
    await wait_for_lsn(replica, await current_lsn(primary))
    print(f"   реплика получила таблицу через {time.perf_counter() - started:.1f} с")
    print(f"   реплика в режиме восстановления: {await replica.fetchval('SELECT pg_is_in_recovery()')}")

    print("\nШаг 1. Запись в реплику")
    try:
        await replica.execute("UPDATE profiles SET name = 'Взлом' WHERE id = 1")
    except asyncpg.PostgresError as error:
        print(f"   {type(error).__name__} — {str(error).splitlines()[0]}")

    print("\nШаг 2. Записали на лидера, сразу читаем с реплики")
    written = await rename(primary, "Анна")
    print("   лидер: имя изменено на «Анна», ответ «сохранено»")
    print(f"   реплика сразу после записи: «{await read_name(replica)}»")
    while await read_name(replica) != "Анна":
        await asyncio.sleep(POLL)
    print(f"   реплика показала «Анна» через {time.perf_counter() - written:.2f} с")

    print("\nШаг 3. Read-your-writes: свои данные читаем с лидера")
    await rename(primary, "Анна Петровна")
    print(f"   лидер сразу после записи: «{await read_name(primary)}»")
    print(f"   реплика в тот же момент: «{await read_name(replica)}»")

    print("\nШаг 4. Read-your-writes: ждём, пока реплика дойдёт до позиции записи в WAL")
    written = await rename(primary, "Анна П.")
    lsn = await current_lsn(primary)
    print(f"   лидер: запись завершилась на позиции WAL {lsn}")
    await wait_for_lsn(replica, lsn)
    print(f"   реплика дошла до {lsn} через {time.perf_counter() - written:.2f} с")
    print(f"   читаем с реплики: «{await read_name(replica)}»")

    await primary.close()
    await replica.close()


if __name__ == "__main__":
    asyncio.run(main())
