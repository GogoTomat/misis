import asyncio
import time

from fastapi import FastAPI, Header, HTTPException

from services.log import log

app = FastAPI(title="stock")
state = {"delay": 0.0}


@app.post("/admin/delay")
async def set_delay(seconds: float):
    state["delay"] = seconds
    log("stock", f"задержка резерва теперь {seconds} с")
    return state


@app.post("/reserve/naive")
async def reserve_naive(order_id: str):
    log("stock", f"заказ {order_id}: начинаю резерв")
    await asyncio.sleep(state["delay"])
    log("stock", f"заказ {order_id}: резерв выполнен")
    return {"order_id": order_id, "reserved": True}


@app.post("/reserve")
async def reserve(order_id: str, x_request_deadline: float | None = Header(default=None)):
    if x_request_deadline is not None:
        remaining = x_request_deadline - time.time()
        if remaining <= 0:
            log("stock", f"заказ {order_id}: дедлайн уже истёк, работу не начинаю")
            raise HTTPException(504, "deadline exceeded")
        if state["delay"] > remaining:
            log("stock", f"заказ {order_id}: начинаю резерв, осталось {remaining:.2f} с")
            await asyncio.sleep(remaining)
            log("stock", f"заказ {order_id}: дедлайн истёк посреди работы, прекращаю")
            raise HTTPException(504, "deadline exceeded")
    log("stock", f"заказ {order_id}: начинаю резерв")
    await asyncio.sleep(state["delay"])
    log("stock", f"заказ {order_id}: резерв выполнен")
    return {"order_id": order_id, "reserved": True}
