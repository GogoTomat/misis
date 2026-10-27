from fastapi import FastAPI, Header
from pydantic import BaseModel
import uuid

app = FastAPI(title="Payments — idempotency demo")

charges_log: list[dict] = []
idempotency_store: dict[str, dict] = {}


class ChargeRequest(BaseModel):
    amount: int
    card_id: str


def charge_card(amount: int, card_id: str) -> dict:
    result = {
        "transaction_id": str(uuid.uuid4()),
        "amount": amount,
        "card_id": card_id,
    }
    charges_log.append(result)
    return result


@app.post("/charge-unsafe")
def charge_unsafe(payload: ChargeRequest):
    return charge_card(payload.amount, payload.card_id)


@app.post("/charge-safe")
def charge_safe(payload: ChargeRequest, idempotency_key: str = Header(...)):
    existing = idempotency_store.get(idempotency_key)
    if existing is not None:
        return existing
    result = charge_card(payload.amount, payload.card_id)
    idempotency_store[idempotency_key] = result
    return result


@app.get("/charges-count")
def charges_count():
    return {"total_charges": len(charges_log)}


@app.post("/reset")
def reset():
    charges_log.clear()
    idempotency_store.clear()
    return {"ok": True}
