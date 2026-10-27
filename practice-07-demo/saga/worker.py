import asyncio
import json
import os
import uuid

import asyncpg
import httpx

from common.config import PAYMENTS_URL, STOCK_URL
from common.db import connect
from common.log import log

NAME = os.getenv("SAGA_WORKER_NAME", "worker")
HTTP_TIMEOUT = float(os.getenv("SAGA_HTTP_TIMEOUT", "1.0"))
CRASH_AFTER = os.getenv("SAGA_CRASH_AFTER", "")
NEW_KEY_ON_RETRY = os.getenv("SAGA_NEW_KEY_ON_RETRY") == "1"
NAIVE = os.getenv("SAGA_NAIVE") == "1"
RESERVE_TTL = float(os.getenv("SAGA_RESERVE_TTL", "20"))
MAX_RETRIES = int(os.getenv("SAGA_MAX_RETRIES", "5"))
MAX_RETRIES_AFTER_PIVOT = int(os.getenv("SAGA_MAX_RETRIES_AFTER_PIVOT", "6"))
BACKOFF = 0.5
LEASE = max(3.0, HTTP_TIMEOUT * 2 + 1)
LOOPS = 4

PRE_PIVOT = ("STARTED", "STOCK_RESERVED", "AUTHORIZED")
FINAL = ("CONFIRMED", "CANCELLED", "NEEDS_ATTENTION")

CLAIM = f"""
UPDATE sagas s SET locked_until = now() + make_interval(secs => $1)
  FROM orders o
 WHERE s.id = (
        SELECT id FROM sagas
         WHERE state NOT IN {FINAL}
           AND next_run_at <= now() AND locked_until <= now()
         ORDER BY next_run_at
         FOR UPDATE SKIP LOCKED
         LIMIT 1)
   AND o.id = s.order_id
RETURNING s.*, o.cancel_requested, now() > s.deadline AS expired
"""


class Retry(Exception):
    pass


async def call(client: httpx.AsyncClient, url: str, body: dict | None = None, key: str | None = None) -> dict:
    headers = {"Idempotency-Key": key} if key else {}
    try:
        response = await client.post(url, json=body, headers=headers, timeout=HTTP_TIMEOUT)
    except httpx.TimeoutException:
        raise Retry(f"таймаут {HTTP_TIMEOUT:g} с")
    except httpx.TransportError:
        raise Retry("участник недоступен")
    if response.status_code == 409 or response.status_code >= 500:
        raise Retry(f"HTTP {response.status_code}")
    response.raise_for_status()
    return response.json()


def crash_point(step: str, saga_id: str) -> None:
    if CRASH_AFTER == step:
        log(NAME, f"{saga_id}: ответ на «{step}» получен — процесс падает, состояние не сохранено")
        os._exit(1)


async def run_step(client: httpx.AsyncClient, saga: asyncpg.Record) -> tuple[str, str]:
    sid, state, data = saga["id"], saga["state"], json.loads(saga["data"])
    if state in PRE_PIVOT:
        if saga["cancel_requested"] and not NAIVE:
            return "COMPENSATING", "покупатель запросил отмену"
        if saga["expired"]:
            return "COMPENSATING", "истёк срок саги"
    if state == "STARTED":
        body = {"saga_id": sid, "product_id": data["product_id"], "qty": data["qty"], "ttl_seconds": RESERVE_TTL}
        result = await call(client, f"{STOCK_URL}/reservations", body, f"{sid}:reserve")
        crash_point("reserve", sid)
        if result["status"] == "held":
            return "STOCK_RESERVED", "товар зарезервирован"
        return "COMPENSATING", f"склад отказал: {result.get('reason', result['status'])}"
    if state == "STOCK_RESERVED":
        key = f"{sid}:authorize"
        if NEW_KEY_ON_RETRY and saga["attempts"] > 0:
            key = f"{sid}:authorize:{uuid.uuid4().hex[:4]}"
        body = {"saga_id": sid, "card": data["card"], "amount": data["amount"]}
        result = await call(client, f"{PAYMENTS_URL}/authorizations", body, key)
        crash_point("authorize", sid)
        if result["status"] == "authorized":
            return "AUTHORIZED", f"деньги заблокированы, платёж {result['payment_id']}"
        reasons = {"declined": "банк отклонил оплату", "cancelled": "авторизация уже отменена"}
        return "COMPENSATING", reasons.get(result["status"], result["status"])
    if state == "AUTHORIZED":
        result = await call(client, f"{STOCK_URL}/reservations/{sid}/confirm")
        crash_point("confirm", sid)
        if result["status"] == "confirmed":
            return "STOCK_CONFIRMED", "резерв подтверждён — поворотный шаг пройден"
        return "COMPENSATING", "резерв истёк до подтверждения"
    if state == "STOCK_CONFIRMED":
        await call(client, f"{PAYMENTS_URL}/authorizations/{sid}/capture")
        crash_point("capture", sid)
        return "CAPTURED", "деньги списаны"
    if state == "CAPTURED":
        return "CONFIRMED", "заказ подтверждён"
    if state == "COMPENSATING":
        await call(client, f"{PAYMENTS_URL}/authorizations/{sid}/void")
        await call(client, f"{STOCK_URL}/reservations/{sid}/release")
        return "CANCELLED", "компенсации выполнены, заказ отменён"
    raise RuntimeError(f"unknown state {state}")


