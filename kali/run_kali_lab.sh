#!/usr/bin/env bash
# =============================================================================
# CampusShield - Kali Linux lab run (Tasks 1.4, 2, 4.4, 5.1, 5.2, 5.3 + capture)
#
#   sudo bash kali/run_kali_lab.sh            # full evidence run (about 5-10 min)
#   sudo bash kali/run_kali_lab.sh cleanup    # remove lab users, groups, netns, rules
#
# Everything happens INSIDE this Kali VM. Two Linux network namespaces act as
# lab zones that have no route anywhere except the Kali host:
#   cs_untrusted 10.10.50.66  <-veth->  10.10.50.1 (Kali)   unauthorised zone
#   cs_staff     10.10.60.10  <-veth->  10.10.60.1 (Kali)   authorised campus zone
# Firewall rules only match the two lab veth interfaces, so the VM's normal
# network connection is never touched. No Internet hosts are scanned.
#
# Output: evidence/kali/*.txt, *.pcap, *.xml  (real command output)
# =============================================================================
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EV="$REPO/evidence/kali"
OPT=/opt/campushield
DB="$OPT/data/campushield.db"
LOGF="$OPT/logs/campushield.log"
UNTR_NS=cs_untrusted; UNTR_IP=10.10.50.66; UNTR_HOST=10.10.50.1
STAFF_NS=cs_staff;    STAFF_IP=10.10.60.10; STAFF_HOST=10.10.60.1
APP_PORT=5000; SHARE_PORT=8000
NMAP_OPTS=(-Pn -sS -sV -p- -T4 --max-retries 2 --reason)

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo bash kali/run_kali_lab.sh"; exit 1; }
mkdir -p "$EV"

# ---------------------------------------------------------------- helpers
CUR=""                                    # current evidence file
step() { CUR="$EV/$1"; : > "$CUR"; printf '\n### %s\n' "$2" | tee -a "$CUR"; }
note() { printf '%s\n' "$*" | tee -a "$CUR"; }
run()  { printf '\n$ %s\n' "$*" | tee -a "$CUR"; "$@" 2>&1 | tee -a "$CUR"; return "${PIPESTATUS[0]}"; }
sh_()  { printf '\n$ %s\n' "$1" | tee -a "$CUR"; bash -c "$1" 2>&1 | tee -a "$CUR"; }
in_ns(){ local ns=$1; shift; ip netns exec "$ns" "$@"; }

wait_port() { for _ in $(seq 1 40); do ss -ltn | grep -q ":$1 " && return 0; sleep 0.5; done; echo "port $1 did not open"; return 1; }
stop_app()   { pkill -f "$OPT/scripts/run_app.py" 2>/dev/null; sleep 1; }
stop_share() { pkill -f "http.server $SHARE_PORT" 2>/dev/null; sleep 1; }
cred()       { grep "^$1:" "$OPT/data/lab_credentials.txt" | cut -d: -f2-; }

start_app() {  # $1 = secure|vulnerable  $2 = run-as user  $3.. extra args
  local mode=$1 user=$2; shift 2
  stop_app
  runuser -u "$user" -- env CAMPUSHIELD_DB="$DB" CAMPUSHIELD_LOG_DIR="$OPT/logs" \
      python3 "$OPT/scripts/run_app.py" --mode "$mode" --host 0.0.0.0 --port $APP_PORT \
      --allow-lab-exposure "$@" >/dev/null 2>&1 &
  wait_port $APP_PORT
}

lab_login() {  # ns base user password cookiejar -> prints HTTP code
  in_ns "$1" curl -sk -m 8 -c "$5" -b "$5" -o /dev/null -w '%{http_code}' \
     --data-urlencode "username=$3" --data-urlencode "password=$4" "$2/login"
}

