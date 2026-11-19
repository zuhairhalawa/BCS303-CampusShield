"""End-to-end check of authentication controls in the SECURE CampusShield build.

(a) RBAC matrix: which role can open which page (200 = allowed, 403 = denied)
(b) Lockout: 5 wrong passwords, then the correct one is still refused
(c) Password policy: admin cannot create an account with a weak password

Uses a temporary copy of data/campushield.db so the real lab database is not changed.
Run:  python scripts/init_db.py   (once)  then
      python demonstrations/authentication/auth_rbac_check.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "evidence" / "authentication"
tmp_db = Path(tempfile.mkdtemp()) / "campushield_test.db"
shutil.copy(ROOT / "data" / "campushield.db", tmp_db)
# must be set BEFORE importing the app modules
os.environ["CAMPUSHIELD_DB"] = str(tmp_db)
os.environ["CAMPUSHIELD_LOG_DIR"] = str(EVID / "app_logs")

sys.path.insert(0, str(ROOT))
from app import db  # noqa: E402
from app.web import create_app  # noqa: E402

OUT = EVID / "auth_rbac_output.txt"
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


creds = db.read_credentials()
app = create_app("secure")

say("=== (a) RBAC matrix, secure build (200 = allowed, 403 = denied) ===")
pages = ["/admin/users", "/admin/audit", "/students", "/search?q=a", "/registrar/attendance", "/attendance"]
say(f"{'user (role)':<24}" + "".join(f"{p:<23}" for p in pages))
for user, role in [("admin1", "admin"), ("registrar1", "registrar"), ("s2026001", "student")]:
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": creds[user]})
    assert r.status_code == 302, f"login failed for {user}"
    codes = [c.get(p).status_code for p in pages]
    say(f"{user + ' (' + role + ')':<24}" + "".join(f"{str(code):<23}" for code in codes))
c = app.test_client()
say(f"{'not logged in':<24}" + "".join(f"{str(c.get(p).status_code):<23}" for p in pages)
    + "  (302 = redirect to /login)")

say()
say("=== (b) Failed-login lockout for s2026002 ===")
c = app.test_client()
for i in range(1, 6):
    r = c.post("/login", data={"username": "s2026002", "password": f"WrongGuess{i}!"})
    say(f"attempt {i}: wrong password -> HTTP {r.status_code}")
r = c.post("/login", data={"username": "s2026002", "password": creds["s2026002"]})
say(f"attempt 6: CORRECT password -> HTTP {r.status_code} (account is locked, so still refused)")
conn = db.connect(tmp_db)
row = conn.execute("SELECT failed_attempts, locked_until FROM users WHERE username='s2026002'").fetchone()
say(f"users table: failed_attempts={row['failed_attempts']} locked_until={row['locked_until']}")
events = conn.execute("SELECT ts, event, detail FROM audit_log WHERE username='s2026002' ORDER BY id").fetchall()
say("audit_log rows for s2026002:")
for e in events:
    say(f"  {e['ts']} {e['event']:<22} {e['detail']}")

say()
say("=== (c) Password policy when the admin creates accounts ===")
c = app.test_client()
c.post("/login", data={"username": "admin1", "password": creds["admin1"]})
with c.session_transaction() as s:
    token = s.get("csrf_token")
if token is None:                       # token is created on the first rendered page
    c.get("/admin/users")
    with c.session_transaction() as s:
        token = s["csrf_token"]
for username, pw in [("newstudent1", "student123"), ("newstudent2", "Bq7!rT2#mW9$kL")]:
    r = c.post("/admin/users", data={"username": username, "password": pw, "role": "student",
                                     "csrf_token": token}, follow_redirects=True)
    body = r.get_data(as_text=True)
    msg = [ln.strip() for ln in body.splitlines() if 'class="flash"' in ln]
    exists = conn.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,)).fetchone()[0]
    say(f"create {username} with '{pw}': {msg[0] if msg else '(no message)'}")
    say(f"   -> account stored in DB? {bool(exists)}")
conn.close()

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {OUT.relative_to(ROOT)}]")
