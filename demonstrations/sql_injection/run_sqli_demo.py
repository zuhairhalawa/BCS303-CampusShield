"""Task 4 - SQL injection before/after test over real HTTP.

Logs in as student s2026001 on BOTH builds and sends the same inputs to
/attendance?course=... . The student should only ever see their own rows.
"""
import datetime
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab_servers import ROOT, SECURE, VULN, Recorder, login, start_servers, stop_servers  # noqa: E402

TESTS = [
    ("T1 normal query", None),                                        # filled with a real course below
    ("T2 tautology", "{course}' OR '1'='1"),
    ("T3 UNION - read users table", "x' UNION SELECT username, role, password_hash, 'leak', 'leak' FROM users --"),
    ("T4 lone quote (error probe)", "'"),
]


def summarise(page: str) -> dict:
    rows = re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td>", page)
    count = re.search(r"(\d+) row\(s\) returned", page)
    err = re.search(r'<p class="error">(.*?)</p>', page, re.S)
    return {
        "rows": int(count.group(1)) if count else 0,
        "distinct_first_col": sorted({r[0] for r in rows}),
        "error": html.unescape(err.group(1).strip()) if err else "",
        "sample": rows[:3],
    }


def main():
    out = Recorder(ROOT / "evidence" / "sql_injection" / "sqli_http_results.txt")
    out(f"CampusShield SQL injection test - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    out("Target: /attendance?course=<input> as student s2026001 (should only see S2026001 rows)")
    out(f"Vulnerable build: {VULN}   Secure build: {SECURE}\n")
    procs = start_servers()
    try:
        sessions = {"VULNERABLE": login(VULN, "s2026001"), "SECURE": login(SECURE, "s2026001")}
        page = sessions["SECURE"].get(f"{SECURE}/attendance").text
        course = re.search(r"<code>([A-Z]{3}\d{3})</code>", page).group(1)
        for name, payload in TESTS:
            value = course if payload is None else payload.format(course=course)
            out("=" * 78)
            out(f"{name}\n  input: {value}")
            for build, base in (("VULNERABLE", VULN), ("SECURE", SECURE)):
                r = sessions[build].get(f"{base}/attendance", params={"course": value})
                s = summarise(r.text)
                out(f"  [{build:<10}] HTTP {r.status_code} | rows returned: {s['rows']:>3} | "
                    f"distinct values in col 1: {len(s['distinct_first_col'])}")
                if s["error"]:
                    out(f"               message: {s['error'][:110]}")
                for row in s["sample"]:
                    shown = [c if len(c) < 40 else c[:37] + "..." for c in row]
                    out(f"               sample row: {shown}")
        out("=" * 78)
        out("Expected: vulnerable build leaks other students' rows (T2) and the users table (T3);")
        out("secure build rejects the same inputs and still answers the normal query (T1).")
    finally:
        stop_servers(procs)
    out.save()


if __name__ == "__main__":
    main()