fw_remove() {
  iptables -D INPUT -i cs-untr-h -j CS_LAB_IN 2>/dev/null
  iptables -D INPUT -i cs-staff-h -j CS_LAB_IN 2>/dev/null
  iptables -F CS_LAB_IN 2>/dev/null; iptables -X CS_LAB_IN 2>/dev/null
}
fw_apply() {
  fw_remove
  iptables -N CS_LAB_IN
  iptables -A CS_LAB_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A CS_LAB_IN -s 10.10.60.0/24 -p tcp --dport $APP_PORT -m conntrack --ctstate NEW -j ACCEPT
  iptables -A CS_LAB_IN -m limit --limit 20/min -j LOG --log-prefix "CS-FW-DROP "
  iptables -A CS_LAB_IN -j DROP
  iptables -I INPUT 1 -i cs-untr-h -j CS_LAB_IN
  iptables -I INPUT 1 -i cs-staff-h -j CS_LAB_IN
}

net_down() {
  ip netns del $UNTR_NS 2>/dev/null; ip netns del $STAFF_NS 2>/dev/null
  ip link del cs-untr-h 2>/dev/null; ip link del cs-staff-h 2>/dev/null
}

cleanup_all() {
  stop_app; stop_share; fw_remove; net_down
  for u in cs_app cs_registrar cs_admin cs_student; do userdel "$u" 2>/dev/null; done
  for g in cs_records cs_audit; do groupdel "$g" 2>/dev/null; done
  echo "Lab users, groups, namespaces and firewall chain removed. $OPT kept (delete manually if wanted)."
}

if [ "${1:-run}" = "cleanup" ]; then cleanup_all; exit 0; fi

