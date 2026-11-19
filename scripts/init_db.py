"""Create data/campushield.db with synthetic students, courses, attendance and dummy accounts.

Dummy-account passwords are random, printed once and written to
data/lab_credentials.txt (git-ignored) so they are never committed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db  # noqa: E402

if __name__ == "__main__":
    creds = db.init_db()
    db.write_credentials(creds)
    conn = db.connect()
    for table in ("students", "users", "courses", "registrations", "attendance"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<14} {n:>4} rows")
    conn.close()
    print(f"Database: {db.DB_PATH}")
    print(f"Lab credentials written to {db.CRED_FILE} (git-ignored)")
