# Notes for the report - privacy, monitoring, e-mail spoofing simulation

All runs below were executed on 2026-11-20 on the Windows development laptop
(Python 3.12, Git Bash with gawk). Outputs are the real console output saved in `evidence/`.
All data is synthetic.

## 1. Privacy (Task 5.4, CLO-5)

Commands
```
python privacy/make_privacy_dataset.py      # -> data/synthetic/privacy_students.csv (24 records, seed 2026)
python privacy/anonymise.py                 # -> privacy/output/privacy_students_anonymised.csv
```
Evidence: `evidence/privacy/privacy_output.txt`, `evidence/privacy/k_anonymity_before_after.png`

Dataset: 24 synthetic students. Direct identifiers: full_name, student_id, email.
Quasi-identifiers (QIs): date_of_birth, gender, nationality, home_area, programme.
Sensitive attribute: scholarship. Target k = 2, accept at most 20% row suppression.

Techniques applied
- Suppression of direct identifiers (name, e-mail removed).
- Pseudonymisation: student_id -> first 12 hex chars of HMAC-SHA256 with a random 256-bit key generated per run (or `CAMPUSHIELD_PSEUDO_KEY`). Key is never written to disk/repo.
- Generalisation, applied level by level until <= 20% of rows would need suppression:
  L1 DOB -> 2-year band, nationality -> region, home_area -> emirate;
  L2 DOB -> 4-year band, region -> MENA / South Asia;
  L3 emirate suppressed ("UAE").
- Record suppression of the rows still in groups smaller than k.

Key numbers (real output)

| Stage | Rows | Classes | k | Unique on QIs | Avg re-id risk | Max re-id risk |
|---|---|---|---|---|---|---|
| Raw data | 24 | 24 | 1 | 24 (100%) | 100% | 100% |
| L1 generalised | 24 | 21 | 1 | 19 (79.2%) | 87.5% | 100% |
| L2 generalised | 24 | 16 | 1 | 12 (50.0%) | 66.7% | 100% |
| L3 generalised | 24 | 10 | 1 | 3 (12.5%) | 41.7% | 100% |
| Final (L3 + suppression of 3 rows) | 21 | 7 | 2 | 0 (0%) | 33.3% | 50% |

- Rows suppressed: 3 of 24 (12.5%).
- Homogeneity check: 2 of 7 released groups have only one scholarship value, so placing a person in that group reveals their scholarship (k-anonymity does not give l-diversity).
- Cost of stronger protection: k=3 would need 11 of 24 rows suppressed even at L3 (21/24 at L1). With a small dataset, every extra unit of k costs a lot of data.
- Utility: mean GPA per programme changed only slightly (CS 2.84 -> 2.88, Cyber 3.12 -> 3.03, IS 3.12 -> 3.06), but Cybersecurity drops from 3 to 2 rows. Scholarship counts: before none 13 / merit 6 / need-based 3 / sports 2; after none 12 / merit 4 / need-based 3 / sports 2.
- No longer possible: exact age, nationality-level statistics, neighbourhood (area) analysis, contacting a student, joining with other data by student_id.

Interpretation (plain English)
- Before: every single student was unique on DOB + gender + nationality + area + programme, so anyone who knows those facts (classmate, social media) can find the row and learn the scholarship. Removing the name alone does nothing.
- After: every released row looks the same as at least one other row on the QIs; the best an attacker can do is a 50% guess, 33% on average.
- k=2 is a weak guarantee; it was chosen because the dataset is tiny. A real release would need more records, a higher k, and l-diversity for the sensitive column.
- The pseudo_id is keyed, so whoever holds the key or a lookup table can re-link records -> this is **pseudonymisation, not anonymisation** (still personal data under GDPR / UAE PDPL style rules).

CIA mapping: privacy controls protect **confidentiality** of student records; generalisation reduces data **integrity/utility** for analysis (less precise values), suppression removes rows (affects completeness/availability of data for research).

## 2. Monitoring (Task 5.3, CLO-5)

Commands
```
python monitoring/generate_synthetic_events.py
LOG_YEAR=2026 bash monitoring/detect_failed_logins.sh monitoring/sample_logs/campushield_synthetic.log 5 10
LOG_YEAR=2026 bash monitoring/detect_failed_logins.sh monitoring/sample_logs/auth_synthetic.log 5 10
LOG_YEAR=2026 bash monitoring/detect_failed_logins.sh monitoring/sample_logs/campushield_synthetic.log 4 90   # tuning test
```
Evidence: `evidence/monitoring/detect_app_log_output.txt`, `detect_auth_log_output.txt`,
`detect_app_log_tuned_4in90min_output.txt`, `alerts_log_copy.txt`.

