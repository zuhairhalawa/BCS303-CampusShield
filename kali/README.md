# Kali lab run

`kali/run_kali_lab.sh` produces the evidence for Task 1.4 (lab isolation), Task 2 (Nmap
before/after, validation, exposure control), Task 4.4 (re-test from the network), Task 5.1
(Linux users/groups/permissions), Task 5.2 (firewall allowed/denied, applied/removed),
Task 5.3 (monitoring) and the traffic-capture item (tshark, HTTP vs HTTPS).

Inside the Kali machine, two network namespaces (`cs_untrusted` 10.10.50.66 and `cs_staff`
10.10.60.10) act as lab zones with no default route. The iptables chain only matches the two
lab veth interfaces, so the machine's normal network connection is not changed.

## How the submitted evidence was produced (container run)

The evidence in `evidence/kali/` comes from the official Kali Linux image (`kalilinux/kali-rolling`)
running in a disposable Docker container that is attached **only** to an internal Docker network
(`docker network create --internal`: no route to the Internet or the host LAN) and has **no
published ports**. From the Windows host:

```bash
bash kali/docker/run_lab_container.sh
```

It builds `kali/docker/Dockerfile` (Kali + nmap, tshark, iptables, sqlite3, Flask), records the
network settings in `00_container_network.txt`, runs `kali/run_kali_lab.sh` as root inside the
container (capabilities NET_ADMIN, NET_RAW, SYS_ADMIN only, not `--privileged`), saves the
whole console output to `full_run_console.txt`, then removes the container and the network.

Why not the VMware VM: the Kali VM ("Kali Fresh", NAT adapter, shared folders and drag-and-drop
disabled - see `vm_settings.txt`) starts fine, but running commands in it from the host with
`vmrun` requires the guest login, which the automated run could not use.

## Running it in the Kali VM instead (same script, no changes)

```bash
git clone https://github.com/zuhairhalawa/BCS303-CampusShield.git   # private: gh auth login first
cd BCS303-CampusShield
sudo bash kali/run_kali_lab.sh            # 5-10 minutes, writes evidence/kali/
sudo bash kali/run_kali_lab.sh cleanup    # optional: remove lab users, groups, rules
```

The VM needs Internet (NAT) only if a tool is missing; the script installs missing packages.

## What each output file contains

| File | Content |
|---|---|
| `00_container_network.txt` | Docker image id, internal network (`internal=true`), no published ports |
| `vm_settings.txt` | the Kali VM's NAT adapter, disabled shared folders / drag-and-drop, snapshot |
| `00_environment.txt` | Kali version and tool versions |
| `01_lab_isolation.txt` | interfaces, routes, namespaces, "no route" proof |
| `02_baseline_deploy.txt` | weak baseline: vulnerable build as root, :8000 share, 666/777 files |
| `03_nmap_before.txt` + `nmap_before_untrusted.xml` | full TCP scan from the untrusted zone + safe NSE scripts |
| `04_validation.txt` | directory listing + HEAD of the database file, SQL injection row count |
| `05_linux_permissions.txt` | users/groups, before/after permission tests |
| `06_firewall.txt` | initial rules, applied rules, allowed/denied connections |
| `07_nmap_after.txt` + XML | same scan after hardening, from both zones, rule counters |
| `08_app_retest.txt` | SQL injection re-test against the secure build over the network |
| `09_firewall_removed.txt` | firewall removed -> reachable, re-applied -> blocked |
| `10_traffic_capture.txt` + `http_login.pcap`, `https_login.pcap` | cleartext HTTP vs TLS |
| `11_monitoring.txt` + `campushield_kali_app.log` | failed-login burst and the detector's ALERT |
| `SUMMARY.txt` | key lines from all steps |
| `full_run_console.txt` | the complete console output of the run |
