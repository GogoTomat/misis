import asyncio
import uuid

from fastapi import FastAPI, Header, HTTPException

from services.log import log

app = FastAPI(title="payments")

PENDING = "pending"
state = {"delay": 0.0, "charged_total": 0, "charges": 0}
idempotency: dict[str, object] = {}


@app.post("/admin/delay")
async def set_delay(seconds: float):
    state["delay"] = seconds
    return state


@app.post("/admin/reset")
async def reset():
    state.update(charged_total=0, charges=0)
    idempotency.clear()
    return state


@app.get("/account")
async def account():
    return {"charged_total": state["charged_total"], "charges": state["charges"]}


@app.post("/charge")
async def charge(amount: int, idempotency_key: str | None = Header(default=None)):
    if idempotency_key is not None:
        existing = idempotency.get(idempotency_key)
        if existing == PENDING:
            log("payments", f"ключ {idempotency_key[:8]}: ещё обрабатывается")
            raise HTTPException(409, "request with this key is still in progress")
        if existing is not None:
            log("payments", f"ключ {idempotency_key[:8]}: повтор, отдаю сохранённый результат")
            return existing
        idempotency[idempotency_key] = PENDING
    log("payments", f"списываю {amount} ₽")
    await asyncio.sleep(state["delay"])
    result = {"charge_id": uuid.uuid4().hex[:8], "amount": amount}
    state["charged_total"] += amount
    state["charges"] += 1
    if idempotency_key is not None:
        idempotency[idempotency_key] = result
    log("payments", f"списано {amount} ₽, charge_id={result['charge_id']}")
    return result
