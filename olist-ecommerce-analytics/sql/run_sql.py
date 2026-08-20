"""
Run every named query in business_questions.sql against the SQLite database and
print the results as tidy tables. This lets anyone reproduce the numbers used in
the README without opening a notebook.

Run from the project root:
    python sql/run_sql.py
"""

import re
import sqlite3
from pathlib import Path
import pandas as pd

DB = Path("data/olist.db")
SQL = Path("sql/business_questions.sql")

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)


def parse_named_queries(text):
    blocks = re.split(r"--\s*@name\s+", text)
    queries = []
    for block in blocks[1:]:
        name, _, body = block.partition("\n")
        sql = "\n".join(
            line for line in body.splitlines() if not line.strip().startswith("--")
        ).strip().rstrip(";")
        if sql:
            queries.append((name.strip(), sql))
    return queries


def main():
    con = sqlite3.connect(DB)
    for name, sql in parse_named_queries(SQL.read_text()):
        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)
        df = pd.read_sql_query(sql, con)
        print(df.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
