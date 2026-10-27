# practice-03-demo

Код для практики 3 курса «Проектирование сервисных приложений»: четыре небольших демо, иллюстрирующих понятия Domain-Driven Design из лекции 3 на работающем коде.

1. **Entity vs Value Object** (`part1_entity_vs_value/`)
2. **Aggregate с защищённым инвариантом** (`part2_aggregate/`)
3. **Bounded Context — одно слово, разные модели** (`part3_bounded_context/`)
4. **Anticorruption Layer** (`part4_anticorruption_layer/`)

Код не содержит комментариев — назначение каждого файла и класса объясняется в отдельном документе `Лекция_03_Описание_кода.md`, который идёт вместе с этим проектом.

---

## Требования

- Python 3.10 или новее, больше ничего — весь проект на стандартной библиотеке, зависимостей нет.

Проверить версию:
```bash
python3 --version
```

---

## Часть 1 — Entity vs Value Object

```bash
cd part1_entity_vs_value
python3 demo.py
```

Ожидаемый вывод:
```
True
False
True
False
```

Первые две строки — сравнение двух `Money` (Value Object): одинаковые суммы равны, разные — нет.
Вторые две строки — сравнение двух `Order` (Entity): один и тот же `order_id` при разных `status`/`total` всё равно даёт равенство; разный `order_id` — нет.

---

## Часть 2 — Aggregate с защищённым инвариантом

Сначала — защищённый путь:
```bash
cd part2_aggregate
python3 demo_protected.py
```
Ожидаемо падает с `ValueError: SHIPPED` на последней строке — `add_line` не даёт добавить товар в уже отправленный заказ.

Теперь — обход границы агрегата в обход `add_line`:
```bash
python3 demo_bypass.py
```
Ожидаемый вывод:
```
SHIPPED
1005
```
Заказ формально в статусе `SHIPPED`, но его сумма всё равно изменилась — инвариант нарушен, потому что код обратился напрямую к `order._lines`, в обход единственной официальной точки входа `add_line`.

---

## Часть 3 — Bounded Context

```bash
cd part3_bounded_context
python3 demo.py
```
Ожидаемый вывод:
```
Наушники
0.3
5000
```

Три класса `Product` — в `catalog_context/`, `shipping_context/`, `pricing_context/` — с одним и тем же именем, но полностью разным набором полей. Файл `god_object_antipattern.py` показывает, как выглядел бы неправильный вариант — один класс `Product` сразу со всеми десятью полями из всех трёх контекстов; этот файл не запускается отдельно, он только для показа на экране.

---

## Часть 4 — Anticorruption Layer

```bash
cd part4_anticorruption_layer
python3 demo.py
```
Ожидаемый вывод:
```
True
TXN-88213-RU
```

`legacy_payment_gateway.py` симулирует чужой формат ответа с неудобными именами полей (`stCode`, `transactionRefId`). `acl.py` — единственное место в проекте, которое их видит и переводит в чистый `PaymentResult`.

---

## Структура проекта

```
practice-03-demo/
  part1_entity_vs_value/
    money.py
    order.py
    demo.py
  part2_aggregate/
    order_line.py
    order.py
    demo_protected.py
    demo_bypass.py
  part3_bounded_context/
    catalog_context/product.py
    shipping_context/product.py
    pricing_context/product.py
    demo.py
    god_object_antipattern.py
  part4_anticorruption_layer/
    legacy_payment_gateway.py
    payment_result.py
    acl.py
    demo.py
```
