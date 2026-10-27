import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.use_cases import PlaceOrderUseCase, GetOrderUseCase
from adapters.in_memory_repository import InMemoryOrderRepository


def test_place_order_succeeds():
    repo = InMemoryOrderRepository()
    use_case = PlaceOrderUseCase(repository=repo)

    order = use_case.execute(user_id=1, item="Laptop")

    assert order.id == 1
    assert order.status_label == "Обрабатывается"


def test_place_order_rejects_empty_item():
    repo = InMemoryOrderRepository()
    use_case = PlaceOrderUseCase(repository=repo)

    with pytest.raises(ValueError):
        use_case.execute(user_id=1, item="")


def test_get_order_not_found():
    repo = InMemoryOrderRepository()
    use_case = GetOrderUseCase(repository=repo)

    with pytest.raises(ValueError):
        use_case.execute(order_id=999)


def test_place_then_get_order():
    repo = InMemoryOrderRepository()  # ОДИН И ТОТ ЖЕ repo для обоих use case
    place = PlaceOrderUseCase(repository=repo)
    get = GetOrderUseCase(repository=repo)

    created = place.execute(user_id=7, item="Mouse")
    fetched = get.execute(order_id=created.id)

    assert fetched.item == "Mouse"
    assert fetched.user_id == 7
