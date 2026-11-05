from __future__ import annotations

import sqlite3

from bot.database import initialize_database


def main() -> None:
    database_path = initialize_database()

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(news)").fetchall()

    print(f"SQLite version: {sqlite3.sqlite_version}")
    print(f"Database created: {database_path}")
    print("news table columns:")
    for column in columns:
        print(f"- {column[1]} ({column[2]})")


if __name__ == "__main__":
    main()
