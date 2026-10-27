# practice-01-demo

Код для практики 1 курса «Проектирование сервисных приложений»: три живых
демо, иллюстрирующих понятия из лекции 1 на работающем коде.

1. **Прямой доступ к чужой БД vs вызов через API** (`orders_service_bad` / `orders_service_good`)
2. **Границы модуля, закреплённые инструментом** (`modular_demo`, import-linter)
3. **Каскадный отказ без таймаута** (`orders_service_cascade` + `payments_service`)

Весь код учебный и написан специально для демонстрации — не для боевого использования.

---

## 1. Требования

- Python 3.10 или новее
- pip

Проверить версию:
```bash
python3 --version
```

## 2. Установка

Из корня проекта:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Устанавливаются: `fastapi`, `uvicorn`, `requests`, `import-linter`.

Дальше все команды выполняются из корня проекта (`practice-01-demo/`),
с активированным `.venv`, если вы его создавали.

---

## 3. Демо 1 — прямой доступ к БД vs API

### 3.1 Плохой вариант

В одном терминале:
```bash
uvicorn users_service.main:app --port 8001
```

Во втором терминале:
```bash
uvicorn orders_service_bad.main:app --port 8002
```

В третьем терминале — проверка:
```bash
curl -X POST "http://localhost:8002/orders?user_id=1&item=Laptop"
```
Ожидаемый ответ:
```json
{"item":"Laptop","user_email":"anna@example.com"}
```

`orders_service_bad` читает таблицу `users` напрямую из того же файла
`shared.db`, который создаёт и наполняет `users_service` — в этом и
есть демонстрируемый антипаттерн.

Чтобы показать, как это ломается при смене схемы (опционально, для
живой демонстрации на паре):
```bash
sqlite3 shared.db "ALTER TABLE users RENAME COLUMN email TO email_address;"
curl -X POST "http://localhost:8002/orders?user_id=1&item=Laptop"   # упадёт
sqlite3 shared.db "ALTER TABLE users RENAME COLUMN email_address TO email;"  # вернуть как было
```

### 3.2 Хороший вариант

Остановите `orders_service_bad` (Ctrl+C) и запустите вместо него:
```bash
uvicorn orders_service_good.main:app --port 8002
```

Тот же запрос — тот же результат, но теперь `orders_service_good` не
знает вообще ничего о структуре базы Users, а только вызывает её HTTP API:
```bash
curl -X POST "http://localhost:8002/orders?user_id=1&item=Laptop"
```

---

## 4. Демо 2 — import-linter

Перейдите в подпроект:
```bash
cd modular_demo
```

Запустите проверку на чистом коде:
```bash
lint-imports
```
Ожидаемый вывод: `Contracts: 1 kept, 0 broken.`

Теперь откройте `modules/orders/domain.py` и замените:
```python
from modules.payments.api import payment_status_for

def order_summary(order_id: int) -> str:
    status = payment_status_for(order_id)
    return f"Order {order_id}: {status}"
```
на нарушающую границу версию:
```python
from modules.payments.repository import get_payment_status

def order_summary(order_id: int) -> str:
    status = get_payment_status(order_id)
    return f"Order {order_id}: {status}"
```

Запустите снова:
```bash
lint-imports
```
Теперь вывод будет содержать `Contracts: 0 kept, 1 broken.` с описанием
нарушенного контракта — именно это стоит показать вживую на паре.

После демонстрации верните `modules/orders/domain.py` в исходный вид
(файл выше, «на чистом коде»), прежде чем показывать что-то ещё.

Вернуться в корень проекта:
```bash
cd ..
```

---

## 5. Демо 3 — каскадный отказ без таймаута

Запустите все три сервиса в отдельных терминалах:
```bash
uvicorn users_service.main:app --port 8001
uvicorn payments_service.main:app --port 8003
uvicorn orders_service_cascade.main:app --port 8002
```

Проверка в обычном режиме:
```bash
curl -X POST "http://localhost:8002/orders?user_id=1&item=Laptop&amount=999.99"
```
Отвечает мгновенно.

Теперь остановите `payments_service` (Ctrl+C) и перезапустите его в
«зависающем» режиме:
```bash
SLOW=1 uvicorn payments_service.main:app --port 8003
```

Повторите запрос — терминал зависнет на 30 секунд, потому что
`orders_service_cascade` вызывает Payments без `timeout`:
```bash
curl -X POST "http://localhost:8002/orders?user_id=1&item=Laptop&amount=999.99"
```

Длительность зависания настраивается переменной окружения
`SLEEP_SECONDS` (по умолчанию 30) — например, для более короткой
демонстрации на паре:
```bash
SLOW=1 SLEEP_SECONDS=10 uvicorn payments_service.main:app --port 8003
```

После демонстрации не забудьте перезапустить `payments_service` без
`SLOW=1`, если планируете использовать демо повторно.

---

## 6. Сброс состояния между запусками

Перед повторным использованием на следующей паре:

```bash
rm -f shared.db                 # users_service создаст файл заново при старте
git checkout -- modular_demo/modules/orders/domain.py   # если каталог версionируется,
                                                          # иначе восстановите файл вручную
                                                          # по содержимому из раздела 4 этого README
```

Также убедитесь, что ни один процесс `uvicorn` не остался запущенным в
фоне (`SLOW=1` в частности) — например, через `pkill -f uvicorn` перед
следующим запуском.

---

## 7. Структура проекта

```
practice-01-demo/
  requirements.txt
  users_service/main.py            # владеет таблицей users в shared.db
  orders_service_bad/main.py       # антипаттерн: прямой доступ к чужой БД
  orders_service_good/main.py      # правильно: доступ через API
  orders_service_cascade/main.py   # без таймаута — для демо каскадного отказа
  payments_service/main.py         # умеет "зависать" через SLOW=1
  modular_demo/
    .importlinter                  # контракт границы модулей
    modules/
      orders/domain.py
      payments/repository.py       # внутренний слой — импортировать нельзя
      payments/api.py              # публичный интерфейс — импортировать можно
```
