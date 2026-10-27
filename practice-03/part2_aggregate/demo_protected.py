from order import Order

order = Order(order_id=1)
order.add_line(product_id=10, quantity=2, price=500)
order.add_line(product_id=11, quantity=1, price=1000)
print(order.total())

order.ship()
order.add_line(product_id=12, quantity=1, price=300)
