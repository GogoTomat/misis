import asyncio

import uvicorn

from services import orders, payments, reports, stock, users

SERVICES = [
    ("users", users.app, 8001),
    ("stock", stock.app, 8002),
    ("orders", orders.app, 8003),
    ("payments", payments.app, 8004),
    ("reports", reports.app, 8005),
]


async def main() -> None:
    servers = []
    for name, app, port in SERVICES:
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        servers.append(uvicorn.Server(config))
        print(f"{name:<9} http://127.0.0.1:{port}")
    print("Все сервисы запущены. Остановка — Ctrl+C.\n")
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
