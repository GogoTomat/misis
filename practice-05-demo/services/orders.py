import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException

from services.log import log

STOCK_URL = "http://127.0.0.1:8002"
DEFAULT_BUDGET = 5.0

client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(base_url=STOCK_URL, timeout=httpx.Timeout(30.0, connect=0.5))
    yield
    await client.aclose()


app = FastAPI(title="orders", lifespan=lifespan)


@app.post("/orders/naive")
async def create_order_naive():
    order_id = uuid.uuid4().hex[:6]
    log("orders", f"заказ {order_id}: зову stock без дедлайна")
    response = await client.post("/reserve/naive", params={"order_id": order_id})
    log("orders", f"заказ {order_id}: stock ответил {response.status_code}")
    return {"order_id": order_id, "status": "created"}


@app.post("/orders")
async def create_order(x_request_deadline: float | None = Header(default=None)):
    order_id = uuid.uuid4().hex[:6]
    deadline = x_request_deadline or time.time() + DEFAULT_BUDGET
    remaining = deadline - time.time()
    if remaining <= 0:
        log("orders", f"заказ {order_id}: дедлайн истёк до начала работы")
        raise HTTPException(504, "deadline exceeded")
    log("orders", f"заказ {order_id}: зову stock, осталось {remaining:.2f} с")
    try:
        response = await client.post(
            "/reserve",
            params={"order_id": order_id},
            headers={"X-Request-Deadline": str(deadline)},
            timeout=remaining,
        )
    except httpx.TimeoutException:
        log("orders", f"заказ {order_id}: stock не успел до дедлайна")
        raise HTTPException(504, "deadline exceeded")
    if response.status_code == 504:
        log("orders", f"заказ {order_id}: stock сообщил об истёкшем дедлайне")
        raise HTTPException(504, "deadline exceeded")
    log("orders", f"заказ {order_id}: создан")
    return {"order_id": order_id, "status": "created"}
