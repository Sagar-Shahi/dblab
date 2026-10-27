import os
import tempfile
import unittest

from dblab import Database, DBError


def make_db() -> Database:
    db = Database()
    db.execute("CREATE TABLE books (id INT PRIMARY KEY, title TEXT, price REAL, lang TEXT)")
    db.execute(
        "INSERT INTO books VALUES "
        "(1, 'Python Crash Notes', 12.5, 'python'), "
        "(2, 'Java Handbook', 18, 'java'), "
        "(3, 'C++ Primer Lite', 20, 'cpp'), "
        "(4, 'SQL Cookbook', 15, 'sql')"
    )
    return db


class SelectTests(unittest.TestCase):
    def setUp(self):
        self.db = make_db()

    def test_select_star(self):
        self.assertEqual(len(self.db.execute("SELECT * FROM books")), 4)

    def test_projection_and_where(self):
        rows = self.db.execute("select title from books where lang = 'java'")
        self.assertEqual(rows, [{"title": "Java Handbook"}])

    def test_and_or_parentheses(self):
        rows = self.db.execute(
            "SELECT id FROM books WHERE (lang = 'java' OR lang = 'sql') AND price > 15 ORDER BY id"
        )
        self.assertEqual(rows, [{"id": 2}])

    def test_order_by_desc_and_limit(self):
        rows = self.db.execute("SELECT id FROM books ORDER BY price DESC LIMIT 2")
        self.assertEqual([r["id"] for r in rows], [3, 2])

    def test_count(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM books WHERE price >= 15"), [{"count": 3}])

    def test_int_stored_in_real_column_becomes_float(self):
        self.assertEqual(self.db.execute("SELECT price FROM books WHERE id = 2"), [{"price": 18.0}])

    def test_negative_numbers(self):
        self.db.execute("INSERT INTO books VALUES (5, 'Refund', -3.5, 'none')")
        self.assertEqual(self.db.execute("SELECT id FROM books WHERE price < 0"), [{"id": 5}])

    def test_string_with_quote_and_semicolon(self):
        self.db.execute("INSERT INTO books VALUES (6, 'It''s; fine', 1, 'x')")
        rows = self.db.execute("SELECT title FROM books WHERE id = 6;")
        self.assertEqual(rows, [{"title": "It's; fine"}])

    def test_null_handling(self):
        self.db.execute("INSERT INTO books (id, title) VALUES (7, 'Draft')")
        self.assertEqual(self.db.execute("SELECT id FROM books WHERE price IS NULL"), [{"id": 7}])
        self.assertEqual(len(self.db.execute("SELECT id FROM books WHERE price IS NOT NULL")), 4)
        # NULL never equals anything, not even NULL.
        self.assertEqual(self.db.execute("SELECT id FROM books WHERE price = 12.5 OR price <> 12.5 ORDER BY id")[-1], {"id": 4})


class WriteTests(unittest.TestCase):
    def setUp(self):
        self.db = make_db()

    def test_update(self):
        self.assertEqual(self.db.execute("UPDATE books SET price = 10 WHERE lang = 'java'"), 1)
        self.assertEqual(self.db.execute("SELECT price FROM books WHERE id = 2"), [{"price": 10.0}])

    def test_delete(self):
        self.assertEqual(self.db.execute("DELETE FROM books WHERE price < 16"), 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM books"), [{"count": 2}])

    def test_deleted_key_can_be_reused(self):
        self.db.execute("DELETE FROM books WHERE id = 1")
        self.db.execute("INSERT INTO books VALUES (1, 'Again', 1, 'x')")

    def test_duplicate_primary_key_rejected(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO books VALUES (1, 'Dup', 1, 'x')")

    def test_multirow_insert_is_atomic(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO books VALUES (10, 'ok', 1, 'x'), (1, 'dup', 1, 'x')")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM books"), [{"count": 4}])

    def test_update_cannot_break_primary_key(self):
        with self.assertRaises(DBError):
            self.db.execute("UPDATE books SET id = 1 WHERE id = 2")
        self.assertEqual(self.db.execute("SELECT id FROM books WHERE title = 'Java Handbook'"), [{"id": 2}])

    def test_type_mismatch_rejected(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO books VALUES (9, 'x', 'cheap', 'x')")

    def test_trailing_garbage_does_not_mutate(self):
        with self.assertRaises(DBError):
            self.db.execute("INSERT INTO books VALUES (9, 'x', 1, 'x') garbage")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM books"), [{"count": 4}])

    def test_unknown_names(self):
        for sql in ("SELECT nope FROM books", "SELECT * FROM nope", "SELECT * FROM books WHERE nope = 1"):
            with self.subTest(sql=sql), self.assertRaises(DBError):
                self.db.execute(sql)

    def test_drop_table(self):
        self.db.execute("DROP TABLE books")
        self.assertEqual(self.db.table_names(), [])

    def test_executescript(self):
        db = Database()
        results = db.executescript("CREATE TABLE t (a INT); INSERT INTO t VALUES (1), (2); SELECT * FROM t;")
        self.assertEqual(results[-1], [{"a": 1}, {"a": 2}])


class DurabilityTests(unittest.TestCase):
    def test_state_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "app.wal")
            db = Database(path)
            db.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
            db.execute("INSERT INTO t VALUES (1, 'a'), (2, 'b')")
            db.execute("UPDATE t SET name = 'z' WHERE id = 2")
            db.execute("DELETE FROM t WHERE id = 1")
            with self.assertRaises(DBError):  # failed statements must not be logged
                db.execute("INSERT INTO t VALUES (2, 'dup')")

            reopened = Database(path)
            self.assertEqual(reopened.execute("SELECT * FROM t"), [{"id": 2, "name": "z"}])


if __name__ == "__main__":
    unittest.main()
