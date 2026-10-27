class Product:
    def __init__(self, product_id: int, price: int, discount_percent: int, tax_rate: float):
        self.product_id = product_id
        self.price = price
        self.discount_percent = discount_percent
        self.tax_rate = tax_rate
