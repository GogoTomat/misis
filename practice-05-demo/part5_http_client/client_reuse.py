import asyncio
import time

import httpx

USERS_URL = "http://127.0.0.1:8001"
CALLS = 300


async def client_per_call() -> float:
    started = time.perf_counter()
    for _ in range(CALLS):
        async with httpx.AsyncClient(base_url=USERS_URL) as client:
            await client.get("/ping")
    return time.perf_counter() - started


async def shared_client() -> float:
    client = httpx.AsyncClient(
        base_url=USERS_URL,
        timeout=httpx.Timeout(2.0, connect=0.5),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    try:
        started = time.perf_counter()
        for _ in range(CALLS):
            await client.get("/ping")
        return time.perf_counter() - started
    finally:
        await client.aclose()


async def main() -> None:
    fresh = await client_per_call()
    shared = await shared_client()
    print(f"{CALLS} вызовов /ping")
    print(f"Новый клиент на каждый вызов: {fresh:.2f} с ({fresh / CALLS * 1000:.2f} мс на вызов)")
    print(f"Один клиент на процесс:       {shared:.2f} с ({shared / CALLS * 1000:.2f} мс на вызов)")
    print(f"Разница: в {fresh / shared:.1f} раза")


if __name__ == "__main__":
    asyncio.run(main())
