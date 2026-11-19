"""Task 4 - why parameterised queries (not input validation) are the real SQLi fix.

Runs directly against data/campushield.db with the sqlite3 module:
  A) string-concatenated query vs parameterised query, same payloads
  B) a quote-blocking "validation" filter breaks a legitimate name (Aisha O'Neill)
     while the parameterised query handles it correctly
"""
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab_servers import ROOT, Recorder  # noqa: E402

DB = ROOT / "data" / "campushield.db"
STUDENT = "S2026001"


def concat_query(conn, course):
    # VULNERABLE: the input becomes part of the SQL program text
    sql = f"SELECT student_id, course_code, status FROM attendance WHERE student_id = '{STUDENT}' AND course_code = '{course}'"
    return conn.execute(sql).fetchall()


def param_query(conn, course):
    # FIXED: the SQL text is fixed; the input is sent separately as a value
    sql = "SELECT student_id, course_code, status FROM attendance WHERE student_id = ? AND course_code = ?"
    return conn.execute(sql, (STUDENT, course)).fetchall()


def blocklist_ok(text):
    # naive "validation": reject anything with a quote or SQL keywords
    return not re.search(r"'|--|;|\bunion\b|\bor\b", text, re.I)


def main():
    out = Recorder(ROOT / "evidence" / "sql_injection" / "param_vs_concat_output.txt")
    conn = sqlite3.connect(DB)
    course = conn.execute("SELECT course_code FROM registrations WHERE student_id = ? LIMIT 1", (STUDENT,)).fetchone()[0]
    out(f"Part A - same input, two query styles (student {STUDENT}, course {course})")
    for payload in (course, f"{course}' OR '1'='1", "x' UNION SELECT username, role, password_hash FROM users --"):
        try:
            a = concat_query(conn, payload)
            a_txt = f"{len(a)} rows, {len({r[0] for r in a})} distinct student/user values"
        except sqlite3.Error as exc:
            a_txt = f"error: {exc}"
        b = param_query(conn, payload)
        out(f"  input: {payload}")
        out(f"    concatenated  -> {a_txt}")
        out(f"    parameterised -> {len(b)} rows (input treated as a literal course code)")

    out("\nPart B - validation is not a substitute")
    name = "O'Neill"
    out(f"  legitimate search term: {name}")
    out(f"    quote-blocking filter accepts it? {blocklist_ok(name)}  (a real student would be blocked)")
    try:
        rows = conn.execute(f"SELECT student_id, full_name FROM students WHERE full_name LIKE '%{name}%'").fetchall()
        out(f"    concatenated query -> {rows}")
    except sqlite3.Error as exc:
        out(f"    concatenated query -> error: {exc}  (the apostrophe breaks the SQL)")
    rows = conn.execute("SELECT student_id, full_name FROM students WHERE full_name LIKE ?", (f"%{name}%",)).fetchall()
    out(f"    parameterised query -> {rows}")
    out("  -> the filter blocks a real student, and every query would need its own perfect filter;")
    out("     the parameterised query keeps code and data separate, so no filter is needed for safety.")
    conn.close()
    out.save()


if __name__ == "__main__":
    main()
