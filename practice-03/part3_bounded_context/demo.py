from catalog_context.product import Product as CatalogProduct
from shipping_context.product import Product as ShippingProduct
from pricing_context.product import Product as PricingProduct

catalog_product = CatalogProduct(
    product_id=1, title="Наушники", description="Беспроводные", category="Электроника"
)
shipping_product = ShippingProduct(
    product_id=1, weight_kg=0.3, dimensions_cm=(15, 10, 5), fragile=True
)
pricing_product = PricingProduct(
    product_id=1, price=5000, discount_percent=10, tax_rate=0.2
)

print(catalog_product.title)
print(shipping_product.weight_kg)
print(pricing_product.price)
