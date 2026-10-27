import asyncio

from common.db import connect
from common.log import log
from common.schema import DATABASES, DDL


async def main() -> None:
    admin = await connect("postgres")
    for name in DATABASES:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1", name
        )
        for gid in await admin.fetch("SELECT gid FROM pg_prepared_xacts WHERE database = $1", name):
            log("setup", f"в базе {name} висит подготовленная транзакция {gid['gid']}, откатываю")
            other = await connect(name)
            await other.execute(f"ROLLBACK PREPARED '{gid['gid']}'")
            await other.close()
        await admin.execute(f"DROP DATABASE IF EXISTS {name}")
        await admin.execute(f"CREATE DATABASE {name}")
    prepared = await admin.fetchval("SHOW max_prepared_transactions")
    await admin.close()
    for name in DATABASES:
        conn = await connect(name)
        await conn.execute(DDL[name])
        await conn.close()
        log("setup", f"база {name} создана")
    log("setup", f"max_prepared_transactions = {prepared}")
    if prepared == "0":
        log("setup", "часть 2 не заработает: запустите PostgreSQL из docker-compose.yml проекта")


if __name__ == "__main__":
    asyncio.run(main())
