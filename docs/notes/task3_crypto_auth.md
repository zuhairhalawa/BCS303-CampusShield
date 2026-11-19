# Task 3 (CLO-3) - notes for the report

All runs were done on 2026-11-20 on the Windows development laptop (Python 3.12,
cryptography 36.0.2, OpenSSL 3.5.6 from Git for Windows). Every number below is
copied from the saved output files in `evidence/`. All accounts, passwords and
records are synthetic.

## Commands we ran

```bash
python scripts/init_db.py                                   # fresh DB + random lab passwords (git-ignored file)
python demonstrations/authentication/password_audit.py      # -> evidence/authentication/password_audit_output.txt
python demonstrations/authentication/auth_rbac_check.py     # -> evidence/authentication/auth_rbac_output.txt
python demonstrations/cryptography/make_dataset.py          # -> data/synthetic/campus_records.csv (25 rows)
python demonstrations/cryptography/aes_gcm_demo.py          # -> evidence/cryptography/aes_gcm_output.txt
python demonstrations/cryptography/hash_demo.py             # -> evidence/cryptography/hash_output.txt
CS_LAB_PASS="$(openssl rand -hex 16)" bash demonstrations/cryptography/openssl_demo.sh   # -> evidence/cryptography/openssl_output.txt
python demonstrations/cryptography/caesar.py                # -> evidence/cryptography/caesar_output.txt
python demonstrations/steganography/lsb_stego.py            # -> evidence/steganography/stego_output.txt + cover_vs_stego.png
```

## 1. Authentication controls in the app (secure build)

RBAC matrix from `auth_rbac_check.py` (Flask test client, temporary copy of the DB):

| user (role) | /admin/users | /admin/audit | /students | /search | /registrar/attendance | /attendance |
|---|---|---|---|---|---|---|
| admin1 (admin) | 200 | 200 | 403 | 403 | 403 | 403 |
| registrar1 (registrar) | 403 | 403 | 200 | 200 | 200 | 403 |
| s2026001 (student) | 403 | 403 | 403 | 403 | 403 | 200 |
| not logged in | 302 | 302 | 302 | 302 | 302 | 302 |

- Each role only reaches its own pages. The admin manages accounts and reads the audit
  log but cannot open student records (separation of duties). Every 403 is written to the
  log as `ACCESS_DENIED`.
- Lockout: 5 wrong passwords for `s2026002` all returned HTTP 401. The 6th attempt used the
  CORRECT password and was still refused (401). DB row: `failed_attempts=5`,
  `locked_until` = 15 minutes later. Audit log shows 5 x `LOGIN_FAILED`, then
  `ACCOUNT_LOCKED`, then `LOGIN_BLOCKED_LOCKED`.
