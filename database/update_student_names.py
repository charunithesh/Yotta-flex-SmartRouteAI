"""Update the existing synthetic database with deterministic Indian student names."""

import sqlite3
from pathlib import Path

from seed_names import indian_student_name

DB = Path(__file__).with_name("transport.db")


def main() -> None:
    connection = sqlite3.connect(DB)
    try:
        student_ids = [row[0] for row in connection.execute("SELECT id FROM students ORDER BY id")]
        connection.executemany(
            "UPDATE students SET name = ? WHERE id = ?",
            [(indian_student_name(index), student_id) for index, student_id in enumerate(student_ids)],
        )
        connection.execute(
            "UPDATE app_users SET display_name = ? WHERE guardian_id = ?",
            (f"Parent of {indian_student_name(0)}", "GDN-000001"),
        )
        connection.commit()
        print(f"Updated {len(student_ids)} synthetic student names in {DB}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
