import asyncio

from fastapi import FastAPI, Query

app = FastAPI(title="users")

USERS = {i: {"id": i, "name": f"Пользователь {i}", "email": f"user{i}@example.com"} for i in range(1, 201)}
LATENCY = 0.02
stats = {"single": 0, "batch": 0, "in_flight": 0, "max_in_flight": 0}


async def simulate_work() -> None:
    stats["in_flight"] += 1
    stats["max_in_flight"] = max(stats["max_in_flight"], stats["in_flight"])
    try:
        await asyncio.sleep(LATENCY)
    finally:
        stats["in_flight"] -= 1


@app.get("/ping")
async def ping():
    return {"ok": True}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    stats["single"] += 1
    await simulate_work()
    return USERS[user_id]


@app.get("/users")
async def get_users(ids: str = Query(...)):
    stats["batch"] += 1
    await simulate_work()
    wanted = sorted({int(x) for x in ids.split(",")})
    return [USERS[i] for i in wanted]


@app.get("/admin/stats")
async def get_stats():
    return stats


@app.post("/admin/reset")
async def reset():
    stats.update(single=0, batch=0, in_flight=0, max_in_flight=0)
    return stats
