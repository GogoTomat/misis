class Product:
    def __init__(
        self,
        product_id: int,
        title: str,
        description: str,
        category: str,
        weight_kg: float,
        dimensions_cm: tuple,
        fragile: bool,
        price: int,
        discount_percent: int,
        tax_rate: float,
    ):
        self.product_id = product_id
        self.title = title
        self.description = description
        self.category = category
        self.weight_kg = weight_kg
        self.dimensions_cm = dimensions_cm
        self.fragile = fragile
        self.price = price
        self.discount_percent = discount_percent
        self.tax_rate = tax_rate
