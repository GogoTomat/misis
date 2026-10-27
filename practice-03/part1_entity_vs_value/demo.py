from money import Money
from order import Order

money_a = Money(100, "RUB")
money_b = Money(100, "RUB")
money_c = Money(200, "RUB")

print(money_a == money_b)
print(money_a == money_c)

order_a = Order(order_id=1, status="DRAFT", total=Money(500, "RUB"))
order_b = Order(order_id=1, status="SHIPPED", total=Money(900, "RUB"))
order_c = Order(order_id=2, status="DRAFT", total=Money(500, "RUB"))

print(order_a == order_b)
print(order_a == order_c)
