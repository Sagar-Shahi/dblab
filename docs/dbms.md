# DBMS fundamentals

A short guide to the ideas behind the code in this repo. Each section points at something you can run.

## 1. What a DBMS does

A database management system sits between your program and the bytes on disk and gives you four things:

1. **A data model and query language** (tables and SQL) so you say *what* you want, not how to fetch it.
2. **Integrity**: constraints that reject bad data (`PRIMARY KEY`, `FOREIGN KEY`, `CHECK`, `NOT NULL`).
3. **Concurrency control**: many users at once without corrupting each other's work.
4. **Durability and recovery**: committed data survives a crash.

Run `python -m dblab` in `python/` to talk to the small engine in [`engine.py`](../python/dblab/engine.py).
It implements the pipeline every DBMS has: **tokenize → parse → execute → log**.

## 2. ACID

| Letter | Promise | Where to see it |
|--------|---------|-----------------|
| **A**tomicity | A transaction happens completely or not at all. | [`acid_demo.py`](../python/examples/acid_demo.py): an overdraft rolls back both updates. |
| **C**onsistency | Transactions move the database between valid states; constraints always hold. | The `CHECK (balance >= 0)` in the same demo. |
| **I**solation | Concurrent transactions behave as if they ran one at a time (to a chosen degree). | Section 5 below. |
| **D**urability | Once committed, it stays committed. | `Database(path)` appends every successful write to an fsync'd log and replays it on open. |

The engine's `INSERT` is atomic across rows: it validates every row before it touches the table, so a duplicate
key in the last row leaves the table unchanged.

## 3. Normalization

Normalization removes redundancy so that each fact is stored once and cannot disagree with itself.

**Start with a messy table** `order_lines(order_id, customer_name, customer_city, product_title, product_price, qty)`:

| Problem | Example |
|---------|---------|
| Update anomaly | Changing a customer's city means editing every one of their order lines. |
| Insert anomaly | You cannot record a new product until someone orders it. |
| Delete anomaly | Deleting a customer's only order also deletes the product's price. |

**1NF**: every cell holds one atomic value, and rows are unique. No `"python, java"` in a single column.

**2NF**: every non-key column depends on the *whole* key. With the composite key `(order_id, product_id)`, `product_price`
depends only on `product_id`, so move it to a `products` table.

**3NF**: non-key columns depend on *nothing but* the key. `customer_city` depends on the customer, not the order,
so it moves to `customers`.

The result is exactly the four tables in [`sql/schema.sql`](../sql/schema.sql). A common rule of thumb:
*"every non-key attribute must depend on the key, the whole key, and nothing but the key."*

Normalize for correctness first; denormalize deliberately later, for read speed, once you have measured a problem.

## 4. Indexes

An index is a sorted copy of one or more columns with pointers back to the rows, usually a **B-tree**. Instead of reading
every row (a *scan*, O(n)) the engine walks the tree (a *search*, O(log n)).

```
$ python examples/index_demo.py
without index: SCAN events
with index:    SEARCH events USING COVERING INDEX idx_events_user (user_id=?)
200 lookups: 1.128s -> 0.001s
```

Guidelines:

- Index columns used in `WHERE`, `JOIN ... ON`, and `ORDER BY`.
- Put the most selective column first in a composite index, and remember it only helps queries that use a **leftmost prefix**.
- Every index slows `INSERT`/`UPDATE`/`DELETE` and uses space. Do not index everything.
- A function on the column (`WHERE lower(email) = ...`) usually defeats a plain index.
- Read the plan: `EXPLAIN QUERY PLAN` in SQLite, `EXPLAIN (ANALYZE)` in PostgreSQL.

## 5. Transactions and isolation

Concurrent transactions can interfere in three classic ways:

| Anomaly | What happens |
|---------|--------------|
| Dirty read | You read another transaction's uncommitted change, which then rolls back. |
| Non-repeatable read | You read a row twice in one transaction and get different values. |
| Phantom read | You run the same query twice and a different set of rows matches. |

The SQL standard's isolation levels trade safety for speed:

| Level | Dirty read | Non-repeatable read | Phantom |
|-------|:---:|:---:|:---:|
| READ UNCOMMITTED | possible | possible | possible |
| READ COMMITTED | no | possible | possible |
| REPEATABLE READ | no | no | possible* |
| SERIALIZABLE | no | no | no |

\* PostgreSQL's REPEATABLE READ also prevents phantoms; MySQL/InnoDB uses next-key locks to do the same for most cases.

Two ways to implement isolation: **locking** (readers and writers block each other) and **MVCC** (each transaction sees a
snapshot; readers never block writers). PostgreSQL, Oracle, and InnoDB use MVCC.

## 6. Write-ahead logging and recovery

Writing straight to table files is unsafe: a crash mid-write leaves a torn page. The fix is the **write-ahead log (WAL)**:
append a description of the change to a sequential log and `fsync` it *before* acknowledging the commit. After a crash, replay
the log to redo committed work. This repo's engine does exactly this at statement level: see `Database._log` and `_replay`.

Real systems add **checkpoints** (so the log doesn't grow forever) and **undo** information (to roll back uncommitted work).

## 7. Query lifecycle

```
SQL text
  └─ parser ............ syntax tree
      └─ planner/optimizer ... picks an index or scan, a join order, a join algorithm
          └─ executor ........ pulls rows through the plan
              └─ storage engine .. pages, buffer pool, indexes, WAL
```

Join algorithms worth knowing: **nested loop** (good with an index on the inner table), **hash join** (equality joins on
large inputs), and **merge join** (both inputs already sorted).

## Further reading

- *Designing Data-Intensive Applications*, Martin Kleppmann
- *Database System Concepts*, Silberschatz, Korth, Sudarshan
- CMU 15-445 Database Systems lectures (free on YouTube)
- Use The Index, Luke (use-the-index-luke.com)
