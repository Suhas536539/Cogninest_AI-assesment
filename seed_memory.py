from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from clinic_nl2sql import SEED_EXAMPLES
from sql_validation import validate_select_sql


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"
SEED_PATH = BASE_DIR / "memory_seed.json"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError("clinic.db was not found. Run setup_database.py first.")

    payload = []
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        for example in SEED_EXAMPLES[:15]:
            sql = validate_select_sql(example.sql)
            rows = connection.execute(sql).fetchall()
            payload.append(
                {
                    "question": example.question,
                    "sql": sql,
                    "notes": example.notes,
                    "preview_row_count": len(rows),
                }
            )

    SEED_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {len(payload)} memory seed examples to {SEED_PATH.name}.")


if __name__ == "__main__":
    main()
