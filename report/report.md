# 1. Objective

The goal of this project was to secure CampusShield, a small simulated university service, and to show with evidence whether each control actually works. CampusShield is a student attendance and registration portal with a local SQLite database, three user roles (administrator, registrar and student) and application logs. All data in it is synthetic.

The project brief described a preliminary review that found unnecessary network services, weak authentication, unsafe input handling, excessive file permissions, privacy exposure and limited monitoring. We built the service ourselves so that each of these problems could be reproduced on purpose in an isolated lab, fixed, and tested again.

For every major test we followed the same loop: record the baseline, safely validate the weakness, apply a control, repeat the same test, and measure the change. In terms of the course learning outcomes, the project covers:

- **CLO-1:** a security blueprint with architecture, assets, threat register, policy and the RBAC model.
- **CLO-2:** scoped service discovery with Nmap, an attack-surface table and exposure reduction.
- **CLO-3:** password storage and auditing, AES encryption and hashing of a CSV dataset, a Caesar cipher and steganography.
- **CLO-4:** SQL injection and reflected XSS in our own application, their fixes and re-tests, plus an offline phishing / e-mail spoofing simulation.
- **CLO-5:** Linux permissions, a host firewall, traffic capture, log monitoring, a privacy (anonymisation) analysis and cloud recommendations.

# 2. Methodology

## 2.1 Lab environment

We used two environments. The application, the database and all cryptography, password, web, privacy and monitoring exercises were developed and executed on a Windows 11 development laptop. The network, operating-system and firewall exercises are scripted for the Kali Linux virtual machine, because they need root access and Linux networking tools.

Table: Tools and versions used in the lab
| Component | Where | Version / details |
|---|---|---|
| CampusShield portal | Windows laptop and Kali VM | Python 3.12.0, Flask 3.1.0, our own code in `app/` |
| Database | both | SQLite 3.42.0 through Python `sqlite3`; `sqlite3` CLI on Kali |
| Cryptography | Windows laptop | `cryptography` 36.0.2 (AES-GCM), `hashlib` (SHA-256, PBKDF2), OpenSSL 3.5.6 |
| Steganography | Windows laptop | Pillow 11.2.1, our own LSB script |
| Browser tests and screenshots | Windows laptop | Microsoft Edge driven by Playwright 1.51.0 |
| Network and OS lab | Kali Linux 2026.2 VM (VMware Workstation) | nmap, tshark, iptables, iproute2 network namespaces, curl, openssl |
| Monitoring | both | Bash + gawk script `monitoring/detect_failed_logins.sh` |

## 2.2 Attack, defend, verify

![The loop we used for every test, shown with the SQL injection result.](diagrams/attack_defend_verify.png){width=16}

For each weakness we kept two versions of the same thing, so that the before and after tests differ only in the control under test. The portal runs either as the **secure build** (default) or as a **vulnerable build** that is only used for demonstrations; both share the same login, lockout, RBAC and logging code. In the Kali lab, the same idea applies to the network: one script first deploys a weak baseline, scans and validates it, then hardens it and runs the identical scan again.

## 2.3 Scope and safety rules

- Only synthetic data. Student names, IDs and e-mail addresses are invented, and e-mail addresses use the reserved `.test` domain.
- Lab passwords for the dummy accounts are generated randomly on each installation and stored in a git-ignored file. They are not printed in this report.
- Testing targets were limited to 127.0.0.1 on the laptop and to two isolated network namespaces inside the Kali VM. No Internet host, real website or third-party system was scanned or attacked.
- The phishing e-mail is an offline `.eml` file. It was never sent and contains no credential form.
- The vulnerable build refuses to listen on anything except the loopback address unless an explicit lab flag is given, which only the Kali lab script uses.

## 2.4 How the evidence is presented

Every output box in this report marked "Real output" is copied automatically from a file in the `evidence/` folder of our repository, which was written by the script while it ran. Screenshots in Section 4 were taken by Playwright from the running application. Diagrams were drawn by us and are labelled as design diagrams. Results that come from the Kali VM are marked "Real Kali output"; where that run had not been done when this version of the report was generated, a yellow PENDING box shows exactly which file will fill it.

<!-- PAGEBREAK -->

# 3. Tasks Performed

## 3.1 Task 1 - Security blueprint (CLO-1)

### Architecture

Figure 2 shows the CampusShield design and the isolated lab around it. Users in the authorised zone reach the Flask portal through the host firewall. The portal checks the user's role on every request, talks to the SQLite database, and writes security events to an application log that our monitoring script reads. The Python "backup share" on port 8000 is the unnecessary service found in the baseline and removed during hardening.

![CampusShield architecture, lab isolation and trust boundaries (design diagram).](diagrams/architecture.png){width=16.5}

We marked three trust boundaries. **TB1** is the network edge, where traffic from the lab zones meets the host firewall. **TB2** is between the application and its data (database file, credential file and logs), which is protected by Linux file ownership and permissions. **TB3** is between user roles inside the application, which is enforced by RBAC.

Table: Roles and access boundaries
| Role | Can do | Cannot do | Enforced by |
|---|---|---|---|
| Administrator (`admin1`) | Create accounts (password policy applies), unlock locked accounts, read the audit log | Read or change student records or attendance | `require_roles("admin")` on `/admin/*` |
| Registrar (`registrar1`) | List and search student records, mark attendance, register students in courses | Manage accounts, read the audit log | `require_roles("registrar")` |
| Student (`s2026001`, `s2026002`, `s2026020`) | View their own attendance per course | See other students, any staff page | `require_roles("student")` and the student ID taken from the session, not from the request |

### Assets and threats

Table: Asset register with the main CIA property at risk
| Asset | Why it matters | Main CIA property | Example threat |
|---|---|---|---|
| A1 Student records (names, e-mails, programme, date of birth) | Personal data of students | Confidentiality | A student reads other students' records through SQL injection |
| A2 Attendance and registration data | Used for academic decisions | Integrity | Someone with stolen registrar access changes attendance |
| A3 User accounts and password hashes | Gate to everything else | Confidentiality, integrity | Offline cracking of leaked hashes, online password guessing |
| A4 Portal service (port 5000) | Students and staff need it daily | Availability | Lockout abuse or flooding the service |
| A5 Application and audit logs | Needed to detect and investigate incidents | Integrity | An attacker deletes or edits log lines to hide activity |
| A6 Database backup / data folder | Full copy of A1-A3 | Confidentiality | An open file share lets anyone download the database |

We used the following definitions in the threat register. A **threat** is a possible cause of harm (who or what could hurt an asset). A **vulnerability** is a weakness that the threat can use. An **attack** is the actual action that exploits the vulnerability. A **risk** is the combination of how likely that is and how much damage it would do.

Table: Threat register (baseline system, before controls)
| ID | Threat | Vulnerability | Attack | Risk (likelihood x impact) |
|---|---|---|---|---|
| R1 | Curious or malicious student | Attendance query built by string concatenation | SQL injection `' OR '1'='1` and `UNION SELECT` | High x High = **Critical**: all attendance rows and all password hashes exposed |
| R2 | External attacker sending links | Search term reflected into the page without encoding, no CSP | Reflected XSS through a crafted link opened by the registrar | Medium x High = **High** |
| R3 | Anyone on a lab network | Unneeded `http.server` publishing the data folder | Directory listing and download of `campushield.db` | High x High = **Critical** |
| R4 | Password guesser | Weak passwords, fast unsalted hashes (legacy design), no lockout | Online guessing or offline dictionary attack | High x Medium = **High** |
| R5 | Local OS user | Database and logs world-readable/writable (666/777) | Read student data or tamper with logs from another account | Medium x High = **High** |
| R6 | Attacker on the network path | Portal served over plain HTTP | Sniffing the login form | Medium x High = **High** |
| R7 | Phisher | Users trust display names and link text | Spoofed "IT Service Desk" e-mail | Medium x High = **High** |
| R8 | Any of the above | No alerting on repeated failures | Brute force goes unnoticed | Medium x Medium = **Medium** |

