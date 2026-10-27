import asyncio

from common.config import PAYMENTS_URL, STOCK_URL
from common.db import connect
from common.log import log, title
from common.orders_api import place
from common.proc import Worker, wait_final
from common.schema import GOOD_CARD
from common.show import history, state
from common.stand import client, reset

QUEUE = """
SELECT s.id, s.data->>'resume_state' AS stuck_at, o.amount, s.data->>'card' AS card
  FROM sagas s JOIN orders o ON o.id = s.order_id
 WHERE s.state = 'NEEDS_ATTENTION'
"""


async def phones(http) -> int:
    return (await http.get(f"{STOCK_URL}/products/phone")).json()["available"]


async def main() -> None:
    async with client() as http:
        await reset()
        title("1. Брошенный резерв: участник убирает за собой сам")
        await http.post(
            f"{STOCK_URL}/reservations",
            json={"saga_id": "s-lost", "product_id": "phone", "qty": 2, "ttl_seconds": 1.5},
            headers={"Idempotency-Key": "s-lost:reserve"},
        )
        log("demo", f"резерв без продолжения, телефонов доступно: {await phones(http)}")
        await asyncio.sleep(2.2)
        log("demo", f"через 2 с телефонов доступно: {await phones(http)}")

        title("2. Резерв истёк раньше поворотного шага")
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 2.0, "delay_calls": 1})
        worker = await Worker(reserve_ttl=1, http_timeout=3).start()
        order_id, saga_id = await place(http, "phone", 1, GOOD_CARD)
        await wait_final(saga_id)
        await worker.stop()
        await state(saga_id, "phone")
        await history(saga_id)

        title("3. Сбой после поворотного шага: только вперёд")
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"fail_capture": True})
        worker = await Worker(max_retries_after_pivot=3).start()
        order_id, saga_id = await place(http, "book", 1, GOOD_CARD)
        await wait_final(saga_id)
        orders = await connect("orders")
        for row in await orders.fetch(QUEUE):
            log("operator", f"очередь разбора: {row['id']} застряла на {row['stuck_at']}, {row['amount']} ₽")
        await state(saga_id, "book")

        log("operator", "провайдер починился — возвращаю сагу в работу")
        await http.post(f"{PAYMENTS_URL}/admin/config")
        async with orders.transaction():
            await orders.execute(
                """
                UPDATE sagas SET state = data->>'resume_state', attempts = 0, next_run_at = now(), version = version + 1
                 WHERE id = $1 AND state = 'NEEDS_ATTENTION'
                """,
                saga_id,
            )
            await orders.execute("INSERT INTO saga_log (saga_id, event) VALUES ($1, 'оператор вернул сагу в работу')", saga_id)
        await orders.close()
        await wait_final(saga_id)
        await worker.stop()
        await state(saga_id, "book")
        await history(saga_id)


if __name__ == "__main__":
    asyncio.run(main())
