import json
import sys

import asyncpg

from common.config import PRIMARY_PORT, admin_dsn, service_dsn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def connect_service(service: str, database: str | None = None, port: int = PRIMARY_PORT) -> asyncpg.Connection:
    return await asyncpg.connect(service_dsn(service, database, port))


async def connect_admin(database: str = "postgres") -> asyncpg.Connection:
    return await asyncpg.connect(admin_dsn(database))


def _scan_nodes(plan: dict) -> list[str]:
    nodes = []
    node_type = plan["Node Type"]
    if "Scan" in node_type:
        name = node_type
        if "Index Name" in plan:
            name += f" using {plan['Index Name']}"
        nodes.append(name)
    for child in plan.get("Plans", []):
        nodes.extend(_scan_nodes(child))
    return nodes


async def explain(conn: asyncpg.Connection, sql: str, *args) -> tuple[str, float]:
    for _ in range(2):
        raw = await conn.fetchval(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}", *args)
    data = json.loads(raw)[0]
    return ", ".join(_scan_nodes(data["Plan"])), data["Execution Time"]
