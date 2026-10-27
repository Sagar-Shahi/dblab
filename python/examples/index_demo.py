"""See what an index does to a query plan and to query time.

Run:  python examples/index_demo.py
"""

import random
import sqlite3
import time

QUERY = "SELECT COUNT(*) FROM events WHERE user_id = ?"


def build(rows: int = 200_000, users: int = 5_000, seed: int = 7) -> sqlite3.Connection:
    rng = random.Random(seed)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL)")
    conn.executemany(
        "INSERT INTO events (user_id, kind) VALUES (?, ?)",
        ((rng.randrange(users), rng.choice(["view", "click", "buy"])) for _ in range(rows)),
    )
    conn.commit()
    return conn


def plan(conn: sqlite3.Connection) -> str:
    return " / ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + QUERY, (42,)))


def time_lookups(conn: sqlite3.Connection, n: int = 200) -> float:
    start = time.perf_counter()
    for user in range(n):
        conn.execute(QUERY, (user,)).fetchone()
    return time.perf_counter() - start


def main() -> None:
    conn = build()
    print("without index:", plan(conn))
    slow = time_lookups(conn)
    conn.execute("CREATE INDEX idx_events_user ON events(user_id)")
    print("with index:   ", plan(conn))
    fast = time_lookups(conn)
    print(f"200 lookups: {slow:.3f}s -> {fast:.3f}s  ({slow / fast:.0f}x faster)")


if __name__ == "__main__":
    main()
