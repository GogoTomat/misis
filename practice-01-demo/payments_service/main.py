"""
Payments Service.

По умолчанию отвечает мгновенно. Если задать переменную окружения
SLOW=1, каждый запрос к /charge будет "зависать" на SLEEP_SECONDS
секунд (по умолчанию 30) — это и есть симуляция зависшего сервиса
для демонстрации каскадного отказа.
"""
import os
import time

from fastapi import FastAPI

app = FastAPI(title="Payments Service")

SLOW = os.environ.get("SLOW") == "1"
SLEEP_SECONDS = float(os.environ.get("SLEEP_SECONDS", "30"))


@app.post("/charge")
def charge(amount: float):
    if SLOW:
        time.sleep(SLEEP_SECONDS)
    return {"status": "ok", "amount": amount}