### Security policy: account access and student-record handling

1. **Accounts are personal and role-based.** Every user gets exactly one role (administrator, registrar or student) and only the permissions of that role. Shared accounts are not allowed.
2. **Least privilege.** Roles are granted by the administrator only when a job needs them, and reviewed each term. Students can only see their own records.
3. **Separation of duties.** The administrator manages accounts and logs but cannot read or change student records; the registrar manages records but cannot create accounts or read the audit log.
4. **Passwords.** At least 12 characters with upper and lower case, a digit and a symbol; not a common password; must not contain the username. Passwords are stored only as salted PBKDF2-HMAC-SHA256 hashes (600,000 iterations).
5. **Failed logins.** An account is locked for 15 minutes after 5 wrong passwords in a row. Only the administrator can unlock early, and every lock and unlock is logged.
6. **Student-record handling.** Records are synthetic in this lab; in production, records may only be accessed through the portal for a teaching or administrative purpose, never exported to personal devices, and any data set shared for analysis must be de-identified first (Section 3.5).
7. **Logging and review.** Logins, failures, lockouts, access denials and record changes are logged with time, user and source IP. Logs are readable only by the audit group and are reviewed with the monitoring script.

### Security model and mechanisms

The main model we used is **role-based access control (RBAC)** [2]. Permissions are attached to roles and users get roles, so the access rules can be read in one place: the `require_roles()` decorator in `app/web.py`. We chose RBAC because a university already thinks in roles, and it makes the policy easy to check: the access matrix in Table 9 was produced by testing every role against every page.

RBAC is supported by three other principles. **Least privilege** appears in the application (a student's ID comes from the session, so a student cannot ask for someone else's data) and in the operating system (the database is only readable by the service account and the records group). **Separation of duties** is visible in Table 2: the person who creates accounts is not the person who edits records. **Defence in depth** means that each attack in this project meets more than one layer: an outsider is blocked by the firewall first, then needs a valid account, then a role, and even an injected query is neutralised by parameterised SQL.

### Lab isolation

The Kali lab script creates two Linux network namespaces inside the VM. `cs_untrusted` (10.10.50.66) represents an unauthorised network zone and is where the scanner runs; `cs_staff` (10.10.60.10) represents the authorised campus zone. Each namespace is connected to the Kali host by a virtual Ethernet (veth) pair and has no default route, so it can reach only the Kali host on its own /24 network. The evidence for this (routes, namespaces and "no route" checks) is in Section 4.1.

## 3.2 Task 2 - Network discovery and attack surface (CLO-2)

![Kali lab network with the two lab zones and the firewall policy after hardening (design diagram).](diagrams/lab_network.png){width=16}

**Baseline.** The script `kali/run_kali_lab.sh` deploys CampusShield to `/opt/campushield` in the weak state described in the brief: the vulnerable build running as root and listening on all interfaces (0.0.0.0:5000), an extra Python `http.server` "backup share" on port 8000 that publishes the data folder, and files with mode 666/777.

**Scan.** From the untrusted zone we run a full TCP scan of the Kali host address on that segment, with service and version detection:

```
sudo ip netns exec cs_untrusted nmap -Pn -sS -sV -p- -T4 --max-retries 2 --reason 10.10.50.1
sudo ip netns exec cs_untrusted nmap -Pn -p 5000,8000 --script http-title,http-headers,http-methods 10.10.50.1
```

The scan is scoped to one lab address inside the VM; it does not leave the VM. `-p-` covers all 65,535 TCP ports, `-sV` asks each open port which service and version it runs, and the second command uses only read-only NSE scripts.

**Required or unnecessary.** Port 5000 (the portal) is required, but only for the authorised zone. Port 8000 (the backup share) is not needed by the portal at all; it exists only because someone copied files with a quick web server. Any other open port found by the scan is listed in Table 8 with a decision.

**Safe validation.** We did not try to break anything. For the backup share we checked whether directory listing is enabled and sent a `HEAD` request for the database file, which returns only headers (status 200 and the file size) without downloading the data. If Metasploit is installed in the VM, the script also runs the read-only auxiliary scanners `auxiliary/scanner/http/dir_listing` and `auxiliary/scanner/http/http_version`. For the portal, we logged in as a student from the untrusted zone and sent the same SQL injection test string used in Task 4, recording only the number of rows returned.

**Exposure control.** We applied three changes and then ran exactly the same Nmap command again:

1. Stopped the unnecessary backup share on port 8000.
2. Restarted the portal as the secure build, running as the unprivileged `cs_app` account instead of root.
3. Added an iptables chain that allows only the staff zone to reach TCP 5000 and logs and drops everything else arriving on the lab interfaces:

```
iptables -N CS_LAB_IN
iptables -A CS_LAB_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A CS_LAB_IN -s 10.10.60.0/24 -p tcp --dport 5000 -m conntrack --ctstate NEW -j ACCEPT
iptables -A CS_LAB_IN -m limit --limit 20/min -j LOG --log-prefix "CS-FW-DROP "
iptables -A CS_LAB_IN -j DROP
iptables -I INPUT 1 -i cs-untr-h  -j CS_LAB_IN
iptables -I INPUT 1 -i cs-staff-h -j CS_LAB_IN
```

The rules only match the two lab veth interfaces, so the VM's own network connection is not affected.

## 3.3 Task 3 - Authentication and cryptography (CLO-3)

**Dummy accounts and login controls.** `scripts/init_db.py` creates five dummy accounts (one administrator, one registrar, three students) with random 16-character passwords. The secure login in `app/web.py` and `app/security.py` applies: the password policy from Section 3.1, salted PBKDF2 storage, lockout after 5 failures, the same error message for every failure (so usernames cannot be guessed from it), a CSRF token on every form that changes data, and a session cookie marked `HttpOnly` and `SameSite=Lax`.

**Offline password audit.** `demonstrations/authentication/password_audit.py` creates 12 synthetic lab users and stores their passwords the "legacy" way: plain SHA-256 with no salt. It then runs an offline dictionary attack using a 60-word local wordlist plus simple mutations (capital first letter, digits and years at the end, common letter swaps), checks every password against our policy, and measures how many SHA-256 and PBKDF2 hashes this laptop can compute per second.

**Salted verification design.** The secure design generates a new 16-byte random salt for every password and stores the algorithm, iteration count, salt and hash together:

```
def hash_password(password, iterations=600_000):
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${b64(salt)}${b64(derived)}"

def verify_password(password, stored):
    scheme, iterations, salt_b64, hash_b64 = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                    b64decode(salt_b64), int(iterations))
    return hmac.compare_digest(candidate, b64decode(hash_b64))
```

