from payment_result import PaymentResult


class PaymentGatewayACL:
    def translate(self, raw: dict) -> PaymentResult:
        return PaymentResult(
            is_successful=raw["stCode"] == 200,
            transaction_id=raw["transactionRefId"],
        )
