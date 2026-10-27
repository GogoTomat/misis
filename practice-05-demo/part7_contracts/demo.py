from pydantic import ValidationError

from consumers import StrictOrderPlaced, TolerantOrderPlaced, billing_handler, notification_handler
from events import ORDER_PLACED_V1, ORDER_PLACED_V2_NEW_FIELD, ORDER_PLACED_V3_RENAMED


def try_consume(title: str, model, event: dict) -> None:
    try:
        model.model_validate(event)
        print(f"   {title:<10} принял")
    except ValidationError as error:
        problems = ", ".join(f"{e['loc'][0]}: {e['type']}" for e in error.errors())
        print(f"   {title:<10} упал — {problems}")


def main() -> None:
    cases = [
        ("Шаг 1. Исходная версия события", ORDER_PLACED_V1),
        ("Шаг 2. Производитель добавил поле promo_code", ORDER_PLACED_V2_NEW_FIELD),
        ("Шаг 3. Производитель переименовал customer_email в email", ORDER_PLACED_V3_RENAMED),
    ]
    for title, event in cases:
        print(title)
        try_consume("strict", StrictOrderPlaced, event)
        try_consume("tolerant", TolerantOrderPlaced, event)
        print()

    print("Шаг 4. Формат совпадает, смысл — нет (total в копейках)")
    print(f"   {billing_handler(ORDER_PLACED_V1)}")
    print(f"   {notification_handler(ORDER_PLACED_V1)}")


if __name__ == "__main__":
    main()