A fast general-purpose hash such as SHA-256 is a poor way to store passwords for two reasons. First, it is designed to be fast, so an attacker who steals the hash table can test a huge number of guesses per second; our own laptop managed about 1.5 million per second (Section 4.3), and GPU tools are much faster. Second, without a salt, two users with the same password get the same hash and precomputed tables work. PBKDF2 with a unique salt fixes both problems: each guess costs 600,000 hash iterations, and each user has to be attacked separately. This was already pointed out by Morris and Thompson for Unix passwords in 1979 [1].

**CSV dataset, AES and hashing.** `make_dataset.py` creates `data/synthetic/campus_records.csv` with 25 synthetic student rows. `aes_gcm_demo.py` encrypts the file with AES-256 in GCM mode using a random 256-bit key (kept in a git-ignored file) and a random 96-bit nonce, decrypts it, compares the SHA-256 of the original and decrypted files, and then flips one bit of the ciphertext to check that tampering is detected. `hash_demo.py` stores a SHA-256 reference hash of the CSV and verifies both the original and a copy in which one GPA was changed. We repeated the hash and an encryption round trip with the OpenSSL command line:

```
openssl dgst -sha256 data/synthetic/campus_records.csv
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -in campus_records.csv -out records.ossl.enc -pass env:CS_LAB_PASS
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -in records.ossl.enc -out check.csv -pass env:CS_LAB_PASS
cmp campus_records.csv check.csv
```

The passphrase comes from an environment variable so it never appears in the command history or the repository.

**Caesar cipher.** `caesar.py` shifts each letter of the harmless message "Meet at the library at 3pm" by 7 places, decrypts it, and then tries all 25 possible shifts as an attacker would.

**Steganography.** `lsb_stego.py` draws a 400 x 260 PNG image locally, hides a short harmless message in the least significant bit of the pixel colour values (with a 32-bit length header), extracts it again, counts the changed pixels, and then tests what happens when the image is re-saved as JPEG.

## 3.4 Task 4 - Application and database security (CLO-4)

### The application

The portal is a Flask application backed by SQLite (`data/campushield.db`) with 20 synthetic students, 4 courses, 60 registrations and 360 attendance records. Each weakness exists only in the vulnerable build, next to its fix, so the code under test is easy to compare.

### SQL injection

**Where.** The student page `/attendance?course=` shows a student's attendance for one course. The student ID comes from the session.

**Vulnerable code** (lab build only): the course code typed by the user is pasted into the SQL text.

```
sql = ("SELECT a.student_id, s.full_name, a.course_code, a.session_date, a.status "
       "FROM attendance a JOIN students s ON s.student_id = a.student_id "
       f"WHERE a.student_id = '{sid}' AND a.course_code = '{course}' "
       "ORDER BY a.student_id, a.session_date")
rows = conn.execute(sql).fetchall()
```

**Fixed code** (secure build): the SQL text is fixed and the value is passed separately, so the database always treats it as data. An allow-list check gives a friendly message for badly formatted codes.

```
if not COURSE_RE.fullmatch(course):          # ^[A-Z]{3}\d{3}$
    error = "Course code must look like BCS303."
else:
    rows = conn.execute("SELECT ... WHERE a.student_id = ? AND a.course_code = ? ...",
                        (sid, course)).fetchall()
```

Table: SQL injection test cases (same inputs sent to both builds as student s2026001)
| Test | Input | What it tries to do |
|---|---|---|
| T1 | a registered course code, e.g. `BCS210` | Normal use - must still work after the fix |
| T2 | `BCS210' OR '1'='1` | Make the WHERE clause always true and return every student's rows |
| T3 | `x' UNION SELECT username, role, password_hash, 'leak', 'leak' FROM users --` | Read a different table (accounts and password hashes) |
| T4 | `'` | Break the query to see whether database errors leak |

**Why validation is not a substitute for parameterised SQL.** Validation decides whether input *looks* acceptable; parameterisation makes sure input can never become SQL code. A filter has to be perfect for every query and every database dialect, and it often blocks legitimate data. We showed this with the synthetic student "Aisha O'Neill": a quote-blocking filter rejects her name, and a concatenated query breaks on the apostrophe, while the parameterised query finds her correctly (Section 4.4). We still kept the allow-list check on the course code because it gives a clear error message, but the protection comes from the parameterised query.

### Reflected XSS

**Where.** The registrar search page `/search?q=` prints "Results for: ..." followed by the search term.

**Precondition.** The attacker needs a logged-in registrar to open a crafted link, for example from a phishing e-mail like the one in our simulation. The page must reflect the input without HTML encoding and the browser must be allowed to run inline script. If the registrar is not logged in, the page redirects to the login form and the payload never runs.

**Payload (harmless).** It only writes a red banner and the value of `document.cookie` into the page:

```
<script>document.body.insertAdjacentHTML('afterbegin','<h2 id="xss-proof" ...>XSS DEMO: script from
the link ran. document.cookie = ['+document.cookie+']</h2>')</script>
```

**Vulnerable vs fixed code.**

```
if app.config["VULNERABLE"]:
    shown_query = Markup(q)      # input marked as trusted HTML -> reflected XSS
else:
    shown_query = q              # Jinja2 auto-escapes < > & ' " in HTML context
```

