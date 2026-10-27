import time
from event_bus import EventBus

bus = EventBus()


class NotificationsService:
    def handle_order_created(self, event: dict) -> None:
        print(f"  [Notifications] получили событие, готовим письмо для user={event['user_id']}...")
        time.sleep(1.0)
        print(f"  [Notifications] письмо о заказе #{event['order_id']} отправлено")


class OrdersService:
    def __init__(self, bus: EventBus):
        self.bus = bus

    def place_order(self, user_id: int, item: str) -> int:
        order_id = 42
        print(f"[Orders] заказ #{order_id} создан ({item})")

        # Orders просто публикует факт — и НЕ ждёт, пока письмо уйдёт
        self.bus.publish("OrderCreated", {"order_id": order_id, "user_id": user_id})

        print(f"[Orders] отвечаем клиенту: заказ #{order_id} оформлен")
        return order_id


notifications = NotificationsService()
bus.subscribe("OrderCreated", notifications.handle_order_created)

if __name__ == "__main__":
    orders = OrdersService(bus=bus)
    start = time.time()
    orders.place_order(user_id=1, item="Laptop")
    print(f"\nВремя ответа клиенту: {time.time() - start:.2f} сек")
    print("^ Orders ответил мгновенно, письмо 'досылается' независимо")
    time.sleep(1.5)
