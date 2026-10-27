import asyncio
import os
import sys

from common.config import PAYMENTS_URL
from common.db import connect
from common.log import log, title
from common.schema import BAD_CARD, GOOD_CARD
from common.show import payments_state, stock_state
from common.stand import client, reset
from part1_naive.place_order import OrderFailed, place_order, place_order_with_except


async def order_status(order_id: str) -> str:
    db = await connect("orders")
    status = await db.fetchval("SELECT status FROM orders WHERE id = $1", order_id)
    await db.close()
    return status


async def last_order() -> str:
    db = await connect("orders")
    order_id = await db.fetchval("SELECT id FROM orders ORDER BY created_at DESC LIMIT 1")
    await db.close()
    return order_id


async def show(order_id: str) -> None:
    print(f"  Orders    заказ {order_id}: {await order_status(order_id)}")
    await stock_state(order_id, "book")
    await payments_state(order_id)


async def main() -> None:
    await reset()
    async with client() as http:
        title("1. Всё хорошо")
        order_id = await place_order(http, "book", 2, GOOD_CARD)
        await show(order_id)

        title("2. Оплата отклонена")
        try:
            await place_order(http, "book", 2, BAD_CARD)
        except OrderFailed as error:
            log("handler", f"пользователю: «{error}»")
        await show(await last_order())

        title("3. Добавили except с отменой — и медленный провайдер")
        await http.post(f"{PAYMENTS_URL}/admin/config", params={"delay": 2.0, "delay_calls": 1})
        try:
            await place_order_with_except(http, "book", 2, GOOD_CARD)
        except OrderFailed as error:
            log("handler", f"пользователю: «{error}»")
        order_id = await last_order()
        await show(order_id)
        log("demo", "ждём, пока провайдер закончит обработку...")
        await asyncio.sleep(1.5)
        await show(order_id)

        title("4. Процесс упал между шагами")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "part1_naive.place_order", "--crash-after", "reserve",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        log("demo", f"процесс завершился с кодом {await process.wait()}")
        await show(await last_order())

        title("5. Пользователь нажал «Оформить» дважды")
        first, second = await asyncio.gather(
            place_order(http, "book", 1, GOOD_CARD), place_order(http, "book", 1, GOOD_CARD)
        )
        await show(first)
        await show(second)


if __name__ == "__main__":
    asyncio.run(main())
