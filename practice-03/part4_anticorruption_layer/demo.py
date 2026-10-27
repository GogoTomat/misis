from legacy_payment_gateway import charge
from acl import PaymentGatewayACL

acl = PaymentGatewayACL()
raw_response = charge(amount=999)
result = acl.translate(raw_response)

print(result.is_successful)
print(result.transaction_id)
