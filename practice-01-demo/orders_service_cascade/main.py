"""
Orders Service — версия БЕЗ отказоустойчивости, для демо каскадного отказа.

Синхронно вызывает Payments Service БЕЗ timeout. Если Payments
зависнет — зависнет и этот сервис вместе с ним. Специально не
чиним это здесь: таймауты, retry и circuit breaker — тема отдельного
занятия, сегодня достаточно увидеть сам паттерн отказа вживую.
"""
from fastapi import FastAPI
import requests

app = FastAPI(title="Orders Service (без отказоустойчивости)")

USERS_URL = "http://localhost:8001"
PAYMENTS_URL = "http://localhost:8003"


@app.post("/orders")
def create_order(user_id: int, item: str, amount: float):
    user = requests.get(f"{USERS_URL}/users/{user_id}", timeout=5).json()
    # Внимание: у вызова ниже нет timeout — это осознанно, для демонстрации.
    payment = requests.post(
        f"{PAYMENTS_URL}/charge", params={"amount": amount}
    )
    return {"item": item, "user_email": user["email"], "payment": payment.json()}
