# BCS303 CampusShield - Cybersecurity Defence Project

Canadian University Dubai - BCS303 Security Principles and Practices.
Team: Zuhair Halawa (20230002902), Ilyass Elmoussaoui (20240005481).

CampusShield is a small local student attendance/registration portal (Flask + SQLite,
synthetic data only) that we attack, fix and re-test: baseline -> validate weakness ->
apply control -> repeat the same test -> measure the change.

## Deliverables

| What | Where |
|---|---|
| Final report (PDF + editable DOCX) | `report/CampusShield_Final_Report.pdf`, `.docx` (source: `report/report.md`) |
| Presentation + speaker script | `presentation/CampusShield_Presentation.pptx`, `presentation/speaker_script.md` |
| Submission bundle | `submission/` |
| Requirement checklist and status | `docs/PROGRESS.md` |
| Handover for Ilyass | `docs/HANDOVER_ILYASS.md` |

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

## Repository layout

```
app/                      Flask portal (web.py: routes + RBAC + both builds; security.py: PBKDF2, policy; db.py: schema + seed)
scripts/                  init_db.py, run_app.py
demonstrations/           sql_injection/, web_security/, authentication/, cryptography/, steganography/, email_simulation/
monitoring/               detect_failed_logins.sh + synthetic log generator
privacy/                  synthetic dataset + anonymisation / k-anonymity analysis
kali/                     run_kali_lab.sh (Nmap, firewall, permissions, tshark, monitoring) + README
diagrams/                 architecture, lab network, cloud, method (PNG + SVG source)
evidence/                 real outputs and screenshots written by the scripts
report/, presentation/    generators and outputs
```

## Evidence labels

- `evidence/*` files are written by the scripts while they run (real output). Screenshots are
  taken by Playwright (Edge) from the running app.
- `diagrams/*` are design diagrams drawn by us.
- `data/synthetic/*` and the app database contain only invented people (`.test` e-mail domain).
- `evidence/kali/` is produced by `sudo bash kali/run_kali_lab.sh` inside the Kali VM. Until it
  exists, the report shows yellow PENDING boxes for those results.

## Re-running the demos

See Appendix B of the report or `report/report.md`. Rebuild the documents with
`python report/build_report.py` (needs Word for the PDF) and `node presentation/build_deck.js`
(needs `npm install pptxgenjs@3.12.0`).

Safety: all testing is on 127.0.0.1 or inside isolated network namespaces in the Kali VM.
The vulnerable build refuses non-loopback addresses unless `--allow-lab-exposure` is given.
