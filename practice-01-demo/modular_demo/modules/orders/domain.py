"""
Домен модуля orders.

Обращается к payments ТОЛЬКО через его публичный интерфейс
(modules.payments.api), а не через внутренний repository.
Это правило проверяется автоматически — см. .importlinter.

Для демонстрации нарушения на практике: замените импорт ниже на
    from modules.payments.repository import get_payment_status
и вызов на get_payment_status(order_id) — затем перезапустите
`lint-imports`, чтобы увидеть падающий контракт. После демонстрации
верните файл в исходное состояние (например, `git checkout --`,
если каталог версionируется, или скопируйте этот файл заново).
"""
from modules.payments.api import payment_status_for


def order_summary(order_id: int) -> str:
    status = payment_status_for(order_id)
    return f"Order {order_id}: {status}"
