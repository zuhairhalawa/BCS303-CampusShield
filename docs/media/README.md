# Media used in the main README

| File | What it is | How it was made |
|---|---|---|
| `campusshield-overview.png` | Hero banner | Composed page containing two real screenshots of the running portal |
| `login.png`, `admin-dashboard.png`, `admin-audit-log.png`, `registrar-students.png`, `registrar-mark-attendance.png`, `student-dashboard.png` | Portal pages | Playwright (Edge) screenshots of the secure build on 127.0.0.1 |
| `sqli-before-after.png`, `xss-before-after.png`, `lockout-rbac.png` | Before/after pairs | Playwright screenshots of both builds with the same input |
| `app-demo.gif`, `sqli-demo.gif`, `xss-demo.gif` | Animated walk-throughs | Sequential Playwright screenshots of real runs, caption bar added with Pillow |
| `nmap-before.png`, `nmap-after.png`, `firewall-checks.png`, `linux-permissions.png`, `traffic-capture.png`, `kali-monitoring-alert.png`, `monitoring-alerts.png` | Terminal views | **Renderings** of saved output files in `evidence/` (the title bar names the file) - not live screen captures |
| `security-scorecard.png` | Summary table | Rendered from the values in the report's scorecard |
| `architecture.png`, `cloud-architecture.png` | Diagrams | Our design diagrams (`diagrams/src`) |

Regenerate everything with `python scripts/make_media.py all`. No passwords, session tokens or
keys appear in any image: passwords are only typed into masked fields.
