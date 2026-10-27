import requests

BASE = "http://localhost:8002"


def main():
    requests.post(f"{BASE}/reset")

    print("=== БЕЗ идемпотентности: клиент дважды повторяет запрос после «таймаута» ===")
    r1 = requests.post(f"{BASE}/charge-unsafe", json={"amount": 5000, "card_id": "card_1"})
    r2 = requests.post(f"{BASE}/charge-unsafe", json={"amount": 5000, "card_id": "card_1"})
    print("Первый вызов:", r1.json())
    print("Повтор:      ", r2.json())
    count = requests.get(f"{BASE}/charges-count").json()["total_charges"]
    print(f"Итого списаний в системе: {count}  <-- деньги списаны дважды!\n")

    requests.post(f"{BASE}/reset")

    print("=== С идемпотентностью: тот же сценарий, но с Idempotency-Key ===")
    key = "client-generated-uuid-abc123"
    r1 = requests.post(
        f"{BASE}/charge-safe",
        json={"amount": 5000, "card_id": "card_1"},
        headers={"Idempotency-Key": key},
    )
    r2 = requests.post(
        f"{BASE}/charge-safe",
        json={"amount": 5000, "card_id": "card_1"},
        headers={"Idempotency-Key": key},
    )
    print("Первый вызов:", r1.json())
    print("Повтор:      ", r2.json())
    count = requests.get(f"{BASE}/charges-count").json()["total_charges"]
    print(f"Итого списаний в системе: {count}  <-- ровно одно списание, как и должно быть")
    print(f"transaction_id совпадает: {r1.json()['transaction_id'] == r2.json()['transaction_id']}")


if __name__ == "__main__":
    main()
