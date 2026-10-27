from order_line import OrderLine


class Order:
    def __init__(self, order_id: int):
        self.order_id = order_id
        self.status = "DRAFT"
        self._lines = []

    def add_line(self, product_id: int, quantity: int, price: int) -> None:
        if self.status == "SHIPPED":
            raise ValueError(self.status)
        self._lines.append(OrderLine(product_id, quantity, price))

    def ship(self) -> None:
        self.status = "SHIPPED"

    def total(self) -> int:
        return sum(line.subtotal() for line in self._lines)
