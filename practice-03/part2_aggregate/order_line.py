class OrderLine:
    def __init__(self, product_id: int, quantity: int, price: int):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price

    def subtotal(self) -> int:
        return self.price * self.quantity
