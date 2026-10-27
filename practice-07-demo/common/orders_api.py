import uuid

from common.config import ORDERS_URL


async def place(client, product_id: str, qty: int, card: str, customer: str = "anna", key: str | None = None) -> tuple[str, str]:
    response = await client.post(
        f"{ORDERS_URL}/orders",
        json={"customer": customer, "product_id": product_id, "qty": qty, "card": card},
        headers={"Idempotency-Key": key or uuid.uuid4().hex},
    )
    order_id = response.json()["order_id"]
    return order_id, "s-" + order_id[2:]
