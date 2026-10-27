"""
Orders Service — ХОРОШИЙ вариант.

Не знает ничего о внутреннем устройстве базы данных Users —
обращается к ней только через её публичный HTTP API.
"""
from fastapi import FastAPI
import requests

app = FastAPI(title="Orders Service (GOOD: через API)")

USERS_SERVICE_URL = "http://localhost:8001"


@app.post("/orders")
def create_order(user_id: int, item: str):
    resp = requests.get(f"{USERS_SERVICE_URL}/users/{user_id}", timeout=5)
    if resp.status_code != 200:
        return {"error": "user not found"}
    user = resp.json()
    return {"item": item, "user_email": user["email"]}
