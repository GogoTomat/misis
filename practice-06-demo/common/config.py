import os

HOST = os.environ.get("PG_HOST", "127.0.0.1")
PRIMARY_PORT = int(os.environ.get("PG_PRIMARY_PORT", "5432"))
REPLICA_PORT = int(os.environ.get("PG_REPLICA_PORT", "5433"))
ADMIN_USER = os.environ.get("PG_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("PG_ADMIN_PASSWORD", "admin")

SERVICES = ["orders", "catalog", "users"]


def dsn(user: str, password: str, database: str, port: int = PRIMARY_PORT) -> str:
    return f"postgresql://{user}:{password}@{HOST}:{port}/{database}"


def admin_dsn(database: str = "postgres") -> str:
    return dsn(ADMIN_USER, ADMIN_PASSWORD, database)


def service_dsn(service: str, database: str | None = None, port: int = PRIMARY_PORT) -> str:
    user = f"{service}_svc"
    return dsn(user, user, database or service, port)
