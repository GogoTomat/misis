import os

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "admin")
PG_PASSWORD = os.getenv("PG_PASSWORD", "admin")

ORDERS_URL = "http://127.0.0.1:8101"
STOCK_URL = "http://127.0.0.1:8102"
PAYMENTS_URL = "http://127.0.0.1:8103"


def dsn(database: str) -> str:
    return f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{database}"
