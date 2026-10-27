import asyncio
import uuid

import httpx

PAYMENTS_URL = "http://127.0.0.1:8004"


async def show_account(client: httpx.AsyncClient) -> None:
    account = (await client.get("/account")).json()
    print(f"   Счёт: списаний {account['charges']}, всего {account['charged_total']} ₽")


async def charge(client: httpx.AsyncClient, timeout: float, key: str | None = None) -> None:
    headers = {"Idempotency-Key": key} if key else {}
    try:
        response = await client.post("/charge", params={"amount": 1000}, headers=headers, timeout=timeout)
        print(f"   Ответ {response.status_code}: {response.json()}")
    except httpx.TimeoutException:
        print(f"   Таймаут через {timeout} с. Списали или нет — неизвестно")


async def main() -> None:
    async with httpx.AsyncClient(base_url=PAYMENTS_URL) as client:
        await client.post("/admin/reset")
        await client.post("/admin/delay", params={"seconds": 2})

        print("Шаг 1. Списываем 1000 ₽, ждём не больше 1 секунды")
        await charge(client, timeout=1)
        await asyncio.sleep(1.5)
        await show_account(client)

        print("\nШаг 2. Повторяем тот же запрос без ключа идемпотентности")
        await charge(client, timeout=3)
        await show_account(client)

        await client.post("/admin/reset")
        key = str(uuid.uuid4())
        print(f"\nШаг 3. Тот же сценарий с Idempotency-Key {key[:8]}…")
        await charge(client, timeout=1, key=key)
        print("   Сразу повторяем:")
        await charge(client, timeout=3, key=key)
        await asyncio.sleep(1.5)
        print("   Повторяем после завершения:")
        await charge(client, timeout=3, key=key)
        await show_account(client)

        await client.post("/admin/delay", params={"seconds": 0})


if __name__ == "__main__":
    asyncio.run(main())
