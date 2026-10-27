from dataclasses import dataclass, field


@dataclass
class Order:
    user_id: int
    item: str
    id: int | None = None
    status: str = "created"

    def validate(self) -> None:
        """Бизнес-правило живёт внутри сущности, а не в use case или контроллере."""
        if not self.item:
            raise ValueError("item is required")

    @property
    def status_label(self) -> str:
        return "Обрабатывается" if self.status == "created" else self.status
