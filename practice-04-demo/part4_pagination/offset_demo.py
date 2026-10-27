import sqlite3

DB_PATH = "offset_demo.db"


def setup():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS orders")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, product TEXT)")
    for i in range(1, 26):
        conn.execute("INSERT INTO orders (id, product) VALUES (?, ?)", (i, f"Product {i}"))
    conn.commit()
    return conn


def fetch_page(conn, limit, offset):
    rows = conn.execute(
        "SELECT id, product FROM orders ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    return [row[0] for row in rows]


def main():
    conn = setup()

    page1 = fetch_page(conn, limit=10, offset=0)
    print("Страница 1 (offset=0, limit=10):", page1)

    print("\n>>> Кто-то удаляет заказ с id=3, пока пользователь листает страницы <<<\n")
    conn.execute("DELETE FROM orders WHERE id = 3")
    conn.commit()

    page2 = fetch_page(conn, limit=10, offset=10)
    print("Страница 2 (offset=10, limit=10):", page2)

    print("\nОжидались бы id 11..20, но из-за удаления одной записи в начале")
    print("вся оставшаяся таблица сдвинулась — фактическая страница 2 отличается")
    print("от ожидаемой, один заказ пропущен или задублирован относительно исходной нумерации.")


if __name__ == "__main__":
    main()
