import argparse
import asyncio
import os
import uuid

import httpx

from common.config import PAYMENTS_URL, STOCK_URL
from common.db import connect
from common.log import log


class OrderFailed(Exception):
    pass


async def place_order(client, product_id: str, qty: int, card: str, crash_after: str = "") -> str:
    order_id = "o-" + uuid.uuid4().hex[:6]
    db = await connect("orders")
    amount = await db.fetchval("SELECT price FROM prices WHERE product_id = $1", product_id) * qty
    await db.execute(
        "INSERT INTO orders (id, customer, product_id, qty, amount, card) VALUES ($1, 'anna', $2, $3, $4, $5)",
        order_id, product_id, qty, amount, card,
    )
    log("naive", f"{order_id}: заказ создан, PENDING")
    reserved = await client.post(
        f"{STOCK_URL}/reservations",
        json={"saga_id": order_id, "product_id": product_id, "qty": qty, "ttl_seconds": 3600},
    )
    if reserved.json()["status"] != "held":
        raise OrderFailed("нет товара")
    if crash_after == "reserve":
        log("naive", f"{order_id}: товар зарезервирован — процесс падает")
        os._exit(1)
    paid = await client.post(
        f"{PAYMENTS_URL}/charges", json={"saga_id": order_id, "card": card, "amount": amount}, timeout=1.0
    )
    if paid.json()["status"] != "captured":
        raise OrderFailed("оплата отклонена")
    await client.post(f"{STOCK_URL}/reservations/{order_id}/confirm")
    await db.execute("UPDATE orders SET status = 'CONFIRMED' WHERE id = $1", order_id)
    await db.close()
    log("naive", f"{order_id}: заказ подтверждён")
    return order_id


async def place_order_with_except(client, product_id: str, qty: int, card: str) -> str:
    order_id = "o-" + uuid.uuid4().hex[:6]
    db = await connect("orders")
    amount = await db.fetchval("SELECT price FROM prices WHERE product_id = $1", product_id) * qty
    await db.execute(
        "INSERT INTO orders (id, customer, product_id, qty, amount, card) VALUES ($1, 'anna', $2, $3, $4, $5)",
        order_id, product_id, qty, amount, card,
    )
    log("naive", f"{order_id}: заказ создан, PENDING")
    await client.post(
        f"{STOCK_URL}/reservations",
        json={"saga_id": order_id, "product_id": product_id, "qty": qty, "ttl_seconds": 3600},
    )
    try:
        paid = await client.post(
            f"{PAYMENTS_URL}/charges", json={"saga_id": order_id, "card": card, "amount": amount}, timeout=1.0
        )
        if paid.json()["status"] != "captured":
            raise OrderFailed("оплата отклонена")
    except (httpx.HTTPError, OrderFailed) as error:
        log("naive", f"{order_id}: ошибка «{type(error).__name__}» — снимаю резерв и отменяю заказ")
        await client.post(f"{STOCK_URL}/reservations/{order_id}/release")
        await db.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = $1", order_id)
        await db.close()
        raise OrderFailed("не удалось оформить") from error
    await client.post(f"{STOCK_URL}/reservations/{order_id}/confirm")
    await db.execute("UPDATE orders SET status = 'CONFIRMED' WHERE id = $1", order_id)
    await db.close()
    return order_id


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash-after", default="")
    parser.add_argument("--card", default="4111-1111-1111-1111")
    args = parser.parse_args()
    async with httpx.AsyncClient(trust_env=False) as client:
        await place_order(client, "book", 2, args.card, args.crash_after)


if __name__ == "__main__":
    asyncio.run(main())
