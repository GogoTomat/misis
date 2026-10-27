import sqlite3

DB_PATH = "cursor_demo.db"


def setup():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS orders")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, product TEXT)")
    for i in range(1, 26):
        conn.execute("INSERT INTO orders (id, product) VALUES (?, ?)", (i, f"Product {i}"))
    conn.commit()
    return conn


def fetch_page(conn, limit, after_id):
    rows = conn.execute(
        "SELECT id, product FROM orders WHERE id > ? ORDER BY id LIMIT ?", (after_id, limit)
    ).fetchall()
    return [row[0] for row in rows]


def main():
    conn = setup()

    page1 = fetch_page(conn, limit=10, after_id=0)
    print("Страница 1 (cursor=0, limit=10):", page1)
    cursor = page1[-1]
    print("Курсор для следующей страницы:", cursor)

    print("\n>>> Кто-то удаляет заказ с id=3, пока пользователь листает страницы <<<\n")
    conn.execute("DELETE FROM orders WHERE id = 3")
    conn.commit()

    page2 = fetch_page(conn, limit=10, after_id=cursor)
    print("Страница 2 (cursor=%d, limit=10):" % cursor, page2)

    print("\nСтраница 2 по-прежнему содержит ровно id 11..20 — то, что произошло")
    print("на странице 1, никак не влияет на курсор, потому что WHERE id > cursor")
    print("не зависит от числовой позиции записи, только от значения самого курсора.")


if __name__ == "__main__":
    main()
