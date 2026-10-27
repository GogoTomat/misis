import asyncio
import random
import time

import httpx

USERS_URL = "http://127.0.0.1:8001"
ORDERS_COUNT = 100
CONCURRENCY_LIMIT = 10


def load_recent_orders() -> list[dict]:
    random.seed(5)
    return [{"order_id": i, "user_id": random.randint(1, 30)} for i in range(1, ORDERS_COUNT + 1)]


async def sequential(client: httpx.AsyncClient, orders: list[dict]) -> dict:
    users = {}
    for order in orders:
        users[order["user_id"]] = (await client.get(f"/users/{order['user_id']}")).json()
    return users


async def parallel(client: httpx.AsyncClient, orders: list[dict]) -> dict:
    responses = await asyncio.gather(*(client.get(f"/users/{o['user_id']}") for o in orders))
    return {r.json()["id"]: r.json() for r in responses}


async def parallel_limited(client: httpx.AsyncClient, orders: list[dict]) -> dict:
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def fetch(user_id: int) -> dict:
        async with semaphore:
            return (await client.get(f"/users/{user_id}")).json()

    users = await asyncio.gather(*(fetch(o["user_id"]) for o in orders))
    return {u["id"]: u for u in users}


async def batch(client: httpx.AsyncClient, orders: list[dict]) -> dict:
    ids = {o["user_id"] for o in orders}
    response = await client.get("/users", params={"ids": ",".join(map(str, sorted(ids)))})
    return {u["id"]: u for u in response.json()}


STRATEGIES = [
    ("последовательно", sequential),
    ("gather без лимита", parallel),
    (f"gather, лимит {CONCURRENCY_LIMIT}", parallel_limited),
    ("пакетный эндпоинт", batch),
]


async def main() -> None:
    orders = load_recent_orders()
    distinct = len({o["user_id"] for o in orders})
    print(f"{len(orders)} заказов, {distinct} разных покупателей, задержка users — 20 мс\n")
    print(f"{'способ':<20} {'время':>8} {'запросов':>9} {'одновременно':>13}")
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    async with httpx.AsyncClient(base_url=USERS_URL, limits=limits, timeout=10) as client:
        for name, strategy in STRATEGIES:
            await client.post("/admin/reset")
            started = time.perf_counter()
            users = await strategy(client, orders)
            elapsed = time.perf_counter() - started
            stats = (await client.get("/admin/stats")).json()
            assert len(users) == distinct
            requests = stats["single"] + stats["batch"]
            print(f"{name:<20} {elapsed:>6.2f} с {requests:>9} {stats['max_in_flight']:>13}")


if __name__ == "__main__":
    asyncio.run(main())
