class Product:
    def __init__(self, product_id: int, weight_kg: float, dimensions_cm: tuple, fragile: bool):
        self.product_id = product_id
        self.weight_kg = weight_kg
        self.dimensions_cm = dimensions_cm
        self.fragile = fragile
