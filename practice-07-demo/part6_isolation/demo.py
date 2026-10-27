import asyncio

from common.config import ORDERS_URL, PAYMENTS_URL, STOCK_URL
from common.log import log, title
from common.orders_api import place
from common.proc import Worker, wait_final
from common.schema import BAD_CARD, GOOD_CARD
from common.show import history, state
from common.stand import client, reset


async def lamp(http) -> int:
    return (await http.get(f"{STOCK_URL}/products/lamp")).json()["available"]


async def cancel_during_saga(http, mode: str) -> None:
    await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 1.5, "delay_calls": 1})
    order_id, saga_id = await place(http, "lamp", 1, GOOD_CARD, customer="boris")
    await asyncio.sleep(0.6)
    response = await http.post(f"{ORDERS_URL}/orders/{order_id}/cancel", params={"mode": mode})
    log("boris", f"нажал «Отменить заказ» → {response.status_code} {response.json()}")
    await wait_final(saga_id)
    await state(saga_id, "lamp")
    await history(saga_id)


async def main() -> None:
    async with client() as http:
        await reset()
        title("1. Грязное чтение: последний экземпляр в резерве")
        worker = await Worker(http_timeout=3).start()
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 1.5, "delay_calls": 1})
        log("demo", f"ламп на складе: {await lamp(http)}")
        order_id, saga_id = await place(http, "lamp", 1, BAD_CARD, customer="anna")
        await asyncio.sleep(0.5)
        log("vera", f"открыла карточку лампы: доступно {await lamp(http)} — «нет в наличии», ушла")
        await wait_final(saga_id)
        log("demo", f"сага {saga_id} отменена, ламп на складе: {await lamp(http)}")
        await worker.stop()

        title("2. Отмена во время саги без семантической блокировки")
        await reset()
        worker = await Worker(naive=1, http_timeout=3).start()
        await cancel_during_saga(http, "naive")
        await worker.stop()

        title("3. Отмена во время саги с семантической блокировкой")
        await reset()
        worker = await Worker(http_timeout=3).start()
        await cancel_during_saga(http, "semantic")

        title("4. Отмена после поворотного шага")
        order_id, saga_id = await place(http, "book", 1, GOOD_CARD, customer="boris")
        await wait_final(saga_id)
        response = await http.post(f"{ORDERS_URL}/orders/{order_id}/cancel")
        log("boris", f"нажал «Отменить заказ» → {response.status_code} {response.json()}")
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