async def save(conn: asyncpg.Connection, saga: asyncpg.Record, new_state: str, event: str, patch: dict | None = None) -> None:
    async with conn.transaction():
        updated = await conn.execute(
            """
            UPDATE sagas SET state = $2, attempts = 0, next_run_at = now(), locked_until = now(),
                             version = version + 1, data = data || $4::jsonb
             WHERE id = $1 AND version = $3
            """,
            saga["id"], new_state, saga["version"], json.dumps(patch or {}),
        )
        if updated == "UPDATE 0":
            log(NAME, f"{saga['id']}: состояние уже изменил другой исполнитель, результат отброшен")
            return
        await conn.execute(
            "INSERT INTO saga_log (saga_id, event) VALUES ($1, $2)", saga["id"], f"{saga['state']} → {new_state}: {event}"
        )
        if new_state == "CONFIRMED":
            if NAIVE:
                await conn.execute("UPDATE orders SET status = 'CONFIRMED' WHERE id = $1", saga["order_id"])
            else:
                late_cancel = await conn.fetchval(
                    "UPDATE orders SET status = 'CONFIRMED' WHERE id = $1 AND status = 'PENDING' RETURNING cancel_requested",
                    saga["order_id"],
                )
                if late_cancel:
                    await conn.execute(
                        "INSERT INTO saga_log (saga_id, event) VALUES ($1, 'отмена пришла после поворотного шага — нужен возврат')",
                        saga["id"],
                    )
        if new_state == "CANCELLED":
            await conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = $1", saga["order_id"])
    log(NAME, f"{saga['id']}: {saga['state']} → {new_state} ({event})")


async def retry_later(conn: asyncpg.Connection, saga: asyncpg.Record, error: str) -> None:
    attempts = saga["attempts"] + 1
    limit = MAX_RETRIES if saga["state"] in PRE_PIVOT else MAX_RETRIES_AFTER_PIVOT
    if attempts > limit:
        if saga["state"] in PRE_PIVOT:
            await save(conn, saga, "COMPENSATING", f"{error}, попытки исчерпаны")
        else:
            await save(conn, saga, "NEEDS_ATTENTION", f"{error}, попытки исчерпаны", {"resume_state": saga["state"]})
        return
    delay = BACKOFF * 2 ** (attempts - 1)
    async with conn.transaction():
        await conn.execute(
            """
            UPDATE sagas SET attempts = $2, next_run_at = now() + make_interval(secs => $3),
                             locked_until = now(), version = version + 1
             WHERE id = $1 AND version = $4
            """,
            saga["id"], attempts, delay, saga["version"],
        )
        await conn.execute(
            "INSERT INTO saga_log (saga_id, event) VALUES ($1, $2)",
            saga["id"], f"{saga['state']}: {error}, попытка {attempts}, повтор через {delay:g} с",
        )
    log(NAME, f"{saga['id']}: {saga['state']} — {error}, попытка {attempts}, повтор через {delay:g} с")


async def loop(client: httpx.AsyncClient) -> None:
    conn = await connect("orders")
    while True:
        saga = await conn.fetchrow(CLAIM, LEASE)
        if saga is None:
            await asyncio.sleep(0.1)
            continue
        try:
            new_state, event = await run_step(client, saga)
        except Retry as error:
            await retry_later(conn, saga, str(error))
            continue
        await save(conn, saga, new_state, event)


async def main() -> None:
    flags = [f for f, on in (("naive", NAIVE), ("new-key-on-retry", NEW_KEY_ON_RETRY)) if on]
    if CRASH_AFTER:
        flags.append(f"crash-after={CRASH_AFTER}")
    log(NAME, f"оркестратор запущен, таймаут {HTTP_TIMEOUT:g} с" + (f", {', '.join(flags)}" if flags else ""))
    async with httpx.AsyncClient(trust_env=False) as client:
        await asyncio.gather(*(loop(client) for _ in range(LOOPS)))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
