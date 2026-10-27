import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from common.db import pool
from common.log import log

DEFAULTS = {"delay": 0.0, "delay_calls": 0, "tombstones": True, "fail_capture": False}
config = dict(DEFAULTS)
db = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db["pool"] = await pool("payments")
    yield
    await db["pool"].close()


app = FastAPI(title="payments", lifespan=lifespan)


class PayRequest(BaseModel):
    saga_id: str
    card: str
    amount: int


@app.post("/admin/config")
async def set_config(
    delay: float = 0.0, delay_calls: int = 0, tombstones: bool = True, fail_capture: bool = False
):
    config.update(delay=delay, delay_calls=delay_calls, tombstones=tombstones, fail_capture=fail_capture)
    return config


async def provider_delay() -> None:
    if config["delay_calls"] > 0:
        config["delay_calls"] -= 1
        log("payments", f"провайдер отвечает медленно: {config['delay']:g} с")
        await asyncio.sleep(config["delay"])


async def card_limit(conn, card: str) -> int:
    return await conn.fetchval("SELECT limit_amount FROM cards WHERE card = $1", card) or 0


@app.post("/charges")
async def charge(body: PayRequest):
    await provider_delay()
    async with db["pool"].acquire() as conn:
        if body.amount > await card_limit(conn, body.card):
            log("payments", f"{body.saga_id}: списание {body.amount} ₽ отклонено банком")
            return {"status": "declined"}
        payment_id = uuid.uuid4().hex[:8]
        await conn.execute(
            "INSERT INTO payments (id, saga_id, card, amount, status) VALUES ($1, $2, $3, $4, 'CAPTURED')",
            payment_id, body.saga_id, body.card, body.amount,
        )
    log("payments", f"{body.saga_id}: списано {body.amount} ₽, платёж {payment_id}")
    return {"status": "captured", "payment_id": payment_id}


@app.post("/authorizations")
async def authorize(body: PayRequest, idempotency_key: str | None = Header(default=None)):
    async with db["pool"].acquire() as conn:
        if idempotency_key is not None:
            fresh = await conn.fetchval(
                "INSERT INTO processed (key, status) VALUES ($1, 'IN_PROGRESS') ON CONFLICT DO NOTHING RETURNING key",
                idempotency_key,
            )
            if fresh is None:
                row = await conn.fetchrow("SELECT status, response FROM processed WHERE key = $1", idempotency_key)
                if row["status"] == "IN_PROGRESS":
                    log("payments", f"{body.saga_id}: ключ {idempotency_key} ещё обрабатывается — 409")
                    raise HTTPException(409, "request with this key is still in progress")
                if row["status"] == "TOMBSTONE":
                    log("payments", f"{body.saga_id}: авторизация уже отменена (tombstone), не выполняю")
                    return {"status": "cancelled"}
                log("payments", f"{body.saga_id}: повтор по ключу {idempotency_key}, отдаю сохранённый ответ")
                return json.loads(row["response"])
        log("payments", f"{body.saga_id}: авторизация {body.amount} ₽, ключ {idempotency_key}")
        await provider_delay()
        async with conn.transaction():
            if idempotency_key is not None:
                status = await conn.fetchval(
                    "SELECT status FROM processed WHERE key = $1 FOR UPDATE", idempotency_key
                )
                if status == "TOMBSTONE":
                    log("payments", f"{body.saga_id}: пока шла авторизация, пришла отмена — не блокирую деньги")
                    return {"status": "cancelled"}
            if body.amount > await card_limit(conn, body.card):
                response = {"status": "declined"}
                log("payments", f"{body.saga_id}: банк отклонил авторизацию")
            else:
                payment_id = uuid.uuid4().hex[:8]
                await conn.execute(
                    "INSERT INTO payments (id, saga_id, card, amount, status) VALUES ($1, $2, $3, $4, 'AUTHORIZED')",
                    payment_id, body.saga_id, body.card, body.amount,
                )
                response = {"status": "authorized", "payment_id": payment_id}
                log("payments", f"{body.saga_id}: {body.amount} ₽ заблокировано на карте, платёж {payment_id}")
            if idempotency_key is not None:
                await conn.execute(
                    "UPDATE processed SET status = 'DONE', response = $2 WHERE key = $1",
                    idempotency_key, json.dumps(response),
                )
    return response


@app.post("/authorizations/{saga_id}/capture")
async def capture(saga_id: str):
    if config["fail_capture"]:
        log("payments", f"{saga_id}: провайдер недоступен — 503")
        raise HTTPException(503, "provider unavailable")
    async with db["pool"].acquire() as conn:
        captured = await conn.fetch(
            "UPDATE payments SET status = 'CAPTURED' WHERE saga_id = $1 AND status = 'AUTHORIZED' RETURNING id, amount",
            saga_id,
        )
        total = await conn.fetchval(
            "SELECT count(*) FROM payments WHERE saga_id = $1 AND status = 'CAPTURED'", saga_id
        )
    for row in captured:
        log("payments", f"{saga_id}: списал {row['amount']} ₽ по платежу {row['id']}")
    if not captured:
        log("payments", f"{saga_id}: списывать нечего, уже списано")
    return {"status": "captured" if total else "nothing"}


@app.post("/authorizations/{saga_id}/void")
async def void(saga_id: str):
    async with db["pool"].acquire() as conn, conn.transaction():
        voided = await conn.fetch(
            "UPDATE payments SET status = 'VOIDED' WHERE saga_id = $1 AND status = 'AUTHORIZED' RETURNING id",
            saga_id,
        )
        if voided:
            log("payments", f"{saga_id}: блокировка снята ({len(voided)} шт.)")
            return {"status": "voided"}
        if config["tombstones"]:
            marked = await conn.execute(
                """
                INSERT INTO processed (key, status) VALUES ($1, 'TOMBSTONE')
                ON CONFLICT (key) DO UPDATE SET status = 'TOMBSTONE' WHERE processed.status = 'IN_PROGRESS'
                """,
                f"{saga_id}:authorize",
            )
            if marked == "INSERT 0 1":
                log("payments", f"{saga_id}: снимать нечего, оставил tombstone")
                return {"status": "nothing"}
        log("payments", f"{saga_id}: снимать нечего")
    return {"status": "nothing"}
