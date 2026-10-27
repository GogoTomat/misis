from pydantic import BaseModel, ConfigDict


class StrictOrderPlaced(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: str
    order_id: str
    customer_email: str
    total: int


class TolerantOrderPlaced(BaseModel):
    model_config = ConfigDict(extra="ignore")
    order_id: str
    customer_email: str
    total: int


def billing_handler(event: dict) -> str:
    order = TolerantOrderPlaced.model_validate(event)
    return f"Billing: счёт по {order.order_id} на {order.total / 100:.2f} ₽"


def notification_handler(event: dict) -> str:
    order = TolerantOrderPlaced.model_validate(event)
    return f"Notifications: письмо на {order.customer_email}: «К оплате {order.total} ₽»"
