import time


class NotificationsService:
    def send_confirmation(self, user_id: int, order_id: int) -> None:
        print(f"  [Notifications] готовим письмо для user={user_id}...")
        time.sleep(1.0)  # имитация похода на внешний почтовый сервер
        print(f"  [Notifications] письмо о заказе #{order_id} отправлено")


class OrdersService:
    def __init__(self, notifications: NotificationsService):
        self.notifications = notifications

    def place_order(self, user_id: int, item: str) -> int:
        order_id = 42  # упрощённо, без реальной БД для демо
        print(f"[Orders] заказ #{order_id} создан ({item})")

        self.notifications.send_confirmation(user_id, order_id)

        print(f"[Orders] отвечаем клиенту: заказ #{order_id} оформлен")
        return order_id


if __name__ == "__main__":
    orders = OrdersService(notifications=NotificationsService())
    start = time.time()
    orders.place_order(user_id=1, item="Laptop")
    print(f"\nВремя ответа клиенту: {time.time() - start:.2f} сек")
    print("^ клиент ждал, пока письмо реально отправится — это и есть цена синхронности")
