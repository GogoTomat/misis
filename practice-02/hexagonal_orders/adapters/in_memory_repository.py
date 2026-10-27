from domain.models import Order
from domain.ports import OrderRepository


class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._storage: dict[int, Order] = {}
        self._next_id = 1

    def save(self, order: Order) -> Order:
        order.id = self._next_id
        self._storage[order.id] = order
        self._next_id += 1
        return order

    def find_by_id(self, order_id: int) -> Order | None:
        return self._storage.get(order_id)
