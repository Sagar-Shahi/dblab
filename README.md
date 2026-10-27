# DBLab

**Learn databases by building one, in Python, Java, C++ and SQL.**

[![CI](https://github.com/Sagar-Shahi/dblab/actions/workflows/ci.yml/badge.svg)](https://github.com/Sagar-Shahi/dblab/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Java](https://img.shields.io/badge/java-17%2B-orange)
![C++](https://img.shields.io/badge/C%2B%2B-17-informational)
![License](https://img.shields.io/badge/license-MIT-green)

DBLab is a small, readable toolkit that teaches how databases really work. Each idea is implemented in code you can
read in one sitting, covered by tests, and explained in the docs. There are no dependencies: a compiler or interpreter is
all you need.

| Topic | What you get | Languages |
|-------|--------------|-----------|
| **SQL** | A practice shop database and 15 graded exercises (joins, CTEs, window functions) with tested solutions | SQL |
| **DBMS** | A mini SQL engine with a write-ahead log, plus ACID and index demos | Python, SQL |
| **DDM** (distributed databases) | Consistent-hash sharding, quorum replication, two-phase commit | Python, Java, C++ |
| **Core data structures** | Consistent hash ring and LRU cache, written idiomatically in each language | Python, Java, C++ |

## Quick start

```bash
git clone https://github.com/Sagar-Shahi/dblab.git
cd dblab
make test        # runs the Python, SQL, Java and C++ test-suites
make shell       # opens the interactive SQL shell
```

You can also run one language at a time: `make python`, `make java`, `make cpp`.

## Try the SQL engine

```text
$ cd python && python -m dblab
dblab> CREATE TABLE books (id INT PRIMARY KEY, title TEXT, price REAL);
dblab> INSERT INTO books VALUES (1, 'SQL Cookbook', 15), (2, 'Java Handbook', 18), (3, 'C++ Primer Lite', 20);
dblab> SELECT title, price FROM books WHERE price >= 18 ORDER BY price DESC;
title           | price
----------------+------
C++ Primer Lite | 20.0
Java Handbook   | 18.0
(2 rows)
dblab> INSERT INTO books VALUES (2, 'Dup', 1);
error: duplicate primary key 2
```

Or from Python, with durability. Every successful write goes to a log that is replayed on the next open:

```python
from dblab import Database

db = Database("shop.wal")
db.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
db.execute("INSERT INTO t VALUES (1, 'asha'), (2, 'bikram')")

db = Database("shop.wal")                # a "restart": state is rebuilt from the log
print(db.execute("SELECT * FROM t"))     # [{'id': 1, 'name': 'asha'}, {'id': 2, 'name': 'bikram'}]
```

The engine supports `CREATE TABLE`, `INSERT`, `SELECT` (with `WHERE`, `ORDER BY`, `LIMIT`, `COUNT(*)`), `UPDATE`,
`DELETE` and `DROP TABLE`, with type checking, primary-key enforcement and all-or-nothing multi-row inserts.

## Distributed building blocks

```python
from dblab import ShardedStore, Coordinator, Participant

store = ShardedStore(["a", "b", "c", "d", "e"], replicas=3)
store.put("user:42", {"name": "Asha"})
store.fail("a")                          # one node dies...
store.get("user:42")                     # ...reads still work
store.add_node("f")                      # scale out: only ~1/6 of the data moves

shards = [Participant("orders"), Participant("payments"), Participant("stock", will_commit=False)]
Coordinator(shards).run("txn-1")         # False: one "no" vote aborts everywhere
```

The test-suite checks the claims, not just the code. Adding a fifth node to a four-node ring moves under 30% of keys
(ideal 20%, plain `hash % n` moves about 80%) and every moved key lands on the new node.

## Repository layout

```
dblab/
├── python/
│   ├── dblab/           engine.py (SQL engine + WAL), sharding.py, twopc.py, repl.py
│   ├── examples/        acid_demo.py, index_demo.py
│   └── tests/           unittest suites, including the SQL exercise checker
├── java/src/dblab/      HashRing.java, LruCache.java, Tests.java
├── cpp/                 hash_ring.hpp, lru_cache.hpp, tests.cpp
├── sql/                 schema.sql, seed.sql, exercises.md, solutions.sql, expected.json
├── docs/                dbms.md (ACID, normalization, indexes, isolation), ddm.md (sharding, CAP, 2PC)
└── .github/workflows/   CI for all three languages
```

## Learning path

1. **Read** [docs/dbms.md](docs/dbms.md), then run `python examples/acid_demo.py` and `python examples/index_demo.py`.
2. **Practice** the 15 problems in [sql/exercises.md](sql/exercises.md) before you look at the solutions.
3. **Read** `python/dblab/engine.py` top to bottom. It is under 500 lines.
4. **Study** [docs/ddm.md](docs/ddm.md), then compare the hash ring in the three languages.
5. **Extend** the project with something from the roadmap.

## Roadmap

- [ ] `JOIN` and `GROUP BY` in the SQL engine
- [ ] Secondary indexes (a B-tree) and a tiny query planner
- [ ] WAL checkpointing and crash-recovery tests
- [ ] Raft leader election across in-process nodes
- [ ] Ports of the ring and cache to Rust, Go and TypeScript
- [ ] MVCC snapshot isolation demo

## Contributing

Pull requests are welcome, especially new exercises and language ports. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
