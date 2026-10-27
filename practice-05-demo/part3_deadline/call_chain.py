import asyncio
import time

import httpx

ORDERS_URL = "http://127.0.0.1:8003"
STOCK_URL = "http://127.0.0.1:8002"
CLIENT_BUDGET = 1.0


async def set_stock_delay(seconds: float) -> None:
    async with httpx.AsyncClient(base_url=STOCK_URL) as client:
        await client.post("/admin/delay", params={"seconds": seconds})


async def call(client: httpx.AsyncClient, path: str, headers: dict, timeout: float) -> None:
    started = time.perf_counter()
    try:
        response = await client.post(path, headers=headers, timeout=timeout)
        print(f"   Ответ {response.status_code} через {time.perf_counter() - started:.2f} с: {response.json()}")
    except httpx.TimeoutException:
        print(f"   Клиент сдался через {time.perf_counter() - started:.2f} с")


async def main() -> None:
    async with httpx.AsyncClient(base_url=ORDERS_URL) as client:
        await set_stock_delay(3)

        print("Шаг 1. Склад медленный (3 с), клиент ждёт 1 с, дедлайн не передаётся")
        await call(client, "/orders/naive", {}, CLIENT_BUDGET)
        print("   Смотрите в окно сервисов: цепочка продолжает работать")
        await asyncio.sleep(3)

        print("\nШаг 2. Тот же склад, клиент передаёт дедлайн")
        deadline = time.time() + CLIENT_BUDGET
        await call(client, "/orders", {"X-Request-Deadline": str(deadline)}, CLIENT_BUDGET + 0.5)
        await asyncio.sleep(1)

        print("\nШаг 3. Дедлайн уже истёк к моменту запроса")
        deadline = time.time() - 0.1
        await call(client, "/orders", {"X-Request-Deadline": str(deadline)}, CLIENT_BUDGET)

        print("\nШаг 4. Склад быстрый (0,2 с), дедлайн передаётся")
        await set_stock_delay(0.2)
        deadline = time.time() + CLIENT_BUDGET
        await call(client, "/orders", {"X-Request-Deadline": str(deadline)}, CLIENT_BUDGET + 0.5)

        await set_stock_delay(0)


if __name__ == "__main__":
    asyncio.run(main())
