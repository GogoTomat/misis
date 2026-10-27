import asyncio

from common.config import PAYMENTS_URL, STOCK_URL
from common.db import connect
from common.log import log, title
from common.orders_api import place
from common.proc import Worker, wait_final
from common.schema import GOOD_CARD
from common.show import history, state
from common.stand import client, reset


async def crash_and_recover(http, product_id: str) -> None:
    order_id, saga_id = await place(http, product_id, 2, GOOD_CARD)
    first = await Worker("worker-1", crash_after="reserve").start()
    log("demo", f"worker-1 завершился с кодом {await first.wait()}")
    await state(saga_id, product_id)
    second = await Worker("worker-2").start()
    log("demo", "worker-2 запущен; сага заблокирована арендой worker-1 ещё на несколько секунд")
    await wait_final(saga_id)
    await second.stop()
    await state(saga_id, product_id)
    await history(saga_id)


async def main() -> None:
    async with client() as http:
        await reset()
        title("1. Оркестратор упал после ответа склада — и перезапустился")
        await crash_and_recover(http, "book")

        title("2. То же самое, но склад без идемпотентности")
        await http.post(f"{STOCK_URL}/admin/config", params={"idempotency": False})
        await crash_and_recover(http, "phone")
        await http.post(f"{STOCK_URL}/admin/config", params={"idempotency": True})

        title("3. Два оркестратора, восемь заказов")
        await reset()
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 0.3, "delay_calls": 8})
        sagas = [(await place(http, "book", 1, GOOD_CARD))[1] for _ in range(8)]
        workers = await asyncio.gather(Worker("worker-A").start(), Worker("worker-B").start())
        for saga_id in sagas:
            await wait_final(saga_id)
        for worker in workers:
            await worker.stop()
        orders, payments = await connect("orders"), await connect("payments")
        done = await orders.fetchval("SELECT count(*) FROM sagas WHERE state = 'CONFIRMED'")
        paid = await payments.fetchval("SELECT count(*) FROM payments WHERE status = 'CAPTURED'")
        await orders.close()
        await payments.close()
        log("demo", f"подтверждено саг: {done} из {len(sagas)}, списаний: {paid}")

if __name__ == "__main__":
    asyncio.run(main())
