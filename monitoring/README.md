# Monitoring - failed-login detection (Task 5.3)

```bash
python monitoring/generate_synthetic_events.py                       # synthetic test logs
bash monitoring/detect_failed_logins.sh monitoring/sample_logs/campushield_synthetic.log 5 10
bash monitoring/detect_failed_logins.sh monitoring/sample_logs/auth_synthetic.log 5 10
bash monitoring/detect_failed_logins.sh logs/campushield.log          # the real app log
sudo bash monitoring/detect_failed_logins.sh /var/log/auth.log         # Kali/Linux sshd log
```

Set `LOG_YEAR=2026` when replaying the synthetic sshd log (sshd lines carry no year).
On Kali, `gawk` is preferred (`sudo apt install gawk` if `awk` is mawk).

## Detection logic

1. Each line is parsed as either a CampusShield app event (`LOGIN_FAILED`,
   `LOGIN_BLOCKED_LOCKED`, `ACCOUNT_LOCKED`, `ACCESS_DENIED`) or an sshd
   `Failed password for ... from <ip>` line. Timestamps are converted to epoch seconds.
2. Failures are grouped by source IP. A sliding time window finds the largest number
   of failures from one IP inside `window_minutes`.
   - **BRUTE_FORCE** if that number is `>= threshold`.
3. **PASSWORD_SPRAY** if one IP failed against `>= SPRAY_USERS` (default 3) different
   usernames. This catches attackers who try one password on many accounts and stay
   under the per-account lockout and the brute-force threshold.
4. `ACCOUNT_LOCKED` and `ACCESS_DENIED` (RBAC violations) are counted and listed.
5. `ALERT` lines go to the screen and are appended to `monitoring/alerts.log`.

## Limitations

- **Threshold tuning:** 5 failures / 10 minutes misses the synthetic "slow attack"
  (4 failures one hour apart from 10.10.50.88). Loosening it to 4 / 90 minutes catches
  it but also turns the 4-guess spray into a second brute-force alert - more noise.
- **Distributed attacks:** many IPs with one or two guesses each never cross the per-IP
  threshold. Per-username counting (or the app lockout) is still needed.
- **Log tampering:** an attacker with root can edit or delete local logs. Logs should be
  forwarded to a separate log server / SIEM with restricted access.
- **Clock problems:** sshd lines have no year and both formats depend on correct system
  time (NTP). Wrong clocks break the time window.
- **False positives:** a student who forgets a password or a shared NAT address
  (a whole lab behind one IP) can look like an attack.
- It is a batch script, not real-time. In production it would run from cron or be
  replaced by fail2ban / SIEM rules.
