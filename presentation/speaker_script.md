# CampusShield presentation - speaker script and live demo plan

About 15-18 minutes plus questions. The full notes for each slide are also in the PPTX
speaker notes. The split below is a suggestion; swap slides if you prefer, but both of us
must be able to explain every slide.

| Slide | Topic | Speaker | Time |
|---|---|---|---|
| 1 | Title | Zuhair | 0:45 |
| 2 | Objectives and method | Zuhair | 1:00 |
| 3 | Architecture and trust boundaries | Zuhair | 1:30 |
| 4 | Threats, vulnerabilities and CIA | Zuhair | 1:15 |
| 5 | Network discovery and exposure reduction (+ Kali demo) | Ilyass | 2:00 |
| 6 | Authentication and cryptography | Ilyass | 1:30 |
| 7 | SQL injection before/after (+ live demo) | Zuhair | 2:00 |
| 8 | Reflected XSS before/after (+ live demo) | Zuhair | 1:30 |
| 9 | Phishing / e-mail spoofing simulation | Zuhair | 1:00 |
| 10 | Linux hardening and host firewall | Ilyass | 1:30 |
| 11 | Monitoring and traffic capture | Ilyass | 1:15 |
| 12 | Privacy | Ilyass | 1:15 |
| 13 | Cloud recommendations | Ilyass | 1:00 |
| 14 | Results and conclusion | Zuhair | 1:00 |

## Before the presentation (10 minutes)

```bash
pip install -r requirements.txt
python scripts/init_db.py                      # fresh DB; passwords in data/lab_credentials.txt
python scripts/run_app.py                      # terminal 1: secure build  http://127.0.0.1:5000
python scripts/run_app.py --mode vulnerable --port 5001   # terminal 2: vulnerable build
```

Open `data/lab_credentials.txt` on the laptop (do not show it on the projector).
Have two browser tabs ready: 127.0.0.1:5001 and 127.0.0.1:5000.

## Live demo 1 - SQL injection (slide 7, Zuhair)

1. Tab 5001 (red banner). Log in as `s2026001`. Type a registered course, e.g. `BCS210`. Say: "6 rows, only my own."
2. Type `BCS210' OR '1'='1`. Point at the red box with the real SQL and "360 row(s) returned" with all students.
3. Optional: `x' UNION SELECT username, role, password_hash, 'leak', 'leak' FROM users --` shows every account hash.
4. Tab 5000. Same login, same input: "Course code must look like BCS303", 0 rows. Normal `BCS210` still works.
5. Say why: parameterised query = the input is data, never SQL code. Validation is only for a nicer message.

## Live demo 2 - reflected XSS (slide 8, Zuhair)

1. Tab 5001, log in as `registrar1`, open:
   `http://127.0.0.1:5001/search?q=<script>document.body.insertAdjacentHTML('afterbegin','<h2>XSS DEMO</h2>')</script>`
   A red "XSS DEMO" heading appears: the script ran.
2. Same link on port 5000: the text is shown literally; nothing runs.
3. Optional: browser dev tools > Network > response headers on 5000 show the CSP and X-Frame-Options.

## Live demo 3 - lockout and RBAC (if time allows)

- On 5000 type a wrong password 5 times for `s2026002`, then the right one: still refused.
- Log in as `admin1` > Accounts: s2026002 shows 5 failures and a lock time; click Unlock.
- As a student, open `http://127.0.0.1:5000/students`: 403.

## Kali demo (slides 5, 10 and 11, Ilyass)

The real Kali run is saved in `evidence/kali/` (Kali Linux kali-rolling, Nmap 7.99, TShark 4.6,
in a container on an internal-only Docker network). For the demo, open:
`03_nmap_before.txt` vs `07_nmap_after.txt`, `06_firewall.txt` (allowed vs blocked),
`05_linux_permissions.txt`, and `10_traffic_capture.txt` (HTTP form fields readable vs TLS only).
To re-run it live (about 10 minutes, start it before the talk): `bash kali/docker/run_lab_container.sh`
on the laptop with Docker Desktop running.

## Likely questions and short answers

- **Why is SHA-256 not enough for passwords?** It is fast and unsalted: same password, same hash, millions of guesses per second. PBKDF2 with a salt makes each guess about 330,000 times more expensive and every user separate.
- **Does input validation fix SQL injection?** No. It helps, but a filter must be perfect for every query and it blocks real data like O'Neill. Parameterised queries separate code from data.
- **If the cookie is HttpOnly, why is XSS still bad?** The script still runs inside the user's session: it can read the page and submit forms as the registrar.
- **Is your dataset anonymous?** No. It is pseudonymised and k = 2. Whoever has the HMAC key can re-link it, and two groups share one scholarship value.
- **What can a host firewall not show?** Anything at layer 2: free wall ports, MAC spoofing, attacks on the same switch. That needs switch port security, 802.1X and VLANs.
- **Is the system secure now?** Safer, not secure. Insiders, lockout abuse, slow attacks and self-signed TLS remain. Next: MFA, HTTPS everywhere, central logging.
