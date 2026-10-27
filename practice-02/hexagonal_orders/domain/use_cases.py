from .models import Order
from .ports import OrderRepository


class PlaceOrderUseCase:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, user_id: int, item: str) -> Order:
        order = Order(user_id=user_id, item=item)
        order.validate()
        return self.repository.save(order)


class GetOrderUseCase:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    def execute(self, order_id: int) -> Order:
        order = self.repository.find_by_id(order_id)
        if order is None:
            raise ValueError("order not found")
        return order
