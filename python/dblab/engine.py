"""A tiny SQL engine you can read in one sitting.

Supported statements (case-insensitive keywords, ``;`` optional):

    CREATE TABLE t (id INT PRIMARY KEY, name TEXT, price REAL)
    INSERT INTO t [(col, ...)] VALUES (...), (...)
    SELECT * | col, ... | COUNT(*) FROM t [WHERE ...] [ORDER BY col [ASC|DESC]] [LIMIT n]
    UPDATE t SET col = value [, ...] [WHERE ...]
    DELETE FROM t [WHERE ...]
    DROP TABLE t

WHERE supports =, <>, !=, <, <=, >, >=, IS [NOT] NULL, AND, OR and parentheses.

Durability: pass a ``path`` and every successful write statement is appended
to a write-ahead log (one JSON string per line) and fsync'd. Re-opening the
same path replays the log, which rebuilds the exact same state.
"""

from __future__ import annotations

import json
import operator
import os
import re
from typing import Any, Callable

__all__ = ["Database", "DBError"]


class DBError(Exception):
    """Raised for any parse, schema, or constraint error."""


_TOKEN = re.compile(
    r"""\s*(?:
        (?P<num>\d+\.\d+|\d+)
      | (?P<str>'(?:[^']|'')*')
      | (?P<id>[A-Za-z_][A-Za-z_0-9]*)
      | (?P<op><=|>=|<>|!=|=|<|>|\(|\)|,|\*|;|-)
    )""",
    re.VERBOSE,
)