Synthetic events planted: brute force (8 failures vs s2026002 from 10.10.50.66 in 1 min 45 s, account locked after 5th), password spray (10.10.50.77, 4 usernames, 1 guess each), slow attack (10.10.50.88, 4 failures one every 20 min), 2 ACCESS_DENIED (student opening /students and /admin/users), one normal typo. sshd log: 6 failures for root from 10.10.50.66 in 40 s, 3 invalid users from 10.10.50.99.

Results (real output)
- App log, rule 5 failures / 10 min: 17 failures from 4 IPs -> 2 alerts:
  `BRUTE_FORCE ip=10.10.50.66 failures=8 between 10:15:00 and 10:16:45 users=s2026002` and
  `PASSWORD_SPRAY ip=10.10.50.77 distinct_users=4`. Also ACCOUNT_LOCKED = 1 (s2026002), ACCESS_DENIED = 2.
  The typo (10.10.60.22, 1 failure) was correctly ignored. The slow attack (max 1 failure in any 10 min window) was **missed**.
- sshd log: 9 failures from 2 IPs -> 2 alerts: BRUTE_FORCE 10.10.50.66 (6 failures, 14:20:00-14:20:40, root) and PASSWORD_SPRAY 10.10.50.99 (test, oracle, guest).
- Tuned 4 failures / 90 min: catches the slow attack (10.10.50.88, 4 failures 12:00-13:00) but also raises an extra BRUTE_FORCE for the spray IP -> 4 alerts instead of 2. Shows the sensitivity vs noise trade-off.

Detection logic: parse two formats -> group failures per source IP -> sliding time window count >= threshold => BRUTE_FORCE; distinct usernames per IP >= 3 => PASSWORD_SPRAY; count ACCOUNT_LOCKED / ACCESS_DENIED.

Limitations: threshold tuning (slow attacks slip under), distributed attacks from many IPs, log tampering by a root attacker (forward logs off-host), clock/NTP problems and missing year in sshd lines, false positives from shared NAT / forgetful users, batch not real-time (cron, fail2ban or SIEM in production).

CIA: detection supports **integrity** and **confidentiality** (spots credential attacks early); lockout protects accounts but can hurt **availability** (attacker can lock a real student out on purpose).

## 3. E-mail spoofing / phishing simulation (rubric item, CLO-4)

Offline only. The message was never sent; all domains use the reserved `.test` TLD; no credential form exists.

Files: `demonstrations/email_simulation/spoofed_notice.eml`, `analyse_eml.py`, `dns_records_example.txt`.
Command: `python demonstrations/email_simulation/analyse_eml.py`
Evidence: `evidence/email_simulation/eml_analysis_output.txt`

What the user sees: display name **"CUD IT Service Desk"**, subject "[ACTION REQUIRED] Your CampusShield account will be suspended in 24 hours", link text `http://campushield.test/login`.

What is really there (9 warning signs flagged by the script):
1. From address is `it-support@campushie1d-support.test`, not the university domain.
2. Return-Path domain `bulk-mailer.test` differs from the From domain (SPF only checks the envelope / Return-Path).
3. Reply-To goes to a third domain `helpdesk-verify.test`.
4. `campushie1d` becomes `campushield` after swapping `1`->`l` (edit distance 1) -> homoglyph lookalike domain.
5. Link text shows `campushield.test` but the href opens `campushie1d-portal.test/verify`.
6. Pressure words: immediately, 24 hours, suspend(ed), locked, action required, verify, unusual sign-in.
7-9. Simulated Authentication-Results: SPF=fail, DKIM=none, DMARC=fail.
Verdict: LIKELY PHISHING / SPOOFED.

Technical limitation demonstrated: SMTP lets the sender write any display name and From header; the mail client shows the display name prominently and may hide the address. HTML lets link text differ from the real destination. SPF/DKIM/DMARC protect only the exact domain - an attacker who registers a lookalike domain can publish valid records for it, so the checks could even pass.

Why users are deceived: trusted name (IT desk), urgency and fear of losing attendance records, lookalike domain that differs by one character, visible link text that looks correct, mobile clients that show only the display name.

Defences
- **SPF** `v=spf1 ... -all` on campushield.test (authorised sending servers).
- **DKIM** signing of outgoing mail (detects tampering, proves signing domain).
- **DMARC** `p=reject` with strict alignment (stops direct spoofing of @campushield.test) + `rua` reports.
- Mail gateway: external-sender banner, lookalike-domain detection/blocking, URL rewriting / sandboxing.
- User verification through a known channel (type the portal address yourself, call the IT desk on the published number) - never via the link or Reply-To in the message.
- "Report phishing" button and short awareness training.
- MFA on the portal so a stolen password alone is not enough.
