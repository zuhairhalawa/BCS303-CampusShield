#!/usr/bin/env bash
# detect_failed_logins.sh - CampusShield failed-login detector (BCS303 Task 5.3)
#
# Usage: ./detect_failed_logins.sh <logfile> [threshold=5] [window_minutes=10]
#
# Reads either the CampusShield application log
#   2026-11-20T10:15:02 campushield[1234]: LOGIN_FAILED user=s2026002 ip=10.10.50.66 attempts=3
# or a Linux sshd log (/var/log/auth.log)
#   Nov 20 14:20:00 host sshd[3101]: Failed password for root from 10.10.50.66 port 51000 ssh2
#
# Rules
#   BRUTE_FORCE    one source IP has >= threshold failed logins inside any window_minutes window
#   PASSWORD_SPRAY one source IP failed against >= SPRAY_USERS (default 3) different usernames
# It also counts ACCOUNT_LOCKED and ACCESS_DENIED events from the app log.
# ALERT lines are printed and appended to $ALERT_FILE (default monitoring/alerts.log).

set -u
LOG="${1:?usage: $0 <logfile> [threshold] [window_minutes]}"
THRESHOLD="${2:-5}"
WINDOW_MIN="${3:-10}"
SPRAY_USERS="${SPRAY_USERS:-3}"
YEAR="${LOG_YEAR:-$(date +%Y)}"                 # sshd lines have no year
ALERT_FILE="${ALERT_FILE:-$(dirname "$0")/alerts.log}"
AWK="$(command -v gawk || command -v awk)"

[ -r "$LOG" ] || { echo "cannot read $LOG" >&2; exit 2; }

echo "== CampusShield failed-login detector =="
echo "log: $LOG"
echo "rules: BRUTE_FORCE >= $THRESHOLD failures from one IP within $WINDOW_MIN min; PASSWORD_SPRAY >= $SPRAY_USERS usernames from one IP"
echo "run at $(date '+%Y-%m-%dT%H:%M:%S') on $(hostname)"
echo

"$AWK" -v thr="$THRESHOLD" -v win="$((WINDOW_MIN * 60))" -v spray="$SPRAY_USERS" \
       -v year="$YEAR" -v alertfile="$ALERT_FILE" -v logname="$LOG" '
function field(name,   i) {                        # value of name=... on the current line
    for (i = 1; i <= NF; i++) if (index($i, name "=") == 1) return substr($i, length(name) + 2)
    return ""
}
function alert(msg) {
    print "ALERT " msg
    print strftime("%Y-%m-%dT%H:%M:%S") " ALERT " msg " source_log=" logname >> alertfile
    alerts++
}
BEGIN {
    PROCINFO["sorted_in"] = "@ind_str_asc"           # gawk: print IPs in a stable order
    split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", m, " ")
    for (i = 1; i <= 12; i++) mon[m[i]] = i
}
{
    fail = 0; ip = ""; user = ""
    if ($2 ~ /^campushield\[/) {                     # ---- CampusShield app format
        ts = $1; gsub(/[-T:]/, " ", ts); t = mktime(ts); stamp = $1
        ev = $3; user = field("user"); ip = field("ip")
        if (ev == "LOGIN_FAILED" || ev == "LOGIN_BLOCKED_LOCKED") fail = 1
        else if (ev == "ACCOUNT_LOCKED") { locked++; lockedlist = lockedlist " " user }
        else if (ev == "ACCESS_DENIED")  { denied++;  deniedlist = deniedlist " " user ":" field("path") }
    } else if ($0 ~ /sshd\[[0-9]+\]: Failed password for /) {   # ---- sshd format
        hms = $3; gsub(":", " ", hms); t = mktime(year " " mon[$1] " " $2 " " hms); stamp = $1 " " $2 " " $3
        for (i = 1; i <= NF; i++) {
            if ($i == "for")  user = ($(i + 1) == "invalid") ? $(i + 3) : $(i + 1)
            if ($i == "from") ip = $(i + 1)
        }
        fail = 1
    }
    if (fail && ip != "") {
        total++
        n[ip]++; times[ip] = times[ip] " " t; when[ip, n[ip]] = stamp
        if (!((ip, user) in seen)) { seen[ip, user] = 1; nusers[ip]++; ulist[ip] = ulist[ip] " " user }
    }
}
END {
    printf "failed logins found: %d from %d source IP(s)\n\n", total, length(n)
    printf "%-15s %8s %16s  %s\n", "source IP", "failures", "max in window", "usernames tried"
    for (ip in n) {
        cnt = split(substr(times[ip], 2), tt, " ")
        best = 0; lo = 1
        for (hi = 1; hi <= cnt; hi++) {             # sliding time window over this IP failures
            while (tt[hi] - tt[lo] > win) lo++
            if (hi - lo + 1 > best) { best = hi - lo + 1; bs = lo; be = hi }
        }
        printf "%-15s %8d %16d %s\n", ip, n[ip], best, ulist[ip]
        maxwin[ip] = best; first[ip] = when[ip, bs]; last[ip] = when[ip, be]
    }
    print ""
    for (ip in n) {
        if (maxwin[ip] >= thr)
            alert("BRUTE_FORCE ip=" ip " failures=" maxwin[ip] " between " first[ip] " and " last[ip] " users=" substr(ulist[ip], 2))
        if (nusers[ip] >= spray)
            alert("PASSWORD_SPRAY ip=" ip " distinct_users=" nusers[ip] " users=" substr(ulist[ip], 2))
    }
    if (alerts == 0) print "no alerts"
    print ""
    printf "ACCOUNT_LOCKED events: %d%s\n", locked, (locked ? " (" substr(lockedlist, 2) ")" : "")
    printf "ACCESS_DENIED events : %d%s\n", denied, (denied ? " (" substr(deniedlist, 2) ")" : "")
    printf "alerts raised: %d (appended to %s)\n", alerts, alertfile
}' "$LOG"
