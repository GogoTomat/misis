import asyncio
import time

import httpx

REPORTS_URL = "http://127.0.0.1:8005"
CLIENT_TIMEOUT = 3


async def main() -> None:
    async with httpx.AsyncClient(base_url=REPORTS_URL, timeout=CLIENT_TIMEOUT) as client:
        print(f"Шаг 1. Синхронный отчёт, клиент ждёт не больше {CLIENT_TIMEOUT} с")
        started = time.perf_counter()
        try:
            response = await client.post("/reports/sync")
            print(f"   {response.status_code}: {response.json()}")
        except httpx.TimeoutException:
            print(f"   Таймаут через {time.perf_counter() - started:.1f} с, а сервер продолжает строить отчёт")

        await asyncio.sleep(2.5)

        print("\nШаг 2. Асинхронный отчёт: 202 Accepted и опрос статуса")
        started = time.perf_counter()
        response = await client.post("/reports")
        body = response.json()
        print(f"   {response.status_code} через {time.perf_counter() - started:.3f} с: {body}")
        while True:
            await asyncio.sleep(1)
            status = (await client.get(body["status_url"])).json()
            print(f"   +{time.perf_counter() - started:4.1f} с  статус: {status['status']}")
            if status["status"] == "done":
                print(f"   Результат: {status['result_url']}")
                break


if __name__ == "__main__":
    asyncio.run(main())
