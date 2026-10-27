from order import Order
from order_line import OrderLine

order = Order(order_id=1)
order.add_line(product_id=10, quantity=2, price=500)
order.ship()

order._lines.append(OrderLine(product_id=99, quantity=5, price=1))

print(order.status)
print(order.total())