# ============================================================== 0. tools
step 00_environment.txt "0. Environment and tools"
NEED=()
for t in nmap tshark sqlite3 curl iptables ip openssl nc ss runuser; do command -v "$t" >/dev/null || NEED+=("$t"); done
python3 -c "import flask, cryptography, requests" 2>/dev/null || NEED+=(python3-flask python3-cryptography python3-requests)
if [ ${#NEED[@]} -gt 0 ]; then
  note "Installing missing packages: ${NEED[*]}"
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
     nmap tshark sqlite3 curl iptables iproute2 openssl netcat-openbsd python3-flask python3-cryptography python3-requests >/dev/null
fi
run date
run uname -a
sh_ "grep PRETTY_NAME /etc/os-release"
sh_ "systemd-detect-virt || true"
sh_ "nmap --version | head -1; tshark --version | head -1; sqlite3 --version; openssl version; python3 --version"

# =================================================== 1. lab network (Task 1.4)
step 01_lab_isolation.txt "1. Isolated lab network (Task 1 - lab isolation evidence)"
net_down
ip netns add $UNTR_NS; ip netns add $STAFF_NS
ip link add cs-untr-h type veth peer name cs-untr-n
ip link add cs-staff-h type veth peer name cs-staff-n
ip link set cs-untr-n netns $UNTR_NS; ip link set cs-staff-n netns $STAFF_NS
ip addr add $UNTR_HOST/24 dev cs-untr-h;  ip link set cs-untr-h up
ip addr add $STAFF_HOST/24 dev cs-staff-h; ip link set cs-staff-h up
in_ns $UNTR_NS ip addr add $UNTR_IP/24 dev cs-untr-n;   in_ns $UNTR_NS ip link set cs-untr-n up;   in_ns $UNTR_NS ip link set lo up
in_ns $STAFF_NS ip addr add $STAFF_IP/24 dev cs-staff-n; in_ns $STAFF_NS ip link set cs-staff-n up; in_ns $STAFF_NS ip link set lo up
note "Kali VM interfaces and routes (VM network settings):"
run ip -br addr
run ip route
run ip netns list
note "Each lab zone only has a route to its own /24 - no default gateway, no Internet:"
run ip netns exec $UNTR_NS ip -br addr
run ip netns exec $UNTR_NS ip route
run ip netns exec $STAFF_NS ip route
sh_ "ip netns exec $UNTR_NS ip route get 1.1.1.1 || echo '=> no route: the untrusted zone cannot leave the lab'"
sh_ "ip netns exec $UNTR_NS ip route get $STAFF_IP || echo '=> no route: zones cannot reach each other directly'"
run ip netns exec $UNTR_NS ping -c 2 -W 1 $UNTR_HOST

# ============================================ 2. insecure baseline deployment
step 02_baseline_deploy.txt "2. Baseline deployment (intentionally weak, as found in the preliminary review)"
stop_app; stop_share
rm -rf "$OPT"; mkdir -p "$OPT"
cp -r "$REPO/app" "$REPO/scripts" "$REPO/requirements.txt" "$OPT/"
mkdir -p "$OPT/data" "$OPT/logs"
run env CAMPUSHIELD_DB="$DB" python3 "$OPT/scripts/init_db.py"
chmod 777 "$OPT/data" "$OPT/logs"; chmod 666 "$DB" "$OPT/data/lab_credentials.txt"
start_app vulnerable root
( cd "$OPT/data" && python3 -m http.server $SHARE_PORT --bind 0.0.0.0 >/dev/null 2>&1 & )
wait_port $SHARE_PORT
note "Baseline problems: app runs as root, vulnerable build, bound to 0.0.0.0,"
note "an extra 'backup share' (python http.server :$SHARE_PORT) publishes the data folder, files are 666/777."
run ls -la "$OPT/data" "$OPT/logs"
sh_ "ss -ltnp | grep -E ':($APP_PORT|$SHARE_PORT) '"
sh_ "ps -o user,pid,cmd -C python3 | grep -E 'run_app|http.server'"
run iptables -S

# ===================================================== 3. Nmap before (Task 2.1)
step 03_nmap_before.txt "3. Nmap BEFORE hardening (scanner in the unauthorised zone)"
run ip netns exec $UNTR_NS nmap "${NMAP_OPTS[@]}" -oX "$EV/nmap_before_untrusted.xml" $UNTR_HOST
note ""
note "Safe NSE scripts (default/safe category, read-only HTTP requests):"
run ip netns exec $UNTR_NS nmap -Pn -p $APP_PORT,$SHARE_PORT --script http-title,http-headers,http-methods $UNTR_HOST

# ========================================== 4. safe weakness validation (Task 2.2)
step 04_validation.txt "4. Non-destructive validation of the weaknesses"
note "4a. Backup share: is directory listing enabled and is the database downloadable?"
sh_ "ip netns exec $UNTR_NS curl -s http://$UNTR_HOST:$SHARE_PORT/ | grep -o 'href=\"[^\"]*\"'"
note "Only the response headers are requested (HEAD) - no file contents are downloaded:"
run ip netns exec $UNTR_NS curl -sI http://$UNTR_HOST:$SHARE_PORT/campushield.db
if command -v msfconsole >/dev/null; then
  note ""
  note "4b. Metasploit auxiliary scanners (read-only): dir_listing and http_version"
  run timeout 300 ip netns exec $UNTR_NS msfconsole -q -n -x \
    "use auxiliary/scanner/http/dir_listing; set RHOSTS $UNTR_HOST; set RPORT $SHARE_PORT; run; use auxiliary/scanner/http/http_version; set RHOSTS $UNTR_HOST; set RPORT $APP_PORT; run; exit"
else
  note "msfconsole not installed - validation above uses curl/nmap only."
fi
note ""
note "4c. SQL injection reachable from the unauthorised zone (student account, vulnerable build)"
JAR=$(mktemp)
note "login s2026001 from $UNTR_IP -> HTTP $(lab_login $UNTR_NS http://$UNTR_HOST:$APP_PORT s2026001 "$(cred s2026001)" "$JAR")"
sh_ "ip netns exec $UNTR_NS curl -s -b $JAR -G --data-urlencode \"course=BCS210' OR '1'='1\" http://$UNTR_HOST:$APP_PORT/attendance | grep -o '[0-9]* row(s) returned'"
rm -f "$JAR"

# ======================================== 5. Linux hardening (Task 5.1)
step 05_linux_permissions.txt "5. Linux users, groups and least-privilege file permissions"
stop_app; stop_share
getent group cs_records >/dev/null || groupadd cs_records
getent group cs_audit   >/dev/null || groupadd cs_audit
id cs_app       >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin cs_app
id cs_registrar >/dev/null 2>&1 || useradd -m -s /bin/bash -G cs_records cs_registrar
id cs_admin     >/dev/null 2>&1 || useradd -m -s /bin/bash -G cs_audit cs_admin
id cs_student   >/dev/null 2>&1 || useradd -m -s /bin/bash cs_student
passwd -l cs_registrar >/dev/null; passwd -l cs_admin >/dev/null; passwd -l cs_student >/dev/null
run id cs_app
run id cs_registrar
run id cs_admin
run id cs_student
note ""
note "BEFORE (baseline 666/777): can the unauthorised OS account read the student database?"
sh_ "ls -l $DB"
sh_ "runuser -u cs_student -- sqlite3 -readonly $DB 'SELECT COUNT(*) AS students_readable FROM students;'"
sh_ "runuser -u cs_student -- sh -c 'echo tampered >> $LOGF' && echo '=> cs_student could WRITE to the application log'"
note ""
note "APPLY least privilege:"
sh_ "chown -R root:root $OPT/app $OPT/scripts && chmod -R u=rwX,go=rX $OPT/app $OPT/scripts"
sh_ "chown cs_app:cs_records $OPT/data && chmod 750 $OPT/data"
sh_ "chown cs_app:cs_records $DB && chmod 640 $DB"
sh_ "chown cs_app:cs_app $OPT/data/lab_credentials.txt && chmod 600 $OPT/data/lab_credentials.txt"
sh_ "chown -R cs_app:cs_audit $OPT/logs && chmod 750 $OPT/logs && find $OPT/logs -type f -exec chmod 640 {} +"
run ls -la "$OPT" "$OPT/data" "$OPT/logs"
note ""
note "AFTER - authorised vs unauthorised access tests:"
sh_ "runuser -u cs_registrar -- sqlite3 -readonly $DB 'SELECT COUNT(*) AS students_readable FROM students;' && echo '=> cs_registrar (cs_records) ALLOWED'"
sh_ "runuser -u cs_student -- sqlite3 -readonly $DB 'SELECT COUNT(*) FROM students;' || echo '=> cs_student DENIED'"
sh_ "runuser -u cs_student -- cat $OPT/data/lab_credentials.txt || echo '=> cs_student DENIED'"
sh_ "runuser -u cs_registrar -- cat $OPT/data/lab_credentials.txt || echo '=> cs_registrar DENIED (only the service account)'"
sh_ "runuser -u cs_admin -- tail -n 2 $LOGF && echo '=> cs_admin (cs_audit) ALLOWED to read logs'"
sh_ "runuser -u cs_registrar -- tail -n 1 $LOGF || echo '=> cs_registrar DENIED (separation of duties)'"
sh_ "runuser -u cs_student -- sh -c 'echo tampered >> $LOGF' || echo '=> cs_student DENIED write to log'"

# ====================================== 6. exposure control + firewall (Task 2.4, 5.2)
step 06_firewall.txt "6. Remove unnecessary service, run secure build as cs_app, host firewall"
note "Initial firewall state:"
run iptables -S
start_app secure cs_app
note "Backup share on :$SHARE_PORT is NOT restarted (unnecessary service removed)."
sh_ "ss -ltnp | grep -E ':($APP_PORT|$SHARE_PORT) '"
sh_ "ps -o user,pid,cmd -C python3 | grep run_app"
fw_apply
note ""
note "Firewall rules applied (only the lab veth interfaces are affected):"
run iptables -S CS_LAB_IN
sh_ "iptables -S INPUT | head -5"
note ""
note "Connectivity checks:"
sh_ "ip netns exec $STAFF_NS curl -s -m 5 -o /dev/null -w 'staff zone   -> :$APP_PORT  HTTP %{http_code}\n' http://$STAFF_HOST:$APP_PORT/login"
sh_ "ip netns exec $UNTR_NS curl -s -m 5 -o /dev/null -w 'untrusted    -> :$APP_PORT  HTTP %{http_code}\n' http://$UNTR_HOST:$APP_PORT/login || echo '=> untrusted zone BLOCKED (timeout)'"
sh_ "ip netns exec $STAFF_NS nc -zv -w 3 $STAFF_HOST $SHARE_PORT || echo '=> :$SHARE_PORT closed/blocked'"
sh_ "ip netns exec $STAFF_NS nc -zv -w 3 $STAFF_HOST 22 || echo '=> other ports from staff zone blocked'"

# ===================================================== 7. Nmap after (Task 2.4)
step 07_nmap_after.txt "7. Nmap AFTER hardening - same command as step 3"
run ip netns exec $UNTR_NS nmap "${NMAP_OPTS[@]}" -oX "$EV/nmap_after_untrusted.xml" $UNTR_HOST
note ""
note "Same scan from the authorised staff zone:"
run ip netns exec $STAFF_NS nmap "${NMAP_OPTS[@]}" -oX "$EV/nmap_after_staff.xml" $STAFF_HOST
note ""
note "Packets matched by each firewall rule (pkts/bytes counters):"
run iptables -L CS_LAB_IN -v -n
sh_ "dmesg | grep CS-FW-DROP | tail -n 5"

# ================================== 8. re-test of the app fix from the network (Task 4.4)
step 08_app_retest.txt "8. Re-test SQL injection against the secure build from the authorised zone"
JAR=$(mktemp); BASE=http://$STAFF_HOST:$APP_PORT
note "login s2026001 from $STAFF_IP -> HTTP $(lab_login $STAFF_NS $BASE s2026001 "$(cred s2026001)" "$JAR")"
COURSE=$(in_ns $STAFF_NS curl -s -b "$JAR" $BASE/attendance | grep -o '<code>[A-Z]\{3\}[0-9]\{3\}</code>' | head -1 | sed 's/<[^>]*>//g')
sh_ "ip netns exec $STAFF_NS curl -s -b $JAR -G --data-urlencode 'course=$COURSE' $BASE/attendance | grep -o '[0-9]* row(s) returned'"
sh_ "ip netns exec $STAFF_NS curl -s -b $JAR -G --data-urlencode \"course=$COURSE' OR '1'='1\" $BASE/attendance | grep -oE '[0-9]+ row\(s\) returned|Course code must look like BCS303'"
rm -f "$JAR"

# ============================================ 9. firewall removed / re-applied
step 09_firewall_removed.txt "9. Firewall REMOVED then re-applied (shows the rule is what blocks access)"
fw_remove
run iptables -S INPUT
sh_ "ip netns exec $UNTR_NS curl -s -m 5 -o /dev/null -w 'untrusted -> :$APP_PORT  HTTP %{http_code}  (firewall removed: reachable again)\n' http://$UNTR_HOST:$APP_PORT/login"
fw_apply
sh_ "ip netns exec $UNTR_NS curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://$UNTR_HOST:$APP_PORT/login || echo 'untrusted -> :$APP_PORT  BLOCKED again (firewall re-applied)'"

# =========================================== 10. traffic capture (rubric: Wireshark)
step 10_traffic_capture.txt "10. Traffic capture with tshark on the staff-zone interface"
note "10a. HTTP login with a deliberately WRONG password (no real lab password is captured)"
tshark -i cs-staff-h -f "tcp port $APP_PORT" -w "$EV/http_login.pcap" -a duration:12 >/dev/null 2>&1 &
TS=$!; sleep 3
JAR=$(mktemp)
lab_login $STAFF_NS http://$STAFF_HOST:$APP_PORT s2026001 "Wrong-Demo-Pass1" "$JAR" >/dev/null
in_ns $STAFF_NS curl -s -o /dev/null http://$STAFF_HOST:$APP_PORT/login
wait $TS; rm -f "$JAR"
run tshark -r "$EV/http_login.pcap" -q -z conv,tcp
run tshark -r "$EV/http_login.pcap" -Y http.request -T fields -E header=y -e frame.number -e ip.src -e ip.dst -e tcp.dstport -e http.request.method -e http.request.uri -e http.file_data
note ""
note "10b. Same login over HTTPS (self-signed lab certificate made with openssl)"
mkdir -p "$OPT/tls"
run openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=campushield.lab" \
     -keyout "$OPT/tls/key.pem" -out "$OPT/tls/cert.pem"
chown -R cs_app:cs_app "$OPT/tls"; chmod 600 "$OPT/tls/key.pem"
start_app secure cs_app --tls --cert "$OPT/tls/cert.pem" --key "$OPT/tls/key.pem"
tshark -i cs-staff-h -f "tcp port $APP_PORT" -w "$EV/https_login.pcap" -a duration:12 >/dev/null 2>&1 &
TS=$!; sleep 3
JAR=$(mktemp)
lab_login $STAFF_NS https://$STAFF_HOST:$APP_PORT s2026001 "Wrong-Demo-Pass1" "$JAR" >/dev/null
wait $TS; rm -f "$JAR"
run tshark -r "$EV/https_login.pcap" -q -z conv,tcp
run tshark -r "$EV/https_login.pcap" -Y "tls" -T fields -E header=y -e frame.number -e ip.src -e ip.dst -e tls.record.content_type -e tls.handshake.type
sh_ "tshark -r $EV/https_login.pcap -Y http.request | wc -l | sed 's/^/HTTP requests readable in the HTTPS capture: /'"
start_app secure cs_app

# ============================================= 11. monitoring (Task 5.3)
step 11_monitoring.txt "11. Detect repeated failed logins (controlled burst from the staff zone)"
JAR=$(mktemp)
for i in 1 2 3 4 5 6; do
  note "attempt $i: HTTP $(lab_login $STAFF_NS http://$STAFF_HOST:$APP_PORT s2026002 "Guess-$i-Wrong!" "$JAR")"
done
rm -f "$JAR"; sleep 1
run tail -n 8 "$LOGF"
run bash "$REPO/monitoring/detect_failed_logins.sh" "$LOGF" 5 10
note ""
note "Firewall drop log (kernel) - evidence of blocked probes from the untrusted zone:"
sh_ "dmesg | grep -c CS-FW-DROP | sed 's/^/CS-FW-DROP log lines: /'"
cp "$LOGF" "$EV/campushield_kali_app.log"

# ================================================== 12. summary + tidy up
step SUMMARY.txt "SUMMARY (key lines pulled from the step files)"
sh_ "grep -E '^[0-9]+/tcp' $EV/03_nmap_before.txt | sed 's/^/BEFORE untrusted: /'"
sh_ "grep -E '^[0-9]+/tcp|ignored states|filtered' $EV/07_nmap_after.txt | sed 's/^/AFTER: /'"
sh_ "grep -hE 'row\(s\) returned|Course code must' $EV/04_validation.txt $EV/08_app_retest.txt"
sh_ "grep -hE '=>' $EV/05_linux_permissions.txt $EV/06_firewall.txt $EV/09_firewall_removed.txt"
sh_ "grep -h 'HTTP' $EV/06_firewall.txt | grep zone"
sh_ "grep -h 'ALERT' $EV/11_monitoring.txt"

stop_app; fw_remove; net_down
[ -n "${SUDO_USER:-}" ] && chown -R "$SUDO_USER":"$SUDO_USER" "$EV" "$REPO/monitoring" 2>/dev/null
echo
echo "Done. Evidence is in $EV . Lab network and firewall chain were removed;"
echo "users/groups stay for screenshots (remove with: sudo bash kali/run_kali_lab.sh cleanup)."
