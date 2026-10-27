import graphene

DB_CALLS = {"count": 0}

users_db = {i: {"id": i, "name": f"User {i}"} for i in range(1, 6)}
orders_db = [{"id": i, "status": "DRAFT", "user_id": (i % 5) + 1} for i in range(1, 101)]

_user_cache: dict[int, dict] = {}


class User(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()


class OrderNaive(graphene.ObjectType):
    id = graphene.Int()
    status = graphene.String()
    user = graphene.Field(User)

    def resolve_user(order, info):
        DB_CALLS["count"] += 1
        user = users_db[order["user_id"]]
        return User(id=user["id"], name=user["name"])


class QueryNaive(graphene.ObjectType):
    orders = graphene.List(OrderNaive)

    def resolve_orders(root, info):
        DB_CALLS["count"] += 1
        return orders_db


schema_naive = graphene.Schema(query=QueryNaive)


class OrderBatched(graphene.ObjectType):
    id = graphene.Int()
    status = graphene.String()
    user = graphene.Field(User)

    def resolve_user(order, info):
        user = _user_cache[order["user_id"]]
        return User(id=user["id"], name=user["name"])


class QueryBatched(graphene.ObjectType):
    orders = graphene.List(OrderBatched)

    def resolve_orders(root, info):
        DB_CALLS["count"] += 1
        needed_ids = {o["user_id"] for o in orders_db}
        DB_CALLS["count"] += 1
        for uid in needed_ids:
            _user_cache[uid] = users_db[uid]
        return orders_db


schema_batched = graphene.Schema(query=QueryBatched)