_CMP: dict[str, Callable[[Any, Any], bool]] = {
    "=": operator.eq,
    "<>": operator.ne,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

_TYPES = {"INT": "INT", "INTEGER": "INT", "TEXT": "TEXT", "REAL": "REAL", "FLOAT": "REAL"}

Row = dict[str, Any]
Predicate = Callable[[Row], bool]


def _tokenize(sql: str) -> list[tuple[str, Any]]:
    sql = sql.strip()
    pos, out = 0, []
    while pos < len(sql):
        m = _TOKEN.match(sql, pos)
        if not m:
            raise DBError(f"unexpected character near {sql[pos:pos + 12]!r}")
        pos = m.end()
        kind = m.lastgroup
        text = m.group(kind)
        if kind == "num":
            out.append(("num", float(text) if "." in text else int(text)))
        elif kind == "str":
            out.append(("str", text[1:-1].replace("''", "'")))
        else:
            out.append((kind, text))
    return out


def _split_script(script: str) -> list[str]:
    """Split on ';' while ignoring semicolons inside string literals."""
    statements, buf, in_str = [], [], False
    for ch in script:
        if ch == "'":
            in_str = not in_str
        if ch == ";" and not in_str:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


class _Parser:
    """Recursive-descent parser. WHERE clauses compile straight to closures."""

    def __init__(self, sql: str) -> None:
        self.tokens = _tokenize(sql)
        self.i = 0

    def peek(self) -> tuple[Any, Any]:
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def next(self) -> tuple[Any, Any]:
        tok = self.peek()
        self.i += 1
        return tok

    def kw(self, word: str) -> bool:
        kind, value = self.peek()
        if kind == "id" and value.upper() == word:
            self.i += 1
            return True
        return False

    def expect_kw(self, word: str) -> None:
        if not self.kw(word):
            raise DBError(f"expected {word}")

    def op(self, symbol: str) -> bool:
        kind, value = self.peek()
        if kind == "op" and value == symbol:
            self.i += 1
            return True
        return False

    def expect_op(self, symbol: str) -> None:
        if not self.op(symbol):
            raise DBError(f"expected {symbol!r}")

    def ident(self) -> str:
        kind, value = self.next()
        if kind != "id":
            raise DBError("expected a name")
        return value.lower()

    def type_name(self) -> str:
        kind, value = self.next()
        if kind != "id" or value.upper() not in _TYPES:
            raise DBError(f"unknown column type {value!r}")
        return _TYPES[value.upper()]

    def literal(self) -> Any:
        kind, value = self.next()
        if kind == "op" and value == "-":
            kind, value = self.next()
            if kind != "num":
                raise DBError("expected a number after '-'")
            return -value
        if kind in ("num", "str"):
            return value
        if kind == "id" and value.upper() == "NULL":
            return None
        raise DBError("expected a literal value")

    def finish(self) -> None:
        while self.op(";"):
            pass
        if self.i < len(self.tokens):
            raise DBError(f"unexpected trailing input near {self.tokens[self.i][1]!r}")

    # --- WHERE -----------------------------------------------------------
    def where(self) -> Predicate | None:
        return self._or() if self.kw("WHERE") else None

    def _or(self) -> Predicate:
        left = self._and()
        while self.kw("OR"):
            left = _either(left, self._and())
        return left

    def _and(self) -> Predicate:
        left = self._cmp()
        while self.kw("AND"):
            left = _both(left, self._cmp())
        return left

    def _cmp(self) -> Predicate:
        if self.op("("):
            inner = self._or()
            self.expect_op(")")
            return inner
        left = self._operand()
        if self.kw("IS"):
            negate = self.kw("NOT")
            self.expect_kw("NULL")
            return lambda r: (left(r) is None) != negate
        kind, symbol = self.next()
        if kind != "op" or symbol not in _CMP:
            raise DBError("expected a comparison operator")
        right = self._operand()
        compare = _CMP[symbol]

        def test(row: Row) -> bool:
            a, b = left(row), right(row)
            return a is not None and b is not None and compare(a, b)

        return test

    def _operand(self) -> Callable[[Row], Any]:
        kind, value = self.peek()
        if kind == "id" and value.upper() != "NULL":
            self.i += 1
            name = value.lower()
            return lambda row: row[name]
        constant = self.literal()
        return lambda row: constant


def _either(a: Predicate, b: Predicate) -> Predicate:
    return lambda row: a(row) or b(row)


def _both(a: Predicate, b: Predicate) -> Predicate:
    return lambda row: a(row) and b(row)


class _Table:
    def __init__(self, name: str, columns: list[tuple[str, str]], pk: str | None) -> None:
        self.name = name
        self.columns = columns
        self.types = dict(columns)
        self.pk = pk
        self.rows: list[Row] = []
        self.keys: set[Any] = set()  # primary-key index: O(1) uniqueness checks

    def coerce(self, col: str, value: Any) -> Any:
        wanted = self.types[col]
        if value is None:
            if col == self.pk:
                raise DBError(f"primary key {col!r} cannot be NULL")
            return None
        if wanted == "INT" and isinstance(value, int) and not isinstance(value, bool):
            return value
        if wanted == "REAL" and isinstance(value, (int, float)):
            return float(value)
        if wanted == "TEXT" and isinstance(value, str):
            return value
        raise DBError(f"column {col!r} expects {wanted}, got {value!r}")


class Database:
    _MUTATING = {"CREATE", "INSERT", "UPDATE", "DELETE", "DROP"}

    def __init__(self, path: str | None = None) -> None:
        self._tables: dict[str, _Table] = {}
        self._path = path
        self._replaying = False
        self._handlers = {
            "CREATE": self._create,
            "INSERT": self._insert,
            "SELECT": self._select,
            "UPDATE": self._update,
            "DELETE": self._delete,
            "DROP": self._drop,
        }
        if path and os.path.exists(path):
            self._replay(path)

    # --- public API ------------------------------------------------------
    def execute(self, sql: str) -> list[Row] | int:
        """Run one statement. SELECT returns a list of dicts, others a row count."""
        parser = _Parser(sql)
        kind, verb = parser.next()
        if kind != "id":
            raise DBError("empty or invalid statement")
        verb = verb.upper()
        handler = self._handlers.get(verb)
        if handler is None:
            raise DBError(f"unsupported statement: {verb}")
        result = handler(parser)
        if verb in self._MUTATING and self._path and not self._replaying:
            self._log(sql)
        return result

    def executescript(self, script: str) -> list[list[Row] | int]:
        return [self.execute(stmt) for stmt in _split_script(script)]

    def table_names(self) -> list[str]:
        return sorted(self._tables)

    # --- durability ------------------------------------------------------
    def _log(self, sql: str) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sql) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _replay(self, path: str) -> None:
        self._replaying = True
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.execute(json.loads(line))
        finally:
            self._replaying = False

    # --- statements ------------------------------------------------------
    def _table(self, name: str) -> _Table:
        try:
            return self._tables[name]
        except KeyError:
            raise DBError(f"no such table: {name}") from None

    def _create(self, p: _Parser) -> int:
        p.expect_kw("TABLE")
        name = p.ident()
        if name in self._tables:
            raise DBError(f"table {name!r} already exists")
        p.expect_op("(")
        columns: list[tuple[str, str]] = []
        pk = None
        while True:
            col = p.ident()
            if col in [c for c, _ in columns]:
                raise DBError(f"duplicate column {col!r}")
            typ = p.type_name()
            if p.kw("PRIMARY"):
                p.expect_kw("KEY")
                if pk is not None:
                    raise DBError("only one PRIMARY KEY is supported")
                pk = col
            columns.append((col, typ))
            if not p.op(","):
                break
        p.expect_op(")")
        p.finish()
        self._tables[name] = _Table(name, columns, pk)
        return 0

    def _insert(self, p: _Parser) -> int:
        p.expect_kw("INTO")
        table = self._table(p.ident())
        cols = [c for c, _ in table.columns]
        if p.op("("):
            cols = [p.ident()]
            while p.op(","):
                cols.append(p.ident())
            p.expect_op(")")
            for c in cols:
                if c not in table.types:
                    raise DBError(f"unknown column {c!r}")
        p.expect_kw("VALUES")
        tuples = []
        while True:
            p.expect_op("(")
            values = [p.literal()]
            while p.op(","):
                values.append(p.literal())
            p.expect_op(")")
            if len(values) != len(cols):
                raise DBError(f"expected {len(cols)} values, got {len(values)}")
            tuples.append(values)
            if not p.op(","):
                break
        p.finish()

        # Validate every row first so a multi-row INSERT is all-or-nothing.
        new_rows, seen = [], set(table.keys)
        for values in tuples:
            row = {c: None for c, _ in table.columns}
            for c, v in zip(cols, values):
                row[c] = table.coerce(c, v)
            if table.pk:
                key = row[table.pk]
                if key is None:
                    raise DBError(f"primary key {table.pk!r} cannot be NULL")
                if key in seen:
                    raise DBError(f"duplicate primary key {key!r}")
                seen.add(key)
            new_rows.append(row)
        table.rows.extend(new_rows)
        table.keys = seen
        return len(new_rows)

    def _filter(self, table: _Table, pred: Predicate | None) -> list[Row]:
        if pred is None:
            return list(table.rows)
        try:
            return [r for r in table.rows if pred(r)]
        except KeyError as e:
            raise DBError(f"unknown column {e.args[0]!r}") from None
        except TypeError:
            raise DBError("cannot compare values of different types") from None

    def _select(self, p: _Parser) -> list[Row]:
        count, cols = False, None
        if p.op("*"):
            pass
        elif p.kw("COUNT"):
            p.expect_op("(")
            p.expect_op("*")
            p.expect_op(")")
            count = True
        else:
            cols = [p.ident()]
            while p.op(","):
                cols.append(p.ident())
        p.expect_kw("FROM")
        table = self._table(p.ident())
        pred = p.where()
        order, desc, limit = None, False, None
        if p.kw("ORDER"):
            p.expect_kw("BY")
            order = p.ident()
            if p.kw("DESC"):
                desc = True
            else:
                p.kw("ASC")
        if p.kw("LIMIT"):
            limit = p.literal()
            if not isinstance(limit, int) or limit < 0:
                raise DBError("LIMIT needs a non-negative integer")
        p.finish()

        rows = self._filter(table, pred)
        if count:
            return [{"count": len(rows)}]
        if order:
            if order not in table.types:
                raise DBError(f"unknown column {order!r}")
            try:
                rows.sort(key=lambda r: (r[order] is not None, r[order]), reverse=desc)
            except TypeError:
                raise DBError("cannot sort values of different types") from None
        if limit is not None:
            rows = rows[:limit]
        names = cols or [c for c, _ in table.columns]
        for c in names:
            if c not in table.types:
                raise DBError(f"unknown column {c!r}")
        return [{c: r[c] for c in names} for r in rows]

    def _update(self, p: _Parser) -> int:
        table = self._table(p.ident())
        p.expect_kw("SET")
        assignments = []
        while True:
            col = p.ident()
            if col not in table.types:
                raise DBError(f"unknown column {col!r}")
            p.expect_op("=")
            assignments.append((col, p.literal()))
            if not p.op(","):
                break
        pred = p.where()
        p.finish()

        targets = self._filter(table, pred)
        keys, changes = set(table.keys), []
        for row in targets:
            new = dict(row)
            for col, value in assignments:
                new[col] = table.coerce(col, value)
            if table.pk and new[table.pk] != row[table.pk]:
                keys.discard(row[table.pk])
                if new[table.pk] in keys:
                    raise DBError(f"duplicate primary key {new[table.pk]!r}")
                keys.add(new[table.pk])
            changes.append((row, new))
        for row, new in changes:
            row.update(new)
        table.keys = keys
        return len(changes)

    def _delete(self, p: _Parser) -> int:
        p.expect_kw("FROM")
        table = self._table(p.ident())
        pred = p.where()
        p.finish()
        doomed = self._filter(table, pred)
        ids = {id(r) for r in doomed}
        table.rows = [r for r in table.rows if id(r) not in ids]
        if table.pk:
            table.keys -= {r[table.pk] for r in doomed}
        return len(doomed)

    def _drop(self, p: _Parser) -> int:
        p.expect_kw("TABLE")
        name = p.ident()
        self._table(name)
        p.finish()
        del self._tables[name]
        return 0
