"""Create SYNTHETIC log files to test the failed-login detector (Task 5.3).

monitoring/sample_logs/campushield_synthetic.log  - same format the CampusShield app writes
monitoring/sample_logs/auth_synthetic.log         - Linux sshd style (/var/log/auth.log)

What is inside (so we know what the detector SHOULD find):
  * normal activity: logins, attendance queries, one typo followed by a success
  * brute force: 8 failures against s2026002 from 10.10.50.66 in under 2 minutes
    (5 x LOGIN_FAILED, then ACCOUNT_LOCKED, then 3 x LOGIN_BLOCKED_LOCKED)
  * password spray: 10.10.50.77 tries 4 different usernames once each (below the
    brute-force threshold on purpose)
  * slow attack: 10.10.50.88 fails once every 20 minutes (should NOT be caught -
    used to discuss limitations)
  * two ACCESS_DENIED events (student opening registrar/admin pages)
"""
import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sample_logs"
DAY = datetime.datetime(2026, 11, 20)
PID = 4242

app_events = []   # (time, message)


def at(h, m, s=0):
    return DAY.replace(hour=h, minute=m, second=s)


def ev(t, msg):
    app_events.append((t, msg))


# normal morning activity
normal = [("registrar1", "10.10.60.10", "registrar", 9, 0), ("s2026001", "10.10.60.21", "student", 9, 5),
          ("admin1", "10.10.60.5", "admin", 9, 12), ("s2026020", "10.10.60.33", "student", 9, 20)]
for user, ip, role, h, m in normal:
    ev(at(h, m), f"LOGIN_SUCCESS user={user} ip={ip} role={role}")
    if role == "student":
        ev(at(h, m, 40), f"ATTENDANCE_QUERY user={user} ip={ip} course='BCS303' rows=6")
ev(at(9, 30, 5), "LOGIN_FAILED user=s2026002 ip=10.10.60.22 attempts=1")      # typo
ev(at(9, 30, 20), "LOGIN_SUCCESS user=s2026002 ip=10.10.60.22 role=student")
ev(at(9, 45), "ATTENDANCE_MARKED user=registrar1 ip=10.10.60.10 S2026001 BCS303 2026-11-20 present")

# brute force against one account (8 tries, ~15 s apart)
t = at(10, 15, 0)
for n in range(1, 9):
    if n <= 5:
        ev(t, f"LOGIN_FAILED user=s2026002 ip=10.10.50.66 attempts={n}")
        if n == 5:
            ev(t, "ACCOUNT_LOCKED user=s2026002 ip=10.10.50.66 until=2026-11-20T10:31:00")
    else:
        ev(t, "LOGIN_BLOCKED_LOCKED user=s2026002 ip=10.10.50.66 locked_until=2026-11-20T10:31:00")
    t += datetime.timedelta(seconds=15)

# password spray: one guess per account, 4 accounts
for i, user in enumerate(["admin1", "registrar1", "s2026001", "bob"]):
    detail = "attempts=unknown_user" if user == "bob" else "attempts=1"
    ev(at(11, 2 + i, 10), f"LOGIN_FAILED user={user} ip=10.10.50.77 {detail}")

# RBAC violations
ev(at(11, 30), "ACCESS_DENIED user=s2026001 ip=10.10.60.21 role=student path=/students")
ev(at(11, 30, 30), "ACCESS_DENIED user=s2026001 ip=10.10.60.21 role=student path=/admin/users")

# slow attack: one failure every 20 minutes
for i in range(4):
    ev(at(12, 0) + datetime.timedelta(minutes=20 * i), "LOGIN_FAILED user=registrar1 ip=10.10.50.88 attempts=" + str(i + 1))
ev(at(13, 30), "LOGIN_SUCCESS user=registrar1 ip=10.10.60.10 role=registrar")

# sshd-style events for the Linux auth.log format
ssh = []
t = at(14, 0, 0)
ssh.append((t, "Accepted password for cs_admin from 10.10.60.5 port 50122 ssh2"))
t = at(14, 20, 0)
for i in range(6):                              # brute force on root
    ssh.append((t, f"Failed password for root from 10.10.50.66 port {51000 + i} ssh2"))
    t += datetime.timedelta(seconds=8)
for i, user in enumerate(["test", "oracle", "guest"]):   # spray on invalid users
    ssh.append((at(14, 40 + i, 5), f"Failed password for invalid user {user} from 10.10.50.99 port {52000 + i} ssh2"))
ssh.append((at(14, 50), "Accepted password for cs_registrar from 10.10.60.10 port 50200 ssh2"))

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "campushield_synthetic.log").open("w", encoding="utf-8", newline="\n") as f:
    for t, msg in sorted(app_events, key=lambda e: e[0]):
        f.write(f"{t:%Y-%m-%dT%H:%M:%S} campushield[{PID}]: {msg}\n")
with (OUT / "auth_synthetic.log").open("w", encoding="utf-8", newline="\n") as f:
    for i, (t, msg) in enumerate(ssh):
        f.write(f"{t:%b %d %H:%M:%S} campushield-lab sshd[{3100 + i}]: {msg}\n")
print(f"wrote {len(app_events)} app events and {len(ssh)} sshd events to {OUT}")
