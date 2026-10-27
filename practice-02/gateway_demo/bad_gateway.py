from fastapi import FastAPI

app = FastAPI(title="Gateway (BAD — с бизнес-логикой)")

CATALOG_URL = "http://localhost:9001"  # условный catalog-service


@app.get("/products/{product_id}/price")
def get_price(product_id: int, user_is_vip: bool = False):
    base_price = 1000.0  # в реальности — запрос в Catalog Service

    if user_is_vip:
        discount = 0.15
    elif base_price > 500:
        discount = 0.05
    else:
        discount = 0.0
    final_price = base_price * (1 - discount)

    return {"product_id": product_id, "final_price": final_price, "discount_applied": discount}