- Password policy: admin tried to create `newstudent1` with `student123` -> rejected
  ("shorter than 12 characters, no uppercase letter, no symbol, appears in
  common-password list") and nothing was stored. `newstudent2` with a 14-character mixed
  password -> created.
- The error message is the same for wrong password, unknown user and locked account, so an
  attacker cannot use it to find valid usernames.

## 2. Offline password audit (synthetic lab hashes only)

- 12 synthetic lab users, passwords stored the "legacy" way: plain SHA-256, no salt.
- `lab_amal` and `lab_ghassan` both use `campus123` and got the SAME hash
  (`4cb48ed6...0b2c69`) - without a salt, one crack reveals every account with that password.
- Dictionary attack: 60-word local wordlist + simple mutations (capitalise, upper case,
  leetspeak, add 1/123/!/2025/2026...) = 2,820 guesses in 0.003 s.
  **7 of 12 accounts cracked**: qwerty123, Football1, campus123 (x2), library,
  Summer2026, Dubai2026!.
- Survivors: `P@ssw0rd` (our rules did not produce that exact leet form - a bigger
  wordlist would), `t7#Rq9!vLm2@Xp`, `Correct-Horse-Battery-42`, `w8$Kd!3zQe&Pn5`,
  `Registrar!2026`.
- Policy check: 8 of 12 fail our policy (all 7 cracked ones + `P@ssw0rd`). Honest
  observation: `Registrar!2026` passes the policy but is still a predictable "word + year"
  pattern, so composition rules alone do not guarantee strength; a breached-password
  check or a longer passphrase rule would help.
- Speed on this laptop: SHA-256 = **1,521,094 hashes/s**, PBKDF2-HMAC-SHA256 with
  600,000 iterations = **4.56 hashes/s**, i.e. about **333,878x slower per guess**.
  (Numbers change from run to run; the order of magnitude is the point.)
- Safer design (`app/security.py`): `hash_password('campus123')` twice gave two different
  stored values because each has its own random 16-byte salt
  (`pbkdf2_sha256$600000$<salt>$<hash>`). `verify_password` -> True for `campus123`,
  False for `Campus123` and for a wrong guess. Comparison uses `hmac.compare_digest`.

Why plain SHA-256 is a poor password store: it is designed to be fast, so an attacker with
a stolen table can test millions of guesses per second on a laptop (far more on a GPU), and
without a salt identical passwords give identical hashes and precomputed (rainbow) tables
work. A salted, slow KDF (PBKDF2/scrypt/Argon2) removes both advantages.

## 3. Synthetic CSV, AES encryption and hashing

- `data/synthetic/campus_records.csv`: 25 synthetic rows (student_id, full_name, .test
  e-mail, programme, gpa, fake 050-000-xxxx phone), 2,510 bytes.
- AES-256-GCM (`aes_gcm_demo.py`): random 256-bit key (kept in git-ignored
  `output/aes.key`), random 96-bit nonce, associated data label. Output
  `output/records.enc` = 2,538 bytes (12 nonce + 2,510 ciphertext + 16 tag). The name
  "Omar" does not appear in the ciphertext.
  - Decryption: SHA-256 of original and decrypted copy are both
    `31b32db9...db28c4ac` -> identical.
  - Tamper test: flipped one bit at byte 40 -> `InvalidTag`, decryption refused.
  - Wrong key -> `InvalidTag`.
- SHA-256 integrity (`hash_demo.py`): reference hash written to
  `data/synthetic/campus_records.csv.sha256`. Re-check of the original -> OK. Copy with one
  GPA changed (S2026001: 2.64 -> 4.00) -> hash `1f8dea69...c22da5d8`, MISMATCH detected;
  121 of 256 bits differ (avalanche effect).
- OpenSSL cross-check (`openssl_demo.sh`): `openssl dgst -sha256` gives the same
  `31b32db9...` value as Python. `openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt`
  with the passphrase taken from an environment variable produced a 2,528-byte file that
  starts with `Salted__` + 8-byte salt; decrypting and `cmp` showed it is identical to the
  original; a wrong passphrase failed with `bad decrypt`. CBC has no authentication tag,
  so in that mode integrity needs a separate hash/HMAC - GCM gives both.

## 4. Caesar cipher

- Plaintext `Meet at the library at 3pm`, shift 7 -> `Tlla ha aol spiyhyf ha 3wt`;
  decrypting with shift -7 gives the original back.
- Brute force: printing all 25 shifts finds the readable text at shift 7 immediately.
  Only 25 useful keys, and letter patterns stay the same ("at" -> "ha" both times), so
  it gives no real confidentiality.

## 5. Steganography (LSB in a locally generated PNG)

- Cover: 400x260 gradient PNG drawn by the script ("CampusShield" text). Hidden message
  (59 bytes + 32-bit length header = 504 bits):
  `CampusShield lab: the BCS303 demo starts at 10:00 in Lab 2.`
- Extracted message matches exactly. Only 134 of 104,000 pixels changed (0.13%) and the
  biggest change in any colour channel is 1/255 - invisible
  (`evidence/steganography/cover_vs_stego.png` shows cover, stego and the changed pixels).
- Limitation 1: re-saving the stego image as JPEG (quality 90) destroyed the message - the
  length header decoded to 3,681,399,222 and extraction failed.
- Limitation 2: anyone who suspects LSB hiding can run the same extractor and read the text
  in clear. Steganography hides that a message exists; it does not protect the content.
  Encrypt first, then hide, if both are needed.

## What each technique protects (CIA)

| Technique | Protects | Does NOT protect | Key point |
|---|---|---|---|
| Salted PBKDF2 password hash | Confidentiality of passwords if the DB leaks (slows guessing) | Weak passwords forever; online guessing (needs lockout) | One-way, slow, unique salt |
| AES-256-GCM | Confidentiality + integrity of the CSV | Availability; key theft | Key management is the hard part |
| AES-256-CBC (OpenSSL) | Confidentiality | Integrity (no tag) | Needs HMAC/hash for integrity |
| SHA-256 file hash | Integrity (detects change) | Confidentiality (anyone can hash); an attacker who can replace both file and hash | Store/sign the hash separately |
| Caesar cipher | Practically nothing (25 keys) | Confidentiality | Historical/teaching only |
| Encoding (e.g. Base64) | Nothing - reversible by anyone | Confidentiality | Format conversion, not security |
| LSB steganography | Secrecy of the message's existence | Content (if found), integrity (JPEG breaks it) | Combine with encryption |

## Limitations of these demos

- Speeds were measured on one laptop with Python; a real attacker using GPU tools
  (hashcat) would be much faster against SHA-256, which only strengthens the conclusion.
- The wordlist is tiny (60 words); real audits use lists with millions of entries.
- AES keys are stored as a local file for the demo; a real system would use a KMS/secrets
  manager.
- Lockout can be abused to lock out real users (denial of service); rate limiting by IP
  and MFA are better long-term.
