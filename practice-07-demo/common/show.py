from common.db import connect


async def available(product_id: str) -> int:
    conn = await connect("stock")
    value = await conn.fetchval("SELECT available FROM products WHERE id = $1", product_id)
    await conn.close()
    return value


async def state(saga_id: str, product_id: str) -> None:
    orders = await connect("orders")
    row = await orders.fetchrow(
        "SELECT o.id, o.status, o.cancel_requested, s.state FROM sagas s JOIN orders o ON o.id = s.order_id WHERE s.id = $1",
        saga_id,
    )
    await orders.close()
    if row:
        flag = " · cancel_requested" if row["cancel_requested"] else ""
        print(f"  Orders    заказ {row['id']}: {row['status']}{flag} · сага {saga_id}: {row['state']}")
    await stock_state(saga_id, product_id)
    await payments_state(saga_id)


async def stock_state(saga_id: str, product_id: str) -> None:
    stock = await connect("stock")
    left = await stock.fetchval("SELECT available FROM products WHERE id = $1", product_id)
    rows = await stock.fetch("SELECT qty, status FROM reservations WHERE saga_id = $1 ORDER BY id", saga_id)
    await stock.close()
    text = ", ".join(f"{r['qty']} шт. {r['status']}" for r in rows) or "нет"
    print(f"  Stock     {product_id}: доступно {left} · резервы: {text}")


async def payments_state(saga_id: str) -> None:
    payments = await connect("payments")
    rows = await payments.fetch("SELECT id, amount, status FROM payments WHERE saga_id = $1 ORDER BY created_at", saga_id)
    await payments.close()
    text = ", ".join(f"{r['id']} {r['amount']} ₽ {r['status']}" for r in rows) or "нет"
    print(f"  Payments  платежи: {text}")


async def history(saga_id: str) -> None:
    orders = await connect("orders")
    rows = await orders.fetch("SELECT at, event FROM saga_log WHERE saga_id = $1 ORDER BY id", saga_id)
    await orders.close()
    print(f"  Журнал саги {saga_id}:")
    start = rows[0]["at"] if rows else None
    for r in rows:
        print(f"    +{(r['at'] - start).total_seconds():5.2f} с  {r['event']}")
