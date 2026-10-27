"""Atomicity in action: a failed bank transfer leaves no half-finished state.

Run:  python examples/acid_demo.py
"""

import sqlite3


def open_bank() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE accounts ("
        " id INTEGER PRIMARY KEY,"
        " owner TEXT NOT NULL,"
        " balance INTEGER NOT NULL CHECK (balance >= 0))"
    )
    conn.executemany(
        "INSERT INTO accounts (id, owner, balance) VALUES (?, ?, ?)",
        [(1, "Asha", 500), (2, "Bikram", 100)],
    )
    conn.commit()
    return conn


def transfer(conn: sqlite3.Connection, src: int, dst: int, amount: int) -> bool:
    """Move money between accounts. Both updates happen or neither does."""
    try:
        with conn:  # BEGIN ... COMMIT, or ROLLBACK if anything raises
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, src))
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, dst))
        return True
    except sqlite3.IntegrityError:  # the CHECK constraint fired: overdraft
        return False


def balances(conn: sqlite3.Connection) -> dict[str, int]:
    return dict(conn.execute("SELECT owner, balance FROM accounts ORDER BY id"))


def main() -> None:
    conn = open_bank()
    print("start:            ", balances(conn))
    print("transfer 200 ok?  ", transfer(conn, 1, 2, 200), balances(conn))
    print("transfer 9999 ok? ", transfer(conn, 2, 1, 9999), balances(conn))
    total = sum(balances(conn).values())
    print("total money:      ", total, "(unchanged, so Consistency and Atomicity both held)")


if __name__ == "__main__":
    main()
