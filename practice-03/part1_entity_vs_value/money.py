from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(self.currency)
        return Money(self.amount + other.amount, self.currency)
