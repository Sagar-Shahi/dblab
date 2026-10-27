"""Interactive shell:  python -m dblab [database-file]"""

from __future__ import annotations

import sys
from typing import Any

from .engine import Database, DBError


def format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(0 rows)"
    cols = list(rows[0])

    def cell(value: Any) -> str:
        return "NULL" if value is None else str(value)

    widths = [max(len(c), *(len(cell(r[c])) for r in rows)) for c in cols]
    line = "-+-".join("-" * w for w in widths)
    out = [" | ".join(c.ljust(w) for c, w in zip(cols, widths)), line]
    out += [" | ".join(cell(r[c]).ljust(w) for c, w in zip(cols, widths)) for r in rows]
    out.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    db = Database(argv[0] if argv else None)
    print("DBLab SQL shell. End statements with ';'.  .tables lists tables, .quit exits.")
    buffer: list[str] = []
    while True:
        try:
            line = input("   ...> " if buffer else "dblab> ")
        except EOFError:
            print()
            break
        stripped = line.strip()
        if not buffer and stripped in (".quit", ".exit"):
            break
        if not buffer and stripped == ".tables":
            print("\n".join(db.table_names()) or "(no tables)")
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement, buffer = " ".join(buffer), []
            try:
                result = db.execute(statement)
            except DBError as e:
                print(f"error: {e}")
                continue
            print(format_rows(result) if isinstance(result, list) else f"ok ({result} rows affected)")


if __name__ == "__main__":
    main()
