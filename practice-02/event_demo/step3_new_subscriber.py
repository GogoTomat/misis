import time
from step2_event_driven import bus, OrdersService  # переиспользуем как есть


class AnalyticsService:
    def handle_order_created(self, event: dict) -> None:
        print(f"  [Analytics] учли заказ #{event['order_id']} в статистике продаж")


# Единственная новая строчка во всей системе:
bus.subscribe("OrderCreated", AnalyticsService().handle_order_created)

if __name__ == "__main__":
    orders = OrdersService(bus=bus)
    orders.place_order(user_id=1, item="Laptop")
    time.sleep(1.5)  # даём фоновым обработчикам время допечатать лог
    print("\n^ Notifications И Analytics оба отреагировали."
          " Orders как был, так и остался нетронутым.")
