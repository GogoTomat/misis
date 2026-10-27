class PaymentResult:
    def __init__(self, is_successful: bool, transaction_id: str):
        self.is_successful = is_successful
        self.transaction_id = transaction_id
