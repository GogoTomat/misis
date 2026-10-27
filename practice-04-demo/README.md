# practice-04-demo

Код для практики 4 курса «Проектирование сервисных приложений»: шесть демо, иллюстрирующих технологии и практики из лекции 4 на реально работающем коде.

1. **REST** (`part1_rest/`) — статус-коды, idempotent PUT/DELETE vs не-idempotent POST
2. **gRPC** (`part2_grpc/`) — `.proto`-контракт, unary и server streaming
3. **GraphQL** (`part3_graphql/`) — проблема N+1 и её решение батчингом
4. **Пагинация** (`part4_pagination/`) — offset vs cursor на реальных данных
5. **Идемпотентность** (`part5_idempotency/`) — двойное списание vs Idempotency-Key
6. **OpenAPI** (`part6_openapi/`) — спецификация + автосгенерированный Swagger UI

Все демо уже написаны и протестированы — на паре их нужно только запустить и обсудить вывод, не писать код с нуля.

---

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10+.

---

## Часть 1 — REST

```bash
cd part1_rest
uvicorn main:app --port 8001
```

В другом терминале:
```bash
python3 demo_requests.py
```

Показывает по порядку: `201 + Location` при создании, `404` для несуществующего заказа, идемпотентный `PUT` (два одинаковых вызова — два одинаковых ответа), неидемпотентный `POST` (два вызова — два разных id), `422` при попытке нарушить инвариант (снять статус SHIPPED), идемпотентный `DELETE`.

Бонус — интерактивная документация уже включена в FastAPI: откройте `http://localhost:8001/docs` в браузере, пока сервис запущен.

---

## Часть 2 — gRPC

Код уже сгенерирован из `order.proto` (файлы `order_pb2.py` и `order_pb2_grpc.py`). Если нужно перегенерировать вручную:
```bash
cd part2_grpc
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. order.proto
```

Запуск:
```bash
cd part2_grpc
python3 server.py
```

В другом терминале:
```bash
python3 client_unary.py       # один запрос — один ответ
python3 client_streaming.py   # один запрос — поток из 4 обновлений статуса с интервалом в секунду
```

---

## Часть 3 — GraphQL

Здесь не нужен отдельный сервер — оба демо выполняют GraphQL-запрос прямо в скрипте через `schema.execute(...)`.

```bash
cd part3_graphql
python3 demo_n1.py          # наивные резолверы: 100 заказов -> 101 обращение к "БД"
python3 demo_dataloader.py  # батчинг: те же 100 заказов -> всего 2 обращения к "БД"
```

---

## Часть 4 — Пагинация

```bash
cd part4_pagination
python3 offset_demo.py   # страница 2 "плывёт" после удаления записи на странице 1
python3 cursor_demo.py   # страница 2 остаётся стабильной при том же удалении
```

Каждый скрипт создаёт свою SQLite-базу с нуля при запуске — предыдущие результаты не мешают следующим прогонам.

---

## Часть 5 — Идемпотентность

```bash
cd part5_idempotency
uvicorn service:app --port 8002
```

В другом терминале:
```bash
python3 demo.py
```

Показывает два сценария подряд: без `Idempotency-Key` повторный вызов создаёт второе, лишнее списание; с `Idempotency-Key` повторный вызов возвращает тот же самый, уже сохранённый результат первого списания.

---

## Часть 6 — OpenAPI

`orders-api.yaml` — спецификация для API из части 1. Можно открыть на [editor.swagger.io](https://editor.swagger.io) и вставить содержимое файла, чтобы увидеть интерактивную документацию и попробовать вызвать эндпоинты прямо оттуда.

Также, пока запущен сервис из части 1 (`uvicorn main:app --port 8001`), FastAPI сам генерирует аналогичную спецификацию на лету — она доступна по адресу `http://localhost:8001/openapi.json`, а интерактивный UI — на `http://localhost:8001/docs`.

---

## Сброс состояния между запусками

Части 1, 2 и 5 хранят данные в памяти процесса — просто перезапустите соответствующий сервер (`Ctrl+C`, затем снова `uvicorn ...` или `python3 server.py`), и состояние очистится само. Часть 4 создаёт свежую SQLite-базу при каждом запуске скрипта. Часть 3 не имеет постоянного состояния между запусками вообще.

---

## Структура проекта

```
practice-04-demo/
  requirements.txt
  part1_rest/
    main.py
    demo_requests.py
  part2_grpc/
    order.proto
    order_pb2.py
    order_pb2_grpc.py
    server.py
    client_unary.py
    client_streaming.py
  part3_graphql/
    schema.py
    demo_n1.py
    demo_dataloader.py
  part4_pagination/
    offset_demo.py
    cursor_demo.py
  part5_idempotency/
    service.py
    demo.py
  part6_openapi/
    orders-api.yaml
```
