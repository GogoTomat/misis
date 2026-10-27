"""
ХОРОШИЙ Gateway — только маршрутизация, никакой бизнес-логики.
Расчёт скидки переехал в отдельный PricingService (условно).

Запуск: uvicorn good_gateway:app --reload --port 9000
"""
from fastapi import FastAPI

app = FastAPI(title="Gateway (GOOD — только маршрутизация)")

CATALOG_URL = "http://localhost:9001"   # catalog-service
PRICING_URL = "http://localhost:9002"   # pricing-service — считает скидки


@app.get("/products/{product_id}/price")
def get_price(product_id: int, user_is_vip: bool = False):
    # Gateway честно маршрутизирует, а не считает сам:
    #   base_price = httpx.get(f"{CATALOG_URL}/products/{product_id}").json()
    #   final_price = httpx.get(f"{PRICING_URL}/price?...").json()
    # Здесь для демо — просто заглушки, чтобы не подниматть три сервиса разом.
    base_price = 1000.0
    pricing_response = _call_pricing_service(product_id, base_price, user_is_vip)
    return pricing_response


def _call_pricing_service(product_id: int, base_price: float, user_is_vip: bool) -> dict:
    """Имитация вызова отдельного PricingService — вся бизнес-логика скидок там."""
    if user_is_vip:
        discount = 0.15
    elif base_price > 500:
        discount = 0.05
    else:
        discount = 0.0
    return {
        "product_id": product_id,
        "final_price": base_price * (1 - discount),
        "discount_applied": discount,
    }

# Теперь если правило скидок изменится — меняется и деплоится только
# PricingService, силами команды, которая им владеет. Gateway не трогаем.
