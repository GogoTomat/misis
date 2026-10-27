from dataclasses import dataclass


class OrderServiceCRUD:
    """Всё в одном месте: и пишет, и читает, через одну модель."""

    def __init__(self):
        self._orders = {}
        self._next_id = 1

    def place_order(self, user_id: int, item: str, price: float) -> dict:
        order = {"id": self._next_id, "user_id": user_id, "item": item, "price": price}
        self._orders[self._next_id] = order
        self._next_id += 1
        return order

    def get_orders_for_user(self, user_id: int) -> list[dict]:
        # каждый раз пересчитываем сумму на лету — обычная CRUD-логика
        return [o for o in self._orders.values() if o["user_id"] == user_id]


@dataclass
class PlaceOrderCommand:
    user_id: int
    item: str
    price: float


class PlaceOrderCommandHandler:
    """Пишет в write-модель. Возвращает минимум — только id."""

    def __init__(self, write_db: dict, order_summary_view: dict):
        self.write_db = write_db
        self.order_summary_view = order_summary_view  # денормализованная read-модель
        self._next_id = 1

    def handle(self, cmd: PlaceOrderCommand) -> int:
        order_id = self._next_id
        self.write_db[order_id] = {"id": order_id, "user_id": cmd.user_id, "item": cmd.item, "price": cmd.price}
        self._next_id += 1

        # синхронизация read-модели — в реальной системе это происходит
        # через событие OrderCreated (см. предыдущий блок практики),
        # здесь для простоты — прямым вызовом
        self._update_read_model(cmd.user_id, order_id, cmd.item, cmd.price)
        return order_id

    def _update_read_model(self, user_id: int, order_id: int, item: str, price: float) -> None:
        summary = self.order_summary_view.setdefault(user_id, {"user_id": user_id, "orders_count": 0, "total_spent": 0.0, "items": []})
        summary["orders_count"] += 1
        summary["total_spent"] += price
        summary["items"].append(item)


@dataclass
class OrderSummaryQuery:
    user_id: int


class OrderSummaryQueryHandler:
    """Читает готовый, уже посчитанный view — без бизнес-валидации, без пересчёта."""

    def __init__(self, order_summary_view: dict):
        self.order_summary_view = order_summary_view

    def handle(self, query: OrderSummaryQuery) -> dict:
        return self.order_summary_view.get(
            query.user_id, {"user_id": query.user_id, "orders_count": 0, "total_spent": 0.0, "items": []}
        )


if __name__ == "__main__":
    print("=== ДО: CRUD ===")
    crud = OrderServiceCRUD()
    crud.place_order(user_id=1, item="Laptop", price=999.0)
    crud.place_order(user_id=1, item="Mouse", price=29.0)
    print(crud.get_orders_for_user(1))
    print("^ каждый вызов get_orders_for_user пересчитывает всё заново\n")

    print("=== ПОСЛЕ: CQRS ===")
    write_db, read_view = {}, {}
    command_handler = PlaceOrderCommandHandler(write_db, read_view)
    query_handler = OrderSummaryQueryHandler(read_view)

    command_handler.handle(PlaceOrderCommand(user_id=1, item="Laptop", price=999.0))
    command_handler.handle(PlaceOrderCommand(user_id=1, item="Mouse", price=29.0))

    summary = query_handler.handle(OrderSummaryQuery(user_id=1))
    print(summary)
    print("^ query_handler просто читает готовый агрегат — сумма уже посчитана")
