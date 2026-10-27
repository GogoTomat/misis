from abc import ABC, abstractmethod
from .models import Order


class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> Order: ...

    @abstractmethod
    def find_by_id(self, order_id: int) -> Order | None: ...
