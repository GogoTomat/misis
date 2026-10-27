import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from pydantic import BaseModel

from common.db import pool
from common.log import log

config = {"idempotency": True}
db = {}


async def sweeper() -> None:
    while True:
        await asyncio.sleep(0.5)
        async with db["pool"].acquire() as conn, conn.transaction():
            expired = await conn.fetch(
                """
                UPDATE reservations SET status = 'EXPIRED'
                 WHERE status = 'HELD' AND expires_at <= now()
                RETURNING saga_id, product_id, qty
                """
            )
            for row in expired:
                await conn.execute(
                    "UPDATE products SET available = available + $2 WHERE id = $1",
                    row["product_id"], row["qty"],
                )
                log("stock", f"{row['saga_id']}: резерв {row['qty']} × {row['product_id']} истёк, вернул на склад")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db["pool"] = await pool("stock")
    task = asyncio.create_task(sweeper())
    yield
    task.cancel()
    await db["pool"].close()


app = FastAPI(title="stock", lifespan=lifespan)


class ReserveRequest(BaseModel):
    saga_id: str
    product_id: str
    qty: int
    ttl_seconds: float = 20


@app.post("/admin/config")
async def set_config(idempotency: bool = True):
    config["idempotency"] = idempotency
    return config


@app.get("/products/{product_id}")
async def product(product_id: str):
    async with db["pool"].acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, available FROM products WHERE id = $1", product_id)
    return dict(row)


@app.post("/reservations")
async def reserve(body: ReserveRequest, idempotency_key: str | None = Header(default=None)):
    use_key = idempotency_key is not None and config["idempotency"]
    async with db["pool"].acquire() as conn, conn.transaction():
        if use_key:
            fresh = await conn.fetchval(
                "INSERT INTO processed (key, status) VALUES ($1, 'IN_PROGRESS') ON CONFLICT DO NOTHING RETURNING key",
                idempotency_key,
            )
            if fresh is None:
                row = await conn.fetchrow("SELECT status, response FROM processed WHERE key = $1", idempotency_key)
                if row["status"] == "TOMBSTONE":
                    log("stock", f"{body.saga_id}: резерв уже отменён (tombstone), не выполняю")
                    return {"status": "cancelled"}
                log("stock", f"{body.saga_id}: повтор по ключу {idempotency_key}, отдаю сохранённый ответ")
                return json.loads(row["response"])
        taken = await conn.fetchval(
            "UPDATE products SET available = available - $2 WHERE id = $1 AND available >= $2 RETURNING available",
            body.product_id, body.qty,
        )
        if taken is None:
            response = {"status": "rejected", "reason": "out_of_stock"}
            log("stock", f"{body.saga_id}: {body.product_id} × {body.qty} — не хватает, отказ")
        else:
            await conn.execute(
                """
                INSERT INTO reservations (saga_id, product_id, qty, status, expires_at)
                VALUES ($1, $2, $3, 'HELD', now() + make_interval(secs => $4))
                """,
                body.saga_id, body.product_id, body.qty, body.ttl_seconds,
            )
            response = {"status": "held", "available": taken}
            log("stock", f"{body.saga_id}: зарезервировал {body.qty} × {body.product_id} на {body.ttl_seconds:g} с, осталось {taken}")
        if use_key:
            await conn.execute(
                "UPDATE processed SET status = 'DONE', response = $2 WHERE key = $1",
                idempotency_key, json.dumps(response),
            )
    return response


@app.post("/reservations/{saga_id}/confirm")
async def confirm(saga_id: str):
    async with db["pool"].acquire() as conn, conn.transaction():
        confirmed = await conn.execute(
            """
            UPDATE reservations SET status = 'CONFIRMED'
             WHERE saga_id = $1 AND status = 'HELD' AND expires_at > now()
            """,
            saga_id,
        )
        if confirmed != "UPDATE 0":
            log("stock", f"{saga_id}: резерв подтверждён")
            return {"status": "confirmed"}
        already = await conn.fetchval(
            "SELECT count(*) FROM reservations WHERE saga_id = $1 AND status = 'CONFIRMED'", saga_id
        )
    if already:
        log("stock", f"{saga_id}: резерв уже был подтверждён")
        return {"status": "confirmed"}
    log("stock", f"{saga_id}: подтверждать нечего — резерв истёк или снят")
    return {"status": "expired"}


@app.post("/reservations/{saga_id}/release")
async def release(saga_id: str):
    async with db["pool"].acquire() as conn, conn.transaction():
        released = await conn.fetch(
            """
            UPDATE reservations SET status = 'RELEASED'
             WHERE saga_id = $1 AND status = 'HELD'
            RETURNING product_id, qty
            """,
            saga_id,
        )
        for row in released:
            await conn.execute(
                "UPDATE products SET available = available + $2 WHERE id = $1", row["product_id"], row["qty"]
            )
        if released:
            log("stock", f"{saga_id}: резерв снят, товар вернулся на склад")
            return {"status": "released"}
        marked = await conn.execute(
            """
            INSERT INTO processed (key, status) VALUES ($1, 'TOMBSTONE')
            ON CONFLICT (key) DO UPDATE SET status = 'TOMBSTONE' WHERE processed.status = 'IN_PROGRESS'
            """,
            f"{saga_id}:reserve",
        )
    log("stock", f"{saga_id}: снимать нечего" + (", оставил tombstone" if marked == "INSERT 0 1" else ""))
    return {"status": "nothing"}
