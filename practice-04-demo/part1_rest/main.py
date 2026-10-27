from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="Orders API — REST demo")

orders_db: dict[int, dict] = {}
next_id = 1


class OrderCreate(BaseModel):
    product: str
    quantity: int


class OrderReplace(BaseModel):
    product: str
    quantity: int
    status: str


class OrderPatch(BaseModel):
    status: str


@app.post("/orders", status_code=201)
def create_order(payload: OrderCreate, response: Response):
    global next_id
    order_id = next_id
    next_id += 1
    orders_db[order_id] = {
        "id": order_id,
        "product": payload.product,
        "quantity": payload.quantity,
        "status": "DRAFT",
    }
    response.headers["Location"] = f"/orders/{order_id}"
    return orders_db[order_id]


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    order = orders_db.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders")
def list_orders():
    return list(orders_db.values())


@app.put("/orders/{order_id}")
def replace_order(order_id: int, payload: OrderReplace):
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    orders_db[order_id] = {
        "id": order_id,
        "product": payload.product,
        "quantity": payload.quantity,
        "status": payload.status,
    }
    return orders_db[order_id]


@app.patch("/orders/{order_id}")
def update_order_status(order_id: int, payload: OrderPatch):
    order = orders_db.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "SHIPPED" and payload.status != "SHIPPED":
        raise HTTPException(status_code=422, detail="Cannot change status of a shipped order")
    order["status"] = payload.status
    return order


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int):
    orders_db.pop(order_id, None)
    return Response(status_code=204)


@app.post("/orders/{order_id}/duplicate-check", status_code=409)
def duplicate_check_demo(order_id: int, payload: OrderCreate):
    for existing in orders_db.values():
        if existing["product"] == payload.product and existing["quantity"] == payload.quantity:
            raise HTTPException(status_code=409, detail="Identical order already exists")
    return {"ok": True}
