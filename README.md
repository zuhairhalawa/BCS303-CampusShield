# BCS303 CampusShield - Cybersecurity Defence Project

Canadian University Dubai - BCS303 Security Principles and Practices.
Team: Zuhair Halawa (20230002902), Ilyass Elmoussaoui (20240005481).

CampusShield is a small local student attendance/registration portal (Flask + SQLite,
synthetic data only) that we attack, fix and re-test.

## Quick start (Windows, Linux or Kali)

```bash
pip install -r requirements.txt
python scripts/init_db.py                 # creates data/campushield.db + data/lab_credentials.txt (git-ignored)
python scripts/run_app.py                 # secure build  -> http://127.0.0.1:5000
python scripts/run_app.py --mode vulnerable --port 5001   # LAB ONLY vulnerable build
```

Roles: `admin1` (accounts + audit log), `registrar1` (student records, attendance),
`s2026001` / `s2026002` / `s2026020` (students - own attendance only).
Passwords are random per install - read them from `data/lab_credentials.txt`.

More sections (demos, evidence, Kali lab script) are added as the project grows.
