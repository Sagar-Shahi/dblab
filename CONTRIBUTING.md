# Contributing to DBLab

Thanks for helping. This project is a teaching tool, so **readability beats cleverness**. If a reader cannot follow a
change in one sitting, simplify it.

## Good first contributions

- Add a SQL exercise: put the problem in `sql/exercises.md`, the answer in `sql/solutions.sql` under a `-- Q<n>` marker,
  and the expected rows in `sql/expected.json` (check them by hand against `seed.sql`).
- Port a data structure to another language: Python, Java and C++ each have a hash ring and an LRU cache; Rust, Go and
  TypeScript are welcome.
- Extend the SQL engine: `JOIN`, `GROUP BY`, secondary indexes, or log checkpointing (see the roadmap in the README).
- Improve the docs with a diagram, an example, or a correction.

## Workflow

1. Fork and create a branch.
2. Make your change **with tests**.
3. Run `make test` from the repo root. It must pass for Python, Java and C++.
4. Open a pull request that says what changed and why.

## Style

- **Python**: 3.10+, type hints, standard library only (zero runtime dependencies is a feature).
- **Java**: 17+, no external libraries. Tests use the small runner in `Tests.java`.
- **C++**: C++17, header-only, clean under `-Wall -Wextra -Wpedantic`.
- **SQL**: uppercase keywords, one clause per line, standard SQL where possible.
- Comments explain *why*, not *what*.
