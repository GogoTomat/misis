import asyncio
import uuid

from common.config import ORDERS_URL
from common.log import log, title
from common.orders_api import place
from common.proc import Worker, wait_final
from common.schema import BAD_CARD, GOOD_CARD
from common.show import history, state
from common.stand import client, reset


async def watch(http, order_id: str) -> None:
    seen = None
    for _ in range(100):
        body = (await http.get(f"{ORDERS_URL}/orders/{order_id}")).json()
        current = (body["status"], body["saga_state"])
        if current != seen:
            log("client", f"GET /orders/{order_id} → status {body['status']}, сага {body['saga_state']}")
            seen = current
        if body["status"] != "PENDING":
            return
        await asyncio.sleep(0.05)


async def main() -> None:
    await reset()
    worker = await Worker().start()
    async with client() as http:
        title("1. Успешная сага: 202 Accepted и опрос статуса")
        key = uuid.uuid4().hex
        response = await http.post(
            f"{ORDERS_URL}/orders",
            json={"customer": "anna", "product_id": "book", "qty": 2, "card": GOOD_CARD},
            headers={"Idempotency-Key": key},
        )
        order_id = response.json()["order_id"]
        log("client", f"POST /orders → {response.status_code}, Location: {response.headers['location']}")
        await watch(http, order_id)
        saga_id = "s-" + order_id[2:]
        await state(saga_id, "book")
        await history(saga_id)

        title("2. Тот же запрос повторно — с тем же Idempotency-Key")
        again = await http.post(
            f"{ORDERS_URL}/orders",
            json={"customer": "anna", "product_id": "book", "qty": 2, "card": GOOD_CARD},
            headers={"Idempotency-Key": key},
        )
        log("client", f"POST /orders → {again.status_code}, order_id {again.json()['order_id']}")

        title("3. Банк отклонил оплату — компенсация")
        order_id, saga_id = await place(http, "book", 2, BAD_CARD)
        await wait_final(saga_id)
        await state(saga_id, "book")
        await history(saga_id)

        title("4. Товара не хватает — отказ на первом шаге")
        order_id, saga_id = await place(http, "lamp", 3, GOOD_CARD)
        await wait_final(saga_id)
        await state(saga_id, "lamp")
        await history(saga_id)
    await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
