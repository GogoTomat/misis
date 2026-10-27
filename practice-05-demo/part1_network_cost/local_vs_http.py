import asyncio
import time

import httpx

USERS_URL = "http://127.0.0.1:8001"
LOCAL_CALLS = 100_000
HTTP_CALLS = 200


def get_price(product_id: int) -> int:
    return 100 + product_id


def bench_local() -> float:
    started = time.perf_counter()
    for i in range(LOCAL_CALLS):
        get_price(i)
    return (time.perf_counter() - started) / LOCAL_CALLS


async def bench_http() -> float:
    async with httpx.AsyncClient(base_url=USERS_URL) as client:
        await client.get("/ping")
        started = time.perf_counter()
        for _ in range(HTTP_CALLS):
            await client.get("/ping")
        return (time.perf_counter() - started) / HTTP_CALLS


async def main() -> None:
    local = bench_local()
    http = await bench_http()
    ratio = http / local
    print(f"Вызов функции:        {local * 1e9:10.1f} нс")
    print(f"HTTP-вызов /ping:     {http * 1e6:10.1f} мкс")
    print(f"HTTP дороже в         {ratio:10.0f} раз")
    print()
    print(f"Если вызов функции длится 1 секунду, HTTP-вызов длится {ratio / 60:.0f} минут")


if __name__ == "__main__":
    asyncio.run(main())
