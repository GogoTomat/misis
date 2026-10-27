import asyncio

import uvicorn

from common.log import log
from services import orders, payments, stock

SERVICES = [("orders", orders.app, 8101), ("stock", stock.app, 8102), ("payments", payments.app, 8103)]


async def main() -> None:
    servers = []
    for name, app, port in SERVICES:
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        servers.append(uvicorn.Server(config))
        log(name, f"http://127.0.0.1:{port}")
    log("services", "все сервисы запущены, остановка — Ctrl+C")
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
