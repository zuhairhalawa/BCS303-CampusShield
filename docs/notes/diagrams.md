# Diagrams

Generated diagrams (not evidence). Source: hand-written SVG in `diagrams/src/*.html`,
rendered to PNG at 2x scale with `python diagrams/render_diagrams.py` (Playwright + local Edge).

| File | Caption |
|---|---|
| `diagrams/architecture.png` | CampusShield architecture inside the isolated Kali lab: user roles in the authorized zone, the host firewall (TB1), the Flask portal and SQLite database separated by TB2, role separation by RBAC (TB3), logging and failed-login monitoring, and the unnecessary tcp/8000 backup share removed during hardening. |
| `diagrams/lab_network.png` | Kali lab topology: the cs_untrusted (10.10.50.66) and cs_staff (10.10.60.10) network namespaces joined to the root namespace by veth pairs, the iptables policy applied after hardening, the intended allowed/filtered/closed outcomes and the tshark capture point on cs-staff-h. |
| `diagrams/cloud_architecture.png` | Conceptual, provider-neutral cloud deployment for CampusShield (nothing deployed): load balancer and WAF in a public subnet, app tier and managed database in private subnets, plus IAM, secrets manager, KMS, logging/SIEM, backups and admin-access controls tagged C1–C11. |
| `diagrams/attack_defend_verify.png` | The baseline → validate → apply control → re-test → quantify loop used for every exercise, illustrated with the SQL-injection result (360 rows exposed before the fix, 0 after). |

Notes for the report writer:
- Lab-network and architecture diagrams describe the *intended* Kali lab design; the actual allowed/filtered/closed results must come from the Kali run evidence, not from the diagram.
- Cloud control tags: C1 TLS, C2 WAF, C3 app security group, C4 DB security group, C5 encryption at rest/KMS, C6 segmentation/NACLs, C7 IAM, C8 secrets manager, C9 logging/SIEM, C10 backups, C11 admin access via session manager.
