ORDER_PLACED_V1 = {
    "event": "OrderPlaced",
    "order_id": "A-1001",
    "customer_email": "anna@example.com",
    "total": 99990,
}

ORDER_PLACED_V2_NEW_FIELD = {**ORDER_PLACED_V1, "promo_code": "AUTUMN"}

ORDER_PLACED_V3_RENAMED = {
    "event": "OrderPlaced",
    "order_id": "A-1002",
    "email": "boris@example.com",
    "total": 149900,
}
