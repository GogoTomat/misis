class Order:
    def __init__(self, order_id: int, status: str, total: "Money"):
        self.order_id = order_id
        self.status = status
        self.total = total

    def __eq__(self, other):
        if not isinstance(other, Order):
            return False
        return self.order_id == other.order_id
