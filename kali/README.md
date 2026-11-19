# Kali lab run - what to do in the Kali VM

This produces the real evidence for Task 1.4 (lab isolation), Task 2 (Nmap before/after,
validation, exposure control), Task 4.4 (re-test from the network), Task 5.1 (Linux
users/groups/permissions), Task 5.2 (firewall allowed/denied, applied/removed), Task 5.3
(monitoring on the Kali run) and the rubric's traffic-capture item (tshark, HTTP vs HTTPS).

Everything stays inside the Kali VM. Two network namespaces (`cs_untrusted`, `cs_staff`)
act as lab zones with no default route. The iptables chain only matches the two lab veth
interfaces, so the VM's normal network connection is not changed.

## 1. Before you start (2 minutes)

1. In VMware: VM > Settings > Network Adapter. Take a screenshot of the adapter mode
   (NAT or Host-only). Save it as `evidence/kali/vmware_network_adapter.png`.
   This is the "VM network settings" part of the lab-isolation evidence.
2. The VM needs Internet (NAT) only if Flask or another tool is missing; the script runs
   `apt-get install` for anything missing.

## 2. Get the repo into Kali

The repo is private. Pick one:

```bash
# A) GitHub CLI (if installed in Kali)
gh auth login
gh repo clone zuhairhalawa/BCS303-CampusShield
# B) HTTPS clone with a personal access token when git asks for a password
git clone https://github.com/zuhairhalawa/BCS303-CampusShield.git
# C) Download the ZIP from GitHub in Windows and drag it into the VM, then unzip
```

## 3. Run it (about 5-10 minutes; the two full-port scans take the longest)

```bash
cd BCS303-CampusShield
sudo bash kali/run_kali_lab.sh
```

While it runs, take screenshots of the terminal at these points (they are the
"Screenshots" deliverable for the network part):
- the step 3 Nmap BEFORE output,
- the step 6 connectivity checks (staff zone 200, untrusted zone blocked),
- the step 7 Nmap AFTER output,
- the step 10 tshark output showing the cleartext form fields, then the TLS-only capture,
- the step 11 ALERT line.
Save them in `evidence/kali/` with short names (`kali_nmap_before.png`, ...).
Optional: open `evidence/kali/http_login.pcap` in Wireshark and screenshot the HTTP POST.

## 4. Send the evidence back

```bash
git add evidence/kali
git commit -m "Add Kali lab evidence: nmap before/after, firewall, permissions, tshark, monitoring"
git push
```
(or copy the `evidence/kali` folder back into the Windows repo).

Then rebuild the report so the Kali results are pulled in automatically:

```bash
python report/build_report.py     # on Windows with Word installed -> DOCX + PDF
```

## 5. Clean up afterwards (optional)

```bash
sudo bash kali/run_kali_lab.sh cleanup
```

## What each output file contains

| File | Content |
|---|---|
| `00_environment.txt` | Kali version, tool versions, `systemd-detect-virt` |
| `01_lab_isolation.txt` | interfaces, routes, namespaces, "no route" proof |
| `02_baseline_deploy.txt` | weak baseline: vulnerable build as root, :8000 share, 666/777 files |
| `03_nmap_before.txt` + `nmap_before_untrusted.xml` | full TCP scan from the untrusted zone + safe NSE scripts |
| `04_validation.txt` | directory listing + HEAD of the database file, Metasploit `dir_listing`/`http_version` (if installed), SQLi row count |
| `05_linux_permissions.txt` | users/groups, before/after permission tests |
| `06_firewall.txt` | initial rules, applied rules, allowed/denied connections |
| `07_nmap_after.txt` + XML | same scan after hardening, from both zones, rule counters |
| `08_app_retest.txt` | SQLi re-test against the secure build over the network |
| `09_firewall_removed.txt` | firewall removed -> reachable, re-applied -> blocked |
| `10_traffic_capture.txt` + `http_login.pcap`, `https_login.pcap` | cleartext HTTP vs TLS |
| `11_monitoring.txt` + `campushield_kali_app.log` | failed-login burst and the detector's ALERT |
| `SUMMARY.txt` | key lines from all steps |
