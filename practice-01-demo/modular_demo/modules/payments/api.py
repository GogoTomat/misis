"""
Публичный интерфейс модуля payments.

Единственная точка входа, через которую другие модули (например,
orders) могут получать статус платежа.
"""
from modules.payments.repository import get_payment_status


def payment_status_for(order_id: int) -> str:
    return get_payment_status(order_id)