The secure build also sends browser security headers on every response: `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; ...`, `X-Frame-Options: DENY` (clickjacking defence), `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. Output encoding is the main fix; the CSP is a second layer that would block inline script even if a future template forgot to encode something [4].

### Phishing / e-mail spoofing simulation (offline)

`demonstrations/email_simulation/spoofed_notice.eml` is a synthetic message that pretends to come from the "CUD IT Service Desk" and asks the student to "verify" their CampusShield account within 24 hours. It uses only reserved `.test` domains, was never sent, and links to no real form. `analyse_eml.py` parses it with Python's e-mail library and checks the sender identity, the Return-Path and Reply-To domains, lookalike domains, link text versus real link target, pressure words, and the SPF/DKIM/DMARC results (the `Authentication-Results` header in the file is simulated and labelled as such).

The technical limitation it demonstrates is that SMTP lets a sender write any display name and any `From:` header, and HTML lets the visible link text differ from the real destination. Users are deceived because mail clients, especially on phones, show the display name more prominently than the address, the lookalike domain `campushie1d` differs from `campushield` by one character, and the message creates urgency. Research on why phishing works found the same pattern: users rely on what the page or message looks like rather than on security indicators [13].

### Final evaluation approach

After the fixes we repeated every test on the secure build, confirmed that normal functions still work, tested RBAC for all roles, and (in the Kali lab) re-ran the SQL injection test over the network from the authorised zone and checked whether the unauthorised zone can reach the service at all. Results and residual risks are in Sections 4.4 and 5.

## 3.5 Task 5 - Operations, privacy and cloud (CLO-5)

### Linux users, groups and permissions

The Kali script creates OS accounts that mirror the application roles, then compares the weak baseline with a least-privilege layout. The three human test accounts have locked passwords; we test access with `runuser`, so no passwords are needed.

Table: Linux accounts and the permission layout applied in /opt/campushield
| Path | Owner : group | Mode | Who can access |
|---|---|---|---|
| `app/`, `scripts/` (code) | root : root | 755 / 644 | Everyone can read and run; nobody except root can change the code |
| `data/` | cs_app : cs_records | 750 | Service account; registrars can enter |
| `data/campushield.db` | cs_app : cs_records | 640 | Service account reads/writes; registrars read only; others nothing |
| `data/lab_credentials.txt` | cs_app : cs_app | 600 | Service account only |
| `logs/`, `logs/campushield.log` | cs_app : cs_audit | 750 / 640 | Service account writes; admins (cs_audit) read; others nothing |

Accounts: `cs_app` (system account, no login shell, runs the portal), `cs_registrar` (member of `cs_records`), `cs_admin` (member of `cs_audit`) and `cs_student` (no extra groups). Additional OS hardening recommendations are listed in Section 5.4.

### Host firewall

The firewall rules are listed in Section 3.2. The script records the initial firewall state, applies the rules, checks one allowed connection (staff zone to port 5000) and several denied ones (untrusted zone to port 5000, staff zone to other ports), then removes the rules to show that access returns, and applies them again.

**What a software firewall test can and cannot show about switch port security.** Our test proves that the host itself filters traffic by source network and port. It cannot show anything about the physical network: a host firewall does not stop someone from plugging a laptop into a free wall socket, spoofing a MAC address, or attacking other machines on the same switch, because these happen at layer 2 before traffic reaches our host. Switch port security (limiting MAC addresses per port, 802.1X authentication, disabling unused ports, VLAN separation) has to be configured on the switch and tested with real hardware, which was outside this lab.

### Traffic capture

We capture the portal's traffic on the staff-zone interface with `tshark` while the staff zone performs a login with a deliberately wrong password (so no real lab password ever appears in a capture file). The same login is then captured again after the portal is restarted with HTTPS using a self-signed certificate created with `openssl req -x509`. The two `.pcap` files are saved in `evidence/kali/` and can be opened in Wireshark.

### Monitoring

The portal writes one line per security event to `logs/campushield.log`, for example `2026-11-20T02:18:55 campushield[1234]: LOGIN_FAILED user=s2026002 ip=127.0.0.1 attempts=3`. `monitoring/detect_failed_logins.sh` reads this format and the Linux `sshd` format, groups failures by source IP, and raises:

- **BRUTE_FORCE** when one IP has 5 or more failures within 10 minutes (sliding window), and
- **PASSWORD_SPRAY** when one IP fails against 3 or more different usernames.

It also counts `ACCOUNT_LOCKED` and `ACCESS_DENIED` events and appends alerts to `monitoring/alerts.log`. We tested it on synthetic logs that contain a brute-force burst, a password spray, a slow attack and a normal typo, and on the real log produced by our own lockout test.

### Privacy

`privacy/make_privacy_dataset.py` creates 24 synthetic student records with direct identifiers (name, student ID, e-mail), five indirect identifiers or quasi-identifiers (date of birth, gender, nationality, home area, programme) and a sensitive attribute (scholarship type). `privacy/anonymise.py` then:

1. **Suppresses** the direct identifiers name and e-mail.
2. **Pseudonymises** the student ID with HMAC-SHA256 using a random key that is never saved.
3. **Generalises** the quasi-identifiers in up to three levels (date of birth to a 2-year and then a 4-year band, nationality to a region, home area to an emirate and then removed).
4. **Suppresses** the few records that are still unique.

For each stage it measures the number of records that are unique on the quasi-identifiers, k (the size of the smallest group of identical records, as in k-anonymity), and the average and maximum re-identification risk (1 / group size). It also checks whether any group has only one scholarship value, which is the weakness that l-diversity addresses [3].

### Cloud design

No cloud account was used. Figure 4 is our conceptual design for running CampusShield in a public cloud, and Table 7 lists the recommended controls.

![Conceptual cloud deployment for CampusShield with recommended controls C1-C11 (design diagram, nothing deployed).](diagrams/cloud_architecture.png){width=16.5}

Table: Cloud security recommendations
| Area | Recommendation |
|---|---|
| Identity and access management (C7, C11) | Single sign-on with MFA for every staff login; one least-privilege cloud role per job (app deployer, database operator, auditor); a monitored break-glass account; no long-lived access keys; admin access through a session manager instead of public SSH. |
| Network segmentation (C6, C3) | Three subnets: public (load balancer only), private app tier, private database tier. Security groups allow 443 to the load balancer, the app port only from the load balancer, and the database port only from the app tier. |
| Private database access (C4) | Managed SQL database with no public IP, reachable only from the app tier's security group. |
| Encryption in transit (C1) | TLS 1.2+ on the load balancer, HTTP redirected to HTTPS, TLS between app and database. |
| Encryption at rest (C5) | Database storage, snapshots and backups encrypted with KMS keys; key use logged and keys rotated yearly. |
| Secrets (C8) | Database password and Flask secret key kept in a secrets manager, fetched at start-up, rotated automatically, never in code or Git (our repository already keeps lab credentials and keys out of Git). |
| Logging and monitoring (C9) | App, audit, load balancer, database and IAM logs sent to a central SIEM; alerts for failed-login bursts (same logic as our script), firewall or security-group changes and new admin users. |
| Backups and recovery (C10) | Automatic encrypted snapshots, a copy in a second region, point-in-time restore, and a restore test every term with agreed RPO/RTO. |
| Web protection (C2) | A WAF with managed rules in front of the app as an extra layer against SQL injection and XSS - not a replacement for the code fixes. |

Shared infrastructure brings its own risks; for example, Ristenpart et al. showed that co-located virtual machines can leak information to each other [10], which is one reason to use managed services, dedicated tenancy where needed, and encryption.

<!-- PAGEBREAK -->

# 4. Results and Screenshots

## 4.1 Task 1 - Lab isolation evidence

The Kali run records the VM's interfaces and routes, the two namespaces and their routes, and shows that the untrusted zone has no route to the Internet or to the staff zone.

<!-- KALI 01_lab_isolation.txt 60 -->

<!-- KALIIMG vmware_network_adapter.png VMware network adapter setting of the Kali VM. -->

## 4.2 Task 2 - Nmap discovery, validation and exposure reduction

**Baseline scan from the unauthorised zone:**

<!-- KALI 03_nmap_before.txt /^(\$ |PORT|[0-9]+/tcp|Nmap scan|Not shown|Service Info|\|)/ 45 -->

**Validation of the weaknesses (non-destructive):**

<!-- KALI 04_validation.txt 45 -->

Table: Attack-surface table for the CampusShield lab target
| Asset / service | Evidence | Possible threat | Vulnerability | CIA impact | Risk | Recommended action |
|---|---|---|---|---|---|---|
| TCP 5000 CampusShield portal (Werkzeug HTTP), baseline = vulnerable build | Nmap `-sV` service and version; SQLi test returned all attendance rows (`04_validation.txt`){{K}} | Student or outsider reads all records and password hashes | SQL injection in `/attendance`, reflected XSS in `/search`, cleartext HTTP, reachable from every zone | C: High, I: Medium | **Critical** | Deploy secure build, restrict to authorised zone, run as unprivileged user, use TLS |
| TCP 8000 Python http.server "backup share" | Directory listing shows `campushield.db`; `HEAD` returns 200 with the file size (`04_validation.txt`){{K}} | Anyone downloads the whole database and the lab credential file | Unauthenticated directory listing of the data folder; service not needed | C: High | **Critical** | Remove the service; never publish the data folder |
| Any other open port found by the scan | `03_nmap_before.txt`{{K}} | Depends on service | None claimed without evidence | - | Low / informational | Not needed for the demo: block with the firewall or disable |

**The same scan after hardening, and from the authorised zone:**

<!-- KALI 07_nmap_after.txt /^(\$ |PORT|[0-9]+/tcp|Nmap scan|Not shown|All [0-9]+ scanned|Chain|pkts| +[0-9]+ +[0-9]+[KM]? +(ACCEPT|LOG|DROP))/ 40 -->

<!-- KALIIMG kali_nmap_before.png Terminal screenshot - Nmap before hardening. -->

<!-- KALIIMG kali_nmap_after.png Terminal screenshot - Nmap after hardening. -->

## 4.3 Task 3 - Authentication and cryptography results

**Password audit.** Two lab users with the same password have identical unsalted hashes, and 7 of the 12 synthetic accounts were cracked in 0.003 seconds with only 2,820 guesses. The policy check flags 8 of the 12 passwords. One honest observation: `Registrar!2026` passes our composition rules but is still a predictable "word + year" pattern, which matches research showing that users' sense of password strength often differs from real guessability [8].

<!-- EXCERPT evidence/authentication/password_audit_output.txt 15-61 -->

PBKDF2 with 600,000 iterations was about 333,878 times slower per guess than SHA-256 on the same laptop (4.56 versus 1,521,094 hashes per second). The same password hashed twice gave two different stored values because of the random salt, and verification returned True only for the exact password.

**Login controls and RBAC.** Table 9 is the access matrix measured with the Flask test client on the secure build. Each role reaches only its own pages; everything else returns 403, and anonymous requests are redirected to the login page.

Table: Measured RBAC matrix (HTTP status codes; 200 = allowed, 403 = denied, 302 = redirected to login)
| User (role) | /admin/users | /admin/audit | /students | /search | /registrar/attendance | /attendance |
|---|---|---|---|---|---|---|
| admin1 (admin) | 200 | 200 | 403 | 403 | 403 | 403 |
| registrar1 (registrar) | 403 | 403 | 200 | 200 | 200 | 403 |
| s2026001 (student) | 403 | 403 | 403 | 403 | 403 | 200 |
| not logged in | 302 | 302 | 302 | 302 | 302 | 302 |

<!-- EXCERPT evidence/authentication/auth_rbac_output.txt 8-29 -->

![After 5 wrong passwords, the correct password for s2026002 is still refused (secure build).](evidence/screenshots/lockout_correct_password_refused.png){width=12}

![Administrator view: s2026002 shows 5 failed attempts and a lock time; only the admin can unlock it.](evidence/screenshots/admin_accounts_locked.png){width=12}

**AES-256-GCM and hashing of the CSV dataset.**

<!-- EXCERPT evidence/cryptography/aes_gcm_output.txt -->

<!-- EXCERPT evidence/cryptography/hash_output.txt -->

The decrypted file has exactly the same SHA-256 as the original, so encryption and decryption were correct. Changing one bit of the ciphertext made decryption fail with `InvalidTag`, which shows that GCM protects integrity as well as confidentiality. Changing one GPA in the CSV changed 121 of the 256 bits of its SHA-256 hash, so even a tiny edit is detected. The OpenSSL commands gave the same SHA-256 value, the AES-256-CBC round trip was identical according to `cmp`, and a wrong passphrase failed with `bad decrypt` (`evidence/cryptography/openssl_output.txt`). Unlike GCM, CBC alone has no authentication tag, so it would need a separate HMAC for integrity.

**Caesar cipher.**

<!-- EXCERPT evidence/cryptography/caesar_output.txt 1-17 -->

With a shift of 7 the message encrypts and decrypts correctly, but the brute-force list finds readable English at shift 7 immediately. There are only 25 useful keys, and the pattern of the text is preserved ("at" becomes "ha" both times), so a Caesar cipher gives no real confidentiality.

**Steganography.**

![Cover image, stego image and the changed pixels (134 of 104,000 pixels changed by 1/255).](evidence/steganography/cover_vs_stego.png){width=15}

<!-- EXCERPT evidence/steganography/stego_output.txt 7-21 -->

Table: What each technique protects
| Technique | Goal it provides | What it does not provide |
|---|---|---|
| Salted PBKDF2 password hash | Confidentiality of passwords if the database leaks (slow, unique per user) | Protection for very weak passwords; online guessing still needs lockout or rate limiting |
| AES-256-GCM | Confidentiality and integrity of the CSV | Availability; protection if the key is stolen |
| AES-256-CBC (OpenSSL) | Confidentiality | Integrity - needs an HMAC or hash |
| SHA-256 file hash | Integrity (detects any change) | Confidentiality; protection if an attacker can replace both file and hash |
| Caesar cipher | Practically nothing (25 keys) | Confidentiality |
| LSB steganography | Hides that a message exists | Confidentiality of the content once found; survives no re-compression |

## 4.4 Task 4 - Application and database results

**SQL injection over HTTP, same inputs to both builds:**

<!-- EXCERPT evidence/sql_injection/sqli_http_results.txt 1-36 -->

![Vulnerable build: the tautology input returns 360 rows belonging to all 20 students. The SQL that was actually run is shown in the red box.](evidence/screenshots/sqli_tautology_vulnerable.png){width=15}

![Vulnerable build: the UNION input lists every account and its password hash.](evidence/screenshots/sqli_union_vulnerable.png){width=15}

![Secure build: the same input is rejected and no rows are returned.](evidence/screenshots/sqli_tautology_secure.png){width=15}

![Secure build: a normal query for a registered course still returns the student's 6 rows.](evidence/screenshots/sqli_normal_query_secure.png){width=15}

**Parameterised query versus concatenation, and why a filter is not enough:**

<!-- EXCERPT evidence/sql_injection/param_vs_concat_output.txt -->

The parameterised query returned 0 rows for both attack strings because the whole string was treated as a (non-existent) course code, while the concatenated query returned 360 and 5 rows. The filter test shows the practical problem with relying on validation: it rejected the real student name O'Neill, which the parameterised query handled correctly.

**Reflected XSS:**

<!-- EXCERPT evidence/web_security/xss_results.txt 5-33 -->

![Vulnerable build: the script from the link ran and wrote the red banner. document.cookie is empty because the session cookie is HttpOnly.](evidence/screenshots/xss_vulnerable.png){width=15}

![Secure build: the same link shows the payload as plain text and nothing runs.](evidence/screenshots/xss_secure.png){width=15}

The browser test confirmed the attack on the vulnerable build and the fix on the secure build, and normal searches (including "O'Neill") still worked. One interesting detail: the injected script could not read the session cookie because it is marked `HttpOnly`. This limits cookie theft, but it does not make XSS harmless - the script still runs inside the registrar's session and could read the student table on the page or submit forms as the registrar.

**RBAC denial:**

![A student opening the registrar page /students gets 403, and the attempt is logged as ACCESS_DENIED.](evidence/screenshots/rbac_student_denied_403.png){width=12}

**Phishing / spoofing analysis:**

<!-- EXCERPT evidence/email_simulation/eml_analysis_output.txt 4-35 -->

The analysis found 9 warning signs. The defences we recommend are: **SPF** to list the servers allowed to send for `campushield.test`; **DKIM** to sign outgoing mail so changes and forged signing domains are detected; **DMARC** with `p=reject` and strict alignment so receivers reject mail that fakes the exact university domain and send reports back [7]; a mail gateway that adds an "external sender" banner and flags lookalike domains; teaching users to verify through a known channel (type the portal address themselves or call the IT desk); a "report phishing" button; and MFA so a stolen password alone is not enough. Example DNS records are in `demonstrations/email_simulation/dns_records_example.txt`. DMARC does not stop lookalike domains, because the attacker can publish valid records for their own domain, so user verification is still needed.

**Network re-test from the lab zones:**

<!-- KALI 08_app_retest.txt 20 -->

## 4.5 Task 5 - Operations, privacy and monitoring results

**Linux users, groups and permissions (before and after):**

<!-- KALI 05_linux_permissions.txt /^(\$ |=>|uid=|students_readable|[0-9]+$|.*Permission denied|.*denied|BEFORE|AFTER|-rw|drw)/ 60 -->

**Host firewall - initial state, rules and connectivity checks:**

<!-- KALI 06_firewall.txt /^(\$ |-A|-N|-P|staff|untrusted|=>|.*succeeded|.*Connection)/ 40 -->

**Firewall removed, then re-applied:**

<!-- KALI 09_firewall_removed.txt 20 -->

<!-- KALIIMG kali_firewall_checks.png Terminal screenshot - allowed and blocked connections. -->

**Traffic capture (HTTP versus HTTPS):**

<!-- KALI 10_traffic_capture.txt /^(\$ tshark|frame|[0-9]+\s|.*<->|HTTP requests|Filter)/ 40 -->

<!-- KALIIMG wireshark_http_post.png Wireshark view of the captured HTTP login POST. -->

In terms of CIA, the HTTP capture is a confidentiality problem: anyone who can see the traffic can read the form fields, including the username and password, and could also change the traffic in transit (integrity). With TLS the capture should contain only the handshake and encrypted "Application Data" records, so the content is protected. The self-signed certificate is fine for the lab, but in production a certificate from a trusted CA is needed, otherwise users learn to click through warnings.

**Monitoring - synthetic attack log:**

<!-- EXCERPT evidence/monitoring/detect_app_log_output.txt 6-19 -->

**Monitoring - real log from our own lockout test on the portal:**

<!-- EXCERPT evidence/monitoring/real_app_log_detection.txt 6-16 -->

**Monitoring - Kali run (controlled burst from the staff zone):**

<!-- KALI 11_monitoring.txt /ALERT|attempt|ACCOUNT_LOCKED|CS-FW-DROP|failed logins found/ 20 -->

The script raised the expected brute-force and spray alerts on the synthetic log and ignored the single typo. On the real portal log it detected our own lockout test (6 failed or blocked attempts from 127.0.0.1 within one second against `s2026002`). It missed the planted slow attack (4 failures, one every 20 minutes) with the default rule. Changing the rule to 4 failures in 90 minutes caught it but also produced 2 extra alerts (`evidence/monitoring/detect_app_log_tuned_4in90min_output.txt`), which is the usual trade-off between sensitivity and noise. Other limitations: attacks spread over many IPs, an attacker with root access could edit the log (logs should be forwarded to another host), clock problems, and the script runs on demand rather than in real time (cron, fail2ban or a SIEM would be used in production).

**Privacy - before and after:**

Table: Re-identification exposure at each stage (24 synthetic records, 5 quasi-identifiers)
| Stage | Rows | k | Records unique on QIs | Average risk | Maximum risk |
|---|---|---|---|---|---|
| Raw data | 24 | 1 | 24 (100%) | 100% | 100% |
| Level 1 generalisation | 24 | 1 | 19 (79.2%) | 87.5% | 100% |
| Level 2 generalisation | 24 | 1 | 12 (50.0%) | 66.7% | 100% |
| Level 3 generalisation | 24 | 1 | 3 (12.5%) | 41.7% | 100% |
| Final: level 3 + 3 rows suppressed | 21 | 2 | 0 (0%) | 33.3% | 50% |

![Equivalence-class sizes before and after generalisation and suppression.](evidence/privacy/k_anonymity_before_after.png){width=14}

Before the transformation every one of the 24 students was unique on date of birth, gender, nationality, area and programme, so anyone who knows those facts (a classmate, for example) could find the row and learn the scholarship type even with the name removed. In the released table every row matches at least one other row, the average re-identification risk fell from 100% to 33.3%, and the maximum from 100% to 50%. The cost was utility: 3 of 24 rows (12.5%) were removed, exact ages, nationalities and home areas are gone, and the Cybersecurity group shrank from 3 to 2 students. Mean GPA per programme stayed close (for example 2.84 to 2.88 for Computer Science). Getting to k = 3 would have required removing 11 of the 24 rows, so with such a small dataset each extra step of protection is expensive. Two of the seven released groups still have only one scholarship value, so k-anonymity alone does not hide the sensitive attribute in those groups; l-diversity would be needed [3]. Because the student ID was replaced with a keyed pseudonym, anyone holding the key could re-link records. This is **pseudonymisation, not full anonymisation**, and the released file should still be treated as personal data.

<!-- PAGEBREAK -->

# 5. Analysis and Recommendations

## 5.1 CIA risk assessment before and after

We rated risk as likelihood x impact on a three-level scale (Low, Medium, High). Likelihood considers who can reach the weakness and how easy it is; impact considers which CIA property is affected and how much data is involved.

Table: Risk ratings before and after the controls
| Finding | Main CIA impact | Before | Control | After | Reasoning for the residual rating |
|---|---|---|---|---|---|
| SQL injection in attendance lookup | C, I | **Critical** | Parameterised query + allow-list | **Low** | Fixed and re-tested; other queries were also written with parameters, but new code could reintroduce it |
| Reflected XSS in search | C, I | **High** | Output encoding + CSP + other headers | **Low** | Re-tested in a real browser; stored XSS and other pages were not separately tested |
| Unneeded backup share on :8000 | C | **Critical** | Service removed | **Low**{{K}} | Removed; risk returns only if someone starts it again (configuration drift) |
| Portal reachable from every zone | C, A | **High** | Host firewall: staff zone only | **Low**{{K}} | Insiders in the staff zone can still reach it, so app-level controls still matter |
| Cleartext HTTP login | C, I | **High** | TLS (lab: self-signed) | **Medium**{{K}} | Needs a trusted certificate and HTTPS-only redirect in production |
| Weak passwords / fast hashes / no lockout | C | **High** | Policy, PBKDF2 + salt, 5-try lockout | **Low-Medium** | Lockout can be abused to lock real users out (availability); no MFA yet |
| Excessive file permissions, app as root | C, I | **High** | cs_app service account, 640/750, groups | **Low**{{K}} | Root can still read everything; full-disk encryption not applied |
| No alerting on failed logins | I | **Medium** | Detection script + audit log | **Low-Medium** | Slow and distributed attacks can stay under the threshold |
| Re-identifiable student dataset | C | **High** | Suppression, pseudonymisation, generalisation | **Medium** | k = 2 only; two groups lack scholarship diversity; pseudonyms reversible with the key |
| Phishing / spoofed sender | C | **High** | SPF, DKIM, DMARC, banners, training (recommended) | **Medium** | Recommended, not deployed; lookalike domains still need user checks |

## 5.2 Security scorecard

Table: Before / after scorecard for CampusShield
| Area | Before | Control implemented | Verification evidence | After | Remaining risk |
|---|---|---|---|---|---|
| Database queries | 360 rows of all 20 students and 5 password hashes exposed to one student | Parameterised SQL | `sqli_http_results.txt`, `param_vs_concat_output.txt`, screenshots | 0 rows leaked; normal query still returns 6 rows | Future code changes |
| Web output | Script from a link ran in the registrar's browser | Auto-escaping, CSP, X-Frame-Options, nosniff | `xss_results.txt`, browser screenshots | Payload shown as text, not run | Stored XSS not tested |
| Access control | (Design) one role could reach any page | RBAC decorator per route | Measured RBAC matrix, 403 screenshots | Each role reaches only its pages | Admin account is powerful; needs MFA |
| Passwords | 7 of 12 legacy passwords cracked in 0.003 s, identical hashes | Policy, PBKDF2-600k + salt | `password_audit_output.txt` | Different hash per user, ~333,878x slower guesses | Predictable passwords that pass the rules |
| Online guessing | Unlimited attempts | Lockout after 5 failures for 15 min | `auth_rbac_output.txt`, lockout screenshots | Correct password refused while locked | Lockout abuse; no MFA |
| Data at rest | CSV readable by anyone with the file | AES-256-GCM + SHA-256 reference hash | `aes_gcm_output.txt`, `hash_output.txt` | Ciphertext unreadable; tampering detected | Key stored as a local file (KMS in production) |
| Network exposure | :5000 and :8000 open to the untrusted zone | Remove :8000, iptables staff-only rule | `03_nmap_before.txt` vs `07_nmap_after.txt`{{K}} | Untrusted zone should see no open ports{{K}} | Insiders in the staff zone |
| OS permissions | DB 666, folders 777, app as root | Service account, groups, 640/750 | `05_linux_permissions.txt`{{K}} | Unauthorised account denied{{K}} | Root compromise |
| Traffic | Login form readable in capture | TLS | `10_traffic_capture.txt`, pcaps{{K}} | Only encrypted records{{K}} | Self-signed certificate in the lab |
| Monitoring | No alerts | Detection script, audit log | Detector outputs (synthetic and real logs) | Brute force and spray alerted | Slow/distributed attacks |
| Privacy | 100% of records unique | Suppression, HMAC pseudonyms, generalisation | `privacy_output.txt`, chart | 0% unique, k = 2, max risk 50% | Homogeneous groups; pseudonymisation only |
| Phishing | No sender checks | Analysis + SPF/DKIM/DMARC recommendations | `eml_analysis_output.txt` | 9 warning signs identified | Depends on users and mail-server setup |

## 5.3 Residual risks

No single fix makes CampusShield "secure". The main risks that remain after our controls are:

1. **Insiders and stolen staff accounts.** The firewall only separates network zones. A registrar account used by the wrong person can still read all student records, so MFA and audit review are the next priority.
2. **Lockout as a denial of service.** Anyone who knows a username can lock that student out for 15 minutes. Per-IP rate limiting and MFA would reduce the need for strict lockout.
3. **Untested areas.** We tested one SQL injection point and one XSS point in depth. Stored XSS, file uploads (none exist), session fixation and the CSRF protection were not attacked separately.
4. **Lab-only TLS and keys.** The certificate is self-signed and the AES key is a local file.
5. **Monitoring gaps.** Fixed thresholds miss slow or distributed attacks, and logs on the same host could be edited by an attacker with root access.
6. **Privacy.** The released dataset reaches only k = 2 and keeps two homogeneous groups.
7. **Vulnerable build in the repository.** It is needed for the demonstration and refuses non-loopback addresses by default, but it must never be deployed.

## 5.4 Recommendations

Ordered by priority:

1. Add **MFA** for the administrator and registrar roles, and per-IP rate limiting on the login form.
2. Serve the portal only over **HTTPS** with a trusted certificate, HSTS and a redirect from HTTP; set the session cookie `Secure` flag.
3. Keep **parameterised queries** as a coding rule, add a code review checklist item for SQL and template output, and run an automated scanner in testing.
4. **OS hardening** (beyond the permissions we applied): remove or disable every service that is not needed and check with `ss -ltnp` after each change; enforce SSH key-only login with `PermitRootLogin no`; enable automatic security updates; set `umask 027` for the service account; run the portal under systemd with `NoNewPrivileges`, `ProtectSystem=strict` and `PrivateTmp`; enable `auditd` rules for the database and log files; keep AppArmor enforcing.
5. Make the firewall **default-deny** for the whole host, not only the lab interfaces, and save the rules so they survive a reboot.
6. Forward logs to a separate host or SIEM and run the detection every few minutes; add rules for new admin accounts and firewall changes.
7. Publish **SPF, DKIM and DMARC (p=reject)** for the university domain and add external-sender banners and a phishing report button.
8. For any data shared for analysis, aim for a higher k with more records and check l-diversity; treat pseudonymised files as personal data.
9. Follow the cloud design in Section 3.5 if the service moves to the cloud: private database, secrets manager, KMS encryption, central logging and tested backups.

## 5.5 Limitations of our testing

The application and most exercises were run on a Windows laptop against 127.0.0.1, and the network and OS exercises in one Kali VM with network namespaces instead of separate physical machines. Speeds in the password test are from one laptop and change between runs. The wordlist and the datasets are small on purpose. The phishing message was analysed, not delivered, so we did not test real mail filters. Results from the Kali VM depend on its configuration, so other services running in that VM will also appear in the scans.

# 6. Conclusion

We built CampusShield as a working Flask and SQLite portal with three roles and synthetic data, then used it to go through the full attack, defend and verify loop. The clearest results were in the application. One crafted course code let a student read all 360 attendance records of 20 students and every password hash, and a crafted link ran script in the registrar's browser. After switching to parameterised queries, output encoding and security headers, the same tests failed while normal use still worked.

The cryptography exercises showed what each technique is good for. Salted PBKDF2 made each password guess about 330,000 times more expensive than plain SHA-256. AES-256-GCM kept the CSV confidential and detected a one-bit change. The SHA-256 hash detected a one-character edit. The Caesar cipher and steganography mainly showed their limits. The privacy work showed that removing names is not enough when every record is unique, and that each extra level of protection costs data. The Kali lab script brings the network, firewall, permission and traffic-capture tests together in one repeatable run, with the same Nmap scan before and after hardening.

The main lesson for us is that every control needs a test that could fail. Several things we expected to be fine needed fixing during the project, including an early version of our XSS test that showed the session cookie only because of how the test loaded it into the browser. The remaining risks are listed in Section 5.3, and MFA, HTTPS everywhere and central logging would be the next steps.

# 7. References

1. Robert Morris and Ken Thompson. 1979. Password security: a case history. *Communications of the ACM* 22, 11 (Nov. 1979), 594-597. https://doi.org/10.1145/359168.359172
2. David F. Ferraiolo, Ravi Sandhu, Serban Gavrila, D. Richard Kuhn, and Ramaswamy Chandramouli. 2001. Proposed NIST standard for role-based access control. *ACM Transactions on Information and System Security* 4, 3 (Aug. 2001), 224-274. https://doi.org/10.1145/501978.501980
3. Ashwin Machanavajjhala, Daniel Kifer, Johannes Gehrke, and Muthuramakrishnan Venkitasubramaniam. 2007. l-diversity: Privacy beyond k-anonymity. *ACM Transactions on Knowledge Discovery from Data* 1, 1 (Mar. 2007), Article 3. https://doi.org/10.1145/1217299.1217302
4. Lukas Weichselbaum, Michele Spagnuolo, Sebastian Lekies, and Artur Janc. 2016. CSP Is Dead, Long Live CSP! On the Insecurity of Whitelists and the Future of Content Security Policy. In *Proceedings of the 2016 ACM SIGSAC Conference on Computer and Communications Security (CCS '16)*, 1376-1387. https://doi.org/10.1145/2976749.2978363
5. Zhendong Su and Gary Wassermann. 2006. The essence of command injection attacks in web applications. In *Proceedings of the 33rd ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '06)*, 372-382. https://doi.org/10.1145/1111037.1111070
6. William G. J. Halfond and Alessandro Orso. 2005. AMNESIA: analysis and monitoring for neutralizing SQL-injection attacks. In *Proceedings of the 20th IEEE/ACM International Conference on Automated Software Engineering (ASE '05)*, 174-183. https://doi.org/10.1145/1101908.1101935
7. Zakir Durumeric, David Adrian, Ariana Mirian, James Kasten, Elie Bursztein, Nicolas Lidzborski, Kurt Thomas, Vijay Eranti, Michael Bailey, and J. Alex Halderman. 2015. Neither Snow Nor Rain Nor MITM... An Empirical Analysis of Email Delivery Security. In *Proceedings of the 2015 Internet Measurement Conference (IMC '15)*, 27-39. https://doi.org/10.1145/2815675.2815695
8. Blase Ur, Jonathan Bees, Sean M. Segreti, Lujo Bauer, Nicolas Christin, and Lorrie Faith Cranor. 2016. Do Users' Perceptions of Password Security Match Reality? In *Proceedings of the 2016 CHI Conference on Human Factors in Computing Systems (CHI '16)*, 3748-3760. https://doi.org/10.1145/2858036.2858546
9. Adam Barth, Collin Jackson, and John C. Mitchell. 2008. Robust defenses for cross-site request forgery. In *Proceedings of the 15th ACM Conference on Computer and Communications Security (CCS '08)*, 75-88. https://doi.org/10.1145/1455770.1455782
10. Thomas Ristenpart, Eran Tromer, Hovav Shacham, and Stefan Savage. 2009. Hey, you, get off of my cloud: exploring information leakage in third-party compute clouds. In *Proceedings of the 16th ACM Conference on Computer and Communications Security (CCS '09)*, 199-212. https://doi.org/10.1145/1653662.1653687
11. Jessica Fridrich, Miroslav Goljan, and Rui Du. 2001. Reliable detection of LSB steganography in color and grayscale images. In *Proceedings of the 2001 Workshop on Multimedia and Security: New Challenges (MM&Sec '01)*, 27-30. https://doi.org/10.1145/1232454.1232466
12. Donald Ray and Jay Ligatti. 2012. Defining code-injection attacks. In *Proceedings of the 39th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '12)*, 179-190. https://doi.org/10.1145/2103656.2103678
13. Rachna Dhamija, J. D. Tygar, and Marti Hearst. 2006. Why phishing works. In *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems (CHI '06)*, 581-590. https://doi.org/10.1145/1124772.1124861
14. OWASP Foundation. Password Storage Cheat Sheet; SQL Injection Prevention Cheat Sheet; Cross Site Scripting Prevention Cheat Sheet. OWASP Cheat Sheet Series. https://cheatsheetseries.owasp.org/
15. Morris Dworkin. 2007. Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC. NIST Special Publication 800-38D. https://doi.org/10.6028/NIST.SP.800-38D
16. Kathleen Moriarty, Burt Kaliski, and Andreas Rusch. 2017. PKCS #5: Password-Based Cryptography Specification Version 2.1. RFC 8018. https://www.rfc-editor.org/rfc/rfc8018
17. Scott Kitterman. 2014. Sender Policy Framework (SPF). RFC 7208; Dave Crocker, Tony Hansen, and Murray Kucherawy. 2011. DKIM Signatures. RFC 6376; Murray Kucherawy and Elizabeth Zwicky. 2015. DMARC. RFC 7489. https://www.rfc-editor.org/
18. Gordon Lyon. Nmap Reference Guide. https://nmap.org/book/man.html ; Wireshark Foundation. tshark manual page. https://www.wireshark.org/docs/man-pages/tshark.html

<!-- PAGEBREAK -->

# Appendix A - CLO to evidence mapping

Table: Where the evidence for each CLO and rubric item is
| CLO / rubric item | Evidence in this report | Files in the repository |
|---|---|---|
| CLO-1 policy, models, mechanisms | Section 3.1 (architecture, roles, assets, threat register, policy, RBAC) | `diagrams/architecture.png`, `app/web.py` (`require_roles`) |
| CLO-1 lab isolation | Section 4.1{{K}} | `kali/run_kali_lab.sh`, `evidence/kali/01_lab_isolation.txt` |
| CLO-2 Nmap, ports, CIA mapping | Sections 3.2, 4.2, Table 8{{K}} | `evidence/kali/03_*`, `04_*`, `07_*` |
| CLO-3 CSV dataset, AES, hash verified | Sections 3.3, 4.3 | `data/synthetic/campus_records.csv`, `demonstrations/cryptography/`, `evidence/cryptography/` |
| CLO-3 passwords, Caesar, steganography | Sections 3.3, 4.3 | `demonstrations/authentication/`, `demonstrations/steganography/` |
| CLO-4 vulnerable script, attack, patch | Sections 3.4, 4.4 | `app/web.py` (both builds), `demonstrations/sql_injection/`, `demonstrations/web_security/`, `evidence/screenshots/` |
| CLO-4 phishing / e-mail spoofing | Sections 3.4, 4.4 | `demonstrations/email_simulation/` |
| CLO-4 SQLite, RBAC, SQLi prevention | Sections 3.4, 4.3, 4.4 | `app/db.py`, `evidence/authentication/auth_rbac_output.txt` |
| CLO-5 traffic capture, firewall applied/removed, CIA | Sections 3.5, 4.5{{K}} | `evidence/kali/06_*`, `09_*`, `10_*`, `*.pcap` |
| CLO-5 hardening, monitoring | Sections 3.5, 4.5, 5.4 | `evidence/kali/05_*`, `monitoring/`, `evidence/monitoring/` |
| CLO-5 privacy and cloud | Sections 3.5, 4.5 | `privacy/`, `evidence/privacy/`, `diagrams/cloud_architecture.png` |

# Appendix B - How to reproduce

```
pip install -r requirements.txt
python scripts/init_db.py                                  # synthetic DB + random lab passwords (git-ignored)
python scripts/run_app.py                                  # secure build  http://127.0.0.1:5000
python scripts/run_app.py --mode vulnerable --port 5001    # lab-only vulnerable build
python demonstrations/sql_injection/run_sqli_demo.py       # SQLi before/after over HTTP
python demonstrations/sql_injection/sqli_param_vs_concat.py
python demonstrations/web_security/run_xss_demo.py         # XSS before/after in Edge
python demonstrations/authentication/password_audit.py
python demonstrations/authentication/auth_rbac_check.py
python demonstrations/cryptography/make_dataset.py && python demonstrations/cryptography/aes_gcm_demo.py
python demonstrations/cryptography/hash_demo.py && python demonstrations/cryptography/caesar.py
python demonstrations/steganography/lsb_stego.py
python privacy/make_privacy_dataset.py && python privacy/anonymise.py
python monitoring/generate_synthetic_events.py
bash monitoring/detect_failed_logins.sh monitoring/sample_logs/campushield_synthetic.log 5 10
python demonstrations/email_simulation/analyse_eml.py
sudo bash kali/run_kali_lab.sh                             # in the Kali VM
python report/build_report.py                              # rebuild this report (DOCX + PDF)
```
