"""SQLite schema and synthetic seed data for CampusShield.

All people, IDs and e-mail addresses below are invented. E-mail addresses use the
reserved .test domain so they can never belong to a real mailbox.
"""
import datetime
import os
import random
import sqlite3
from pathlib import Path

from . import security

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("CAMPUSHIELD_DB", DATA_DIR / "campushield.db"))
CRED_FILE = DATA_DIR / "lab_credentials.txt"   # git-ignored, created locally only

SCHEMA = """
CREATE TABLE students (
    student_id    TEXT PRIMARY KEY,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    programme     TEXT NOT NULL,
    year          INTEGER NOT NULL,
    date_of_birth TEXT NOT NULL
);
CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'registrar', 'student')),
    student_id      TEXT REFERENCES students(student_id),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT
);
CREATE TABLE courses (
    code  TEXT PRIMARY KEY,
    title TEXT NOT NULL
);
CREATE TABLE registrations (
    student_id  TEXT NOT NULL REFERENCES students(student_id),
    course_code TEXT NOT NULL REFERENCES courses(code),
    term        TEXT NOT NULL,
    PRIMARY KEY (student_id, course_code)
);
CREATE TABLE attendance (
    id           INTEGER PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES students(student_id),
    course_code  TEXT NOT NULL REFERENCES courses(code),
    session_date TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late'))
);
CREATE TABLE audit_log (
    id       INTEGER PRIMARY KEY,
    ts       TEXT NOT NULL,
    username TEXT,
    event    TEXT NOT NULL,
    detail   TEXT,
    ip       TEXT
);
"""

FIRST = ["Omar", "Lina", "Yousef", "Maya", "Karim", "Sara", "Hadi", "Nour", "Rami", "Dana",
         "Tariq", "Leila", "Samir", "Hana", "Faris", "Rania", "Adam", "Zainab", "Bilal"]
LAST = ["Haddad", "Khalil", "Nasser", "Saleh", "Rahman", "Aziz", "Farouk", "Mansour",
        "Qasim", "Darwish", "Hamdan", "Yassin", "Barakat", "Sabri", "Jaber", "Hijazi",
        "Shami", "Amin", "Toukan"]
PROGRAMMES = ["BSc Cybersecurity", "BSc Computer Science", "BSc Information Systems"]
COURSES = [("BCS303", "Security Principles and Practices"),
           ("BCS210", "Database Systems"),
           ("BCS220", "Computer Networks"),
           ("BCS240", "Web Application Development")]
TERM = "Fall 2026"


def connect(path: Path = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path = None, seed: int = 303) -> dict:
    """(Re)create the database with synthetic data. Returns {username: password}."""
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    conn = connect(path)
    conn.executescript(SCHEMA)

    conn.executemany("INSERT INTO courses VALUES (?, ?)", COURSES)

    students = []
    for i in range(20):
        sid = f"S2026{i + 1:03d}"
        first, last = FIRST[i % len(FIRST)], LAST[i % len(LAST)]
        if i == 19:                       # apostrophe on purpose: shows why blocking quotes is not a fix
            first, last = "Aisha", "O'Neill"
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower().replace(chr(39), '')}@student.campushield.test"
        dob = datetime.date(2002, 1, 1) + datetime.timedelta(days=rng.randint(0, 1460))
        students.append((sid, name, email, rng.choice(PROGRAMMES), rng.randint(1, 4), dob.isoformat()))
    conn.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", students)

    start = datetime.date(2026, 9, 7)
    for sid, *_ in students:
        for code, _title in rng.sample(COURSES, 3):
            conn.execute("INSERT INTO registrations VALUES (?, ?, ?)", (sid, code, TERM))
            for week in range(6):
                status = rng.choices(["present", "absent", "late"], weights=[80, 12, 8])[0]
                day = start + datetime.timedelta(weeks=week)
                conn.execute(
                    "INSERT INTO attendance (student_id, course_code, session_date, status) VALUES (?, ?, ?, ?)",
                    (sid, code, day.isoformat(), status))

    accounts = [("admin1", "admin", None),
                ("registrar1", "registrar", None),
                ("s2026001", "student", "S2026001"),
                ("s2026002", "student", "S2026002"),
                ("s2026020", "student", "S2026020")]
    creds = {}
    for username, role, sid in accounts:
        pw = security.generate_lab_password()
        creds[username] = pw
        conn.execute("INSERT INTO users (username, password_hash, role, student_id) VALUES (?, ?, ?, ?)",
                     (username, security.hash_password(pw), role, sid))
    conn.commit()
    conn.close()
    return creds


def write_credentials(creds: dict, path: Path = CRED_FILE) -> None:
    lines = ["# CampusShield LOCAL LAB credentials - synthetic accounts only.",
             "# Generated by scripts/init_db.py. This file is git-ignored. Do not commit it.", ""]
    lines += [f"{u}:{p}" for u, p in creds.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_credentials(path: Path = CRED_FILE) -> dict:
    creds = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and ":" in line:
            u, p = line.split(":", 1)
            creds[u] = p
    return creds
