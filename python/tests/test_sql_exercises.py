"""Runs every reference solution in sql/solutions.sql against the seed data.

Expected results live in sql/expected.json and were checked by hand against seed.sql.
"""

import json
import re
import sqlite3
import unittest
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def load_solutions() -> dict[str, str]:
    text = (SQL_DIR / "solutions.sql").read_text(encoding="utf-8")
    parts = re.split(r"^-- (Q\d+)\s*$", text, flags=re.MULTILINE)
    # parts = [preamble, "Q1", body, "Q2", body, ...]
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def open_shop() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((SQL_DIR / "seed.sql").read_text(encoding="utf-8"))
    return conn


class SqlExerciseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = open_shop()
        cls.solutions = load_solutions()
        cls.expected = json.loads((SQL_DIR / "expected.json").read_text(encoding="utf-8"))

    def test_every_exercise_has_a_solution_and_expected_result(self):
        self.assertEqual(set(self.solutions), set(self.expected))
        self.assertEqual(len(self.solutions), 15)

    def test_solutions_produce_expected_rows(self):
        for qid in sorted(self.solutions, key=lambda q: int(q[1:])):
            with self.subTest(qid=qid):
                rows = [list(r) for r in self.conn.execute(self.solutions[qid]).fetchall()]
                self.assertEqual(rows, self.expected[qid])

    def test_foreign_keys_are_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO orders VALUES (99, 12345, '2026-06-01', 'paid')")

    def test_check_constraints_are_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO products VALUES (99, 'Bad', 'book', -1)")


class ExampleTests(unittest.TestCase):
    def test_acid_demo_rolls_back_failed_transfer(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
        import acid_demo

        conn = acid_demo.open_bank()
        self.assertTrue(acid_demo.transfer(conn, 1, 2, 200))
        self.assertEqual(acid_demo.balances(conn), {"Asha": 300, "Bikram": 300})
        self.assertFalse(acid_demo.transfer(conn, 2, 1, 9999))
        self.assertEqual(acid_demo.balances(conn), {"Asha": 300, "Bikram": 300})

    def test_index_demo_changes_the_plan(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
        import index_demo

        conn = index_demo.build(rows=5000, users=200)
        self.assertIn("SCAN", index_demo.plan(conn))
        conn.execute("CREATE INDEX idx_events_user ON events(user_id)")
        self.assertIn("SEARCH", index_demo.plan(conn))
        self.assertIn("idx_events_user", index_demo.plan(conn))


if __name__ == "__main__":
    unittest.main()
