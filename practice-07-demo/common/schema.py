DATABASES = ("orders", "stock", "payments")

DDL = {
    "orders": """
        CREATE TABLE prices (
            product_id text PRIMARY KEY,
            price      int  NOT NULL
        );
        CREATE TABLE orders (
            id               text PRIMARY KEY,
            client_key       text UNIQUE,
            customer         text NOT NULL,
            product_id       text NOT NULL,
            qty              int  NOT NULL,
            amount           int  NOT NULL,
            card             text NOT NULL,
            status           text NOT NULL DEFAULT 'PENDING',
            cancel_requested boolean NOT NULL DEFAULT false,
            created_at       timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE sagas (
            id           text PRIMARY KEY,
            order_id     text NOT NULL REFERENCES orders (id),
            state        text NOT NULL,
            attempts     int  NOT NULL DEFAULT 0,
            next_run_at  timestamptz NOT NULL DEFAULT now(),
            locked_until timestamptz NOT NULL DEFAULT now(),
            deadline     timestamptz NOT NULL,
            version      int  NOT NULL DEFAULT 0,
            data         jsonb NOT NULL DEFAULT '{}'
        );
        CREATE INDEX sagas_runnable ON sagas (next_run_at)
            WHERE state NOT IN ('CONFIRMED', 'CANCELLED', 'NEEDS_ATTENTION');
        CREATE TABLE saga_log (
            id      bigserial PRIMARY KEY,
            saga_id text NOT NULL,
            at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            event   text NOT NULL
        );
    """,
    "stock": """
        CREATE TABLE products (
            id        text PRIMARY KEY,
            name      text NOT NULL,
            available int  NOT NULL CHECK (available >= 0)
        );
        CREATE TABLE reservations (
            id         bigserial PRIMARY KEY,
            saga_id    text NOT NULL,
            product_id text NOT NULL REFERENCES products (id),
            qty        int  NOT NULL,
            status     text NOT NULL,
            expires_at timestamptz NOT NULL
        );
        CREATE INDEX ON reservations (saga_id);
        CREATE TABLE processed (
            key        text PRIMARY KEY,
            status     text NOT NULL,
            response   jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """,
    "payments": """
        CREATE TABLE cards (
            card  text PRIMARY KEY,
            limit_amount int NOT NULL
        );
        CREATE TABLE payments (
            id      text PRIMARY KEY,
            saga_id text NOT NULL,
            card    text NOT NULL,
            amount  int  NOT NULL,
            status  text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ON payments (saga_id);
        CREATE TABLE processed (
            key        text PRIMARY KEY,
            status     text NOT NULL,
            response   jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """,
}

PRODUCTS = [("book", "Книга", 10, 1200), ("lamp", "Лампа", 1, 3500), ("phone", "Телефон", 5, 30000)]
CARDS = [("4111-1111-1111-1111", 1_000_000), ("4000-0000-0000-0002", 0)]
GOOD_CARD = CARDS[0][0]
BAD_CARD = CARDS[1][0]
