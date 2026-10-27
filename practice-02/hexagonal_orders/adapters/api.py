from fastapi import FastAPI, HTTPException
from domain.use_cases import PlaceOrderUseCase, GetOrderUseCase
from adapters.sqlite_repository import SqliteOrderRepository

app = FastAPI(title="Orders (Hexagonal)")

repository = SqliteOrderRepository()
place_order_use_case = PlaceOrderUseCase(repository)
get_order_use_case = GetOrderUseCase(repository)


@app.post("/orders")
def create_order(user_id: int, item: str):
    try:
        order = place_order_use_case.execute(user_id=user_id, item=item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"order_id": order.id}


@app.get("/orders/{order_id}")
def read_order(order_id: int):
    try:
        order = get_order_use_case.execute(order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "id": order.id,
        "user_id": order.user_id,
        "item": order.item,
        "status_label": order.status_label,
    }
