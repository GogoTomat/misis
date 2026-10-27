import asyncpg

from common.config import dsn


async def connect(database: str) -> asyncpg.Connection:
    return await asyncpg.connect(dsn(database))


async def pool(database: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn(database), min_size=1, max_size=5)
