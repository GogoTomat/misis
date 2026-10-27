import requests

BASE = "http://localhost:8001"


def show(label, response):
    print(f"\n=== {label} ===")
    print(f"Status: {response.status_code}")
    if response.text:
        print(f"Body:   {response.text}")


def main():
    r = requests.post(f"{BASE}/orders", json={"product": "Laptop", "quantity": 1})
    show("POST /orders (создание, 201 + Location)", r)
    print(f"Location header: {r.headers.get('Location')}")
    order_id = r.json()["id"]

    r = requests.get(f"{BASE}/orders/{order_id}")
    show("GET /orders/{id} (успех, 200)", r)

    r = requests.get(f"{BASE}/orders/999999")
    show("GET /orders/999999 (не существует, 404)", r)

    r1 = requests.put(
        f"{BASE}/orders/{order_id}",
        json={"product": "Laptop", "quantity": 2, "status": "DRAFT"},
    )
    r2 = requests.put(
        f"{BASE}/orders/{order_id}",
        json={"product": "Laptop", "quantity": 2, "status": "DRAFT"},
    )
    show("PUT /orders/{id} — первый вызов", r1)
    show("PUT /orders/{id} — второй вызов, тот же результат (idempotent)", r2)

    p1 = requests.post(f"{BASE}/orders", json={"product": "Mouse", "quantity": 1})
    p2 = requests.post(f"{BASE}/orders", json={"product": "Mouse", "quantity": 1})
    show("POST /orders — первый вызов", p1)
    show("POST /orders — второй вызов, НОВЫЙ id (не idempotent)", p2)
    print(f"Первый id: {p1.json()['id']}, второй id: {p2.json()['id']}")

    r = requests.patch(f"{BASE}/orders/{order_id}", json={"status": "SHIPPED"})
    show("PATCH статус -> SHIPPED", r)

    r = requests.patch(f"{BASE}/orders/{order_id}", json={"status": "DRAFT"})
    show("PATCH обратно в DRAFT после SHIPPED (инвариант, 422)", r)

    d1 = requests.delete(f"{BASE}/orders/{p1.json()['id']}")
    d2 = requests.delete(f"{BASE}/orders/{p1.json()['id']}")
    show("DELETE — первый вызов (204)", d1)
    show("DELETE — второй вызов, тот же результат системы (idempotent)", d2)


if __name__ == "__main__":
    main()
