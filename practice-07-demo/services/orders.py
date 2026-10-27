import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from common.db import pool
from common.log import log

db = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db["pool"] = await pool("orders")
    yield
    await db["pool"].close()


app = FastAPI(title="orders", lifespan=lifespan)


class OrderRequest(BaseModel):
    customer: str
    product_id: str
    qty: int
    card: str


@app.post("/orders", status_code=202)
async def create_order(body: OrderRequest, idempotency_key: str = Header()):
    order_id = "o-" + uuid.uuid4().hex[:6]
    async with db["pool"].acquire() as conn, conn.transaction():
        price = await conn.fetchval("SELECT price FROM prices WHERE product_id = $1", body.product_id)
        if price is None:
            raise HTTPException(404, "unknown product")
        created = await conn.fetchval(
            """
            INSERT INTO orders (id, client_key, customer, product_id, qty, amount, card)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (client_key) DO NOTHING RETURNING id
            """,
            order_id, idempotency_key, body.customer, body.product_id, body.qty, price * body.qty, body.card,
        )
        if created is None:
            existing = await conn.fetchval("SELECT id FROM orders WHERE client_key = $1", idempotency_key)
            log("orders", f"повтор POST /orders с ключом {idempotency_key}: тот же заказ {existing}")
            return JSONResponse({"order_id": existing}, 202, headers={"Location": f"/orders/{existing}"})
        saga_id = "s-" + order_id[2:]
        data = {"product_id": body.product_id, "qty": body.qty, "amount": price * body.qty, "card": body.card}
        await conn.execute(
            "INSERT INTO sagas (id, order_id, state, deadline, data) VALUES ($1, $2, 'STARTED', now() + interval '30 seconds', $3)",
            saga_id, order_id, json.dumps(data),
        )
        await conn.execute("INSERT INTO saga_log (saga_id, event) VALUES ($1, 'создана, STARTED')", saga_id)
    log("orders", f"заказ {order_id} принят: {body.qty} × {body.product_id} на {price * body.qty} ₽, сага {saga_id}")
    return JSONResponse({"order_id": order_id}, 202, headers={"Location": f"/orders/{order_id}"})


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    async with db["pool"].acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT o.id, o.status, o.cancel_requested, s.id AS saga_id, s.state AS saga_state
              FROM orders o LEFT JOIN sagas s ON s.order_id = o.id
             WHERE o.id = $1
            """,
            order_id,
        )
    if row is None:
        raise HTTPException(404, "not found")
    return dict(row)


@app.post("/orders/{order_id}/cancel")
async def cancel(order_id: str, mode: str = "semantic"):
    async with db["pool"].acquire() as conn:
        if mode == "naive":
            await conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = $1", order_id)
            log("orders", f"{order_id}: отмена покупателем — сразу CANCELLED")
            return {"status": "CANCELLED"}
        requested = await conn.fetchval(
            """
            UPDATE orders o SET cancel_requested = true
              FROM sagas s
             WHERE o.id = $1 AND s.order_id = o.id AND o.status = 'PENDING'
               AND s.state IN ('STARTED', 'STOCK_RESERVED', 'AUTHORIZED')
            RETURNING o.id
            """,
            order_id,
        )
    if requested:
        log("orders", f"{order_id}: отмена запрошена, сага увидит отметку")
        return {"status": "CANCEL_REQUESTED"}
    log("orders", f"{order_id}: отменить нельзя — поворотный шаг пройден, только возврат")
    raise HTTPException(409, "order is past the point of no return")
