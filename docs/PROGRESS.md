# Requirement to evidence checklist

Status key: **DONE** = implemented and executed, real output saved. **DESIGN** = diagram or
recommendation only, as the brief allows. Kali items were executed with `kali/run_kali_lab.sh`
on Kali Linux (kali-rolling) in an isolated container (`kali/docker/run_lab_container.sh`).

| Requirement (brief / rubric) | CLO | Status | Evidence |
|---|---|---|---|
| Architecture diagram with roles, app, DB, OS, firewall, logs, trust boundaries | 1 | DONE | `diagrams/architecture.png`, report 3.1 |
| 4+ assets, threat register (threat / vulnerability / attack / risk), CIA mapping | 1 | DONE | report Tables 3-4 |
| Account-access and student-record policy, model (RBAC) justified | 1 | DONE | report 3.1, `app/web.py` `require_roles` |
| Lab isolation evidence (VM / network settings) | 1 | DONE | `evidence/kali/00_container_network.txt`, `01_lab_isolation.txt`, `vm_settings.txt` |
| Scoped Nmap scan, ports, services, versions; required vs unnecessary | 2 | DONE | `evidence/kali/03_nmap_before.txt` |
| Safe validation of a weakness (Metasploit read-only module or other) | 2 | DONE | `evidence/kali/04_validation.txt` |
| Attack-surface table | 2 | DONE | report Table 8 |
| Port/exposure control + same Nmap scan again, before/after | 2 | DONE | `evidence/kali/06_firewall.txt`, `07_nmap_after.txt` |
| Dummy accounts, password policy, lockout | 3 | DONE | `evidence/authentication/auth_rbac_output.txt`, lockout screenshots |
| Offline password audit with self-generated hashes, weak passwords found | 3 | DONE | `evidence/authentication/password_audit_output.txt` |
| Salted KDF password verification, why fast hash is bad | 3 | DONE | same file, `app/security.py`, report 3.3 |
| CSV dataset, AES encryption + decryption, hash generated and verified (rubric) | 3 | DONE | `evidence/cryptography/aes_gcm_output.txt`, `hash_output.txt`, `openssl_output.txt` |
| Caesar cipher with shift, key-space weakness | 3 | DONE | `evidence/cryptography/caesar_output.txt` |
| Steganography hide/recover, hiding vs encrypting, limitation | 3 | DONE | `evidence/steganography/` |
| SQLite app with synthetic records | 4 | DONE | `app/`, `scripts/init_db.py` |
| SQL injection: vulnerable query, payload, effect, fix, re-test, normal use | 4 | DONE | `evidence/sql_injection/`, screenshots |
| Validation is not a substitute for parameterised SQL | 4 | DONE | `evidence/sql_injection/param_vs_concat_output.txt` |
| Second web weakness (reflected XSS) with precondition, fix, re-test | 4 | DONE | `evidence/web_security/xss_results.txt`, screenshots |
| Phishing / e-mail spoofing simulation (rubric) | 4 | DONE | `demonstrations/email_simulation/`, `evidence/email_simulation/` |
| RBAC enforced and tested (rubric) | 4 | DONE | measured RBAC matrix, 403 screenshots |
| Network reachability of the app from an unauthorised zone, residual risk, severity | 4 | DONE | `evidence/kali/08_app_retest.txt`; report 5.1 |
| Linux users/groups, least-privilege permissions, authorised vs unauthorised test | 5 | DONE | `evidence/kali/05_linux_permissions.txt` |
| 2+ OS hardening recommendations | 5 | DONE | report 5.4 |
| Host firewall: allowed/blocked checks, applied/removed (rubric), switch-port limitation | 5 | DONE | `evidence/kali/06_firewall.txt`, `09_firewall_removed.txt`; report 3.5 |
| Network traffic capture (rubric) | 5 | DONE | `evidence/kali/10_traffic_capture.txt`, `*.pcap` |
| Log monitoring script + synthetic events + alert | 5 | DONE | `evidence/monitoring/` |
| Privacy: 15+ records, generalisation/suppression/pseudonymisation, uniqueness before/after | 5 | DONE | `evidence/privacy/` |
| Cloud diagram + IAM, segmentation, private DB, encryption, secrets, logging, backups | 5 | DESIGN | `diagrams/cloud_architecture.png`, report Table 7 |
| Before/after security scorecard with residual risks | 5 | DONE | report Table 13 |
| Final report (PDF) in the required structure, ACM references | - | DONE | `report/CampusShield_Final_Report.pdf` (+ editable `.docx`, source `report/report.md`) |
| Presentation slides + script | - | DONE | `presentation/CampusShield_Presentation.pptx`, `speaker_script.md` |

## Still open

- The Kali evidence comes from the official Kali image in a container, not from the team's VMware
  VM: running commands in the VM from the host needs the guest login (see `kali/README.md`).
  The same script runs unchanged in the VM if the team wants VM screenshots as well.
- Read the whole report once and adjust wording to your own voice; add an AI-use statement if
  the course requires one.
