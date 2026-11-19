"""Generate the README media in docs/media/ from the REAL running app and REAL evidence files.

    python scripts/make_media.py app        # browser screenshots + 3 GIFs (starts both builds on 127.0.0.1)
    python scripts/make_media.py evidence   # terminal-style renders of evidence/kali + monitoring output files
    python scripts/make_media.py all

* Screenshots and GIF frames are taken by Playwright (Microsoft Edge) from the running portal.
  Passwords are typed only into masked password fields; no credentials or tokens are shown.
* Terminal images are RENDERINGS of captured output files. Each one says so in its title bar and
  names the source file - they are not screen captures of a live terminal.
"""
import html
import io
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "demonstrations"))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

MEDIA = ROOT / "docs" / "media"
W, H = 1100, 640


# ---------------------------------------------------------------- helpers
def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def caption(img: Image.Image, text: str, color=(31, 78, 121)) -> Image.Image:
    """Add a caption bar under a frame."""
    bar = 46
    out = Image.new("RGB", (img.width, img.height + bar), (255, 255, 255))
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    d.rectangle([0, img.height, img.width, img.height + bar], fill=color)
    d.text((18, img.height + 11), text, font=font(20, True), fill=(255, 255, 255))
    return out


def png(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")


def save_gif(frames, durations, name):
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    path = MEDIA / name
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
    print(f"  {name}: {len(frames)} frames, {sum(durations) / 1000:.1f} s, {path.stat().st_size // 1024} KB")


def side_by_side(left: Image.Image, right: Image.Image, ltxt, rtxt, name):
    gap, head = 24, 54
    w = left.width + right.width + gap
    out = Image.new("RGB", (w, max(left.height, right.height) + head), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for x, txt, col in ((0, ltxt, (164, 22, 26)), (left.width + gap, rtxt, (42, 157, 143))):
        d.rounded_rectangle([x, 6, x + 26 + d.textlength(txt, font=font(22, True)), 44], radius=19, fill=col)
        d.text((x + 13, 11), txt, font=font(22, True), fill=(255, 255, 255))
    out.paste(left, (0, head))
    out.paste(right, (left.width + gap, head))
    out.save(MEDIA / name, optimize=True)
    print("  " + name)


# ---------------------------------------------------------------- app media
def app_media():
    from playwright.sync_api import sync_playwright
    from lab_servers import SECURE, VULN, db, start_servers, stop_servers
    creds = db.read_credentials()
    procs = start_servers()
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(channel="msedge")

            def new_page():
                return br.new_context(viewport={"width": W, "height": H}).new_page()

            def login(page, base, user, frames=None, label=None):
                page.goto(f"{base}/login")
                page.fill("input[name=username]", user)
                page.fill("input[name=password]", creds[user])        # masked field
                if frames is not None:
                    frames.append(caption(png(page), label))
                page.click("button[type=submit]")
                page.wait_for_load_state()

            # ---------- still screenshots
            pg = new_page(); pg.goto(f"{SECURE}/login"); png(pg).save(MEDIA / "login.png")
            login(pg, SECURE, "admin1"); pg.goto(f"{SECURE}/admin/users"); png(pg).save(MEDIA / "admin-dashboard.png")
            pg.goto(f"{SECURE}/admin/audit"); png(pg).save(MEDIA / "admin-audit-log.png")
            pg = new_page(); login(pg, SECURE, "registrar1"); png(pg).save(MEDIA / "registrar-students.png")
            pg.goto(f"{SECURE}/registrar/attendance"); png(pg).save(MEDIA / "registrar-mark-attendance.png")
            pg = new_page(); login(pg, SECURE, "s2026001")
            course = pg.locator("code").first.inner_text()
            pg.goto(f"{SECURE}/attendance?course={course}"); png(pg).save(MEDIA / "student-dashboard.png")
            print("  login.png, admin-dashboard.png, admin-audit-log.png, registrar-*.png, student-dashboard.png")

            # ---------- GIF 1: application walkthrough
            fr, du = [], []
            pg = new_page(); pg.goto(f"{SECURE}/login")
            fr.append(caption(png(pg), "CampusShield portal - secure build on 127.0.0.1:5000")); du.append(1300)
            login(pg, SECURE, "registrar1", fr, "Registrar signs in (password field is masked)"); du.append(1100)
            fr.append(caption(png(pg), "Registrar: all 20 synthetic student records")); du.append(1500)
            pg.goto(f"{SECURE}/search?q=Haddad")
            fr.append(caption(png(pg), "Registrar: search students by name")); du.append(1300)
            pg.goto(f"{SECURE}/registrar/attendance")
            fr.append(caption(png(pg), "Registrar: mark attendance / register a student")); du.append(1300)
            pg = new_page(); login(pg, SECURE, "s2026001")
            pg.goto(f"{SECURE}/attendance?course={course}")
            fr.append(caption(png(pg), "Student: sees only their own attendance")); du.append(1500)
            pg.goto(f"{SECURE}/students")
            fr.append(caption(png(pg), "Student opens a registrar page -> 403 (RBAC), logged as ACCESS_DENIED",
                              (164, 22, 26))); du.append(1600)
            pg = new_page(); login(pg, SECURE, "admin1"); pg.goto(f"{SECURE}/admin/users")
            fr.append(caption(png(pg), "Administrator: accounts, lockout status, unlock")); du.append(1500)
            save_gif(fr, du, "app-demo.gif")

            # ---------- GIF 2: SQL injection vulnerable vs secure
            payload = f"{course}' OR '1'='1"
            fr, du = [], []
            for base, tag, col in ((VULN, "VULNERABLE build :5001", (164, 22, 26)), (SECURE, "SECURE build :5000", (42, 157, 143))):
                pg = new_page(); login(pg, base, "s2026001")
                pg.goto(f"{base}/attendance?course={course}")
                fr.append(caption(png(pg), f"{tag} - normal query: the student's own 6 rows", col)); du.append(1400)
                pg.fill("input[name=course]", payload)
                fr.append(caption(png(pg), f"{tag} - same student types:  {payload}", col)); du.append(1400)
                pg.click("button[type=submit]"); pg.wait_for_load_state()
                msg = ("360 rows of ALL 20 students returned" if base == VULN
                       else "input rejected, 0 rows - parameterised query + allow-list")
                fr.append(caption(png(pg), f"{tag} - {msg}", col)); du.append(2200)
            save_gif(fr, du, "sqli-demo.gif")
            side_by_side(fr[2].crop((0, 0, W, H)), fr[5].crop((0, 0, W, H)),
                         "VULNERABLE: 360 rows leaked", "SECURE: rejected, 0 rows", "sqli-before-after.png")

            # ---------- GIF 3: reflected XSS vulnerable vs secure
            xss = ("<script>document.body.insertAdjacentHTML('afterbegin','<h2 style=\"color:#a4161a\">"
                   "XSS DEMO: script from the link ran</h2>')</script>")
            fr, du = [], []
            for base, tag, col in ((VULN, "VULNERABLE build :5001", (164, 22, 26)), (SECURE, "SECURE build :5000", (42, 157, 143))):
                pg = new_page(); login(pg, base, "registrar1")
                pg.goto(f"{base}/search")
                fr.append(caption(png(pg), f"{tag} - registrar is signed in", col)); du.append(1100)
                pg.goto(f"{base}/search?q={quote(xss)}")
                msg = ("crafted link opened: the injected script RAN" if base == VULN
                       else "same link: shown as text, nothing runs (escaping + CSP)")
                fr.append(caption(png(pg), f"{tag} - {msg}", col)); du.append(2300)
            save_gif(fr, du, "xss-demo.gif")
            side_by_side(fr[1].crop((0, 0, W, H)), fr[3].crop((0, 0, W, H)),
                         "VULNERABLE: script executed", "SECURE: rendered as text", "xss-before-after.png")

            # ---------- lockout + RBAC composite
            pg = new_page()
            for i in range(5):
                pg.goto(f"{SECURE}/login"); pg.fill("input[name=username]", "s2026020")
                pg.fill("input[name=password]", f"Wrong-{i}-guess!"); pg.click("button[type=submit]")
            login(pg, SECURE, "s2026020")
            locked = png(pg)
            adm = new_page(); login(adm, SECURE, "admin1"); adm.goto(f"{SECURE}/admin/users")
            admin_locked = png(adm)
            adm.click("form[action$='/admin/unlock/s2026020'] button")      # restore the account
            side_by_side(locked, admin_locked, "5 wrong passwords: correct one refused",
                         "Admin view: account locked, can unlock", "lockout-rbac.png")
            br.close()
    finally:
        stop_servers(procs)


# ---------------------------------------------------------------- evidence renders
TERM_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#fff;font-family:Segoe UI,Arial,sans-serif}}
.win{{width:{w}px;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.25);margin:12px}}
.bar{{background:#2d333b;color:#cdd9e5;font-size:14px;padding:9px 14px;display:flex;gap:8px;align-items:center}}
.dot{{width:12px;height:12px;border-radius:50%;display:inline-block}}
.src{{margin-left:10px;opacity:.9}}
pre{{margin:0;background:#0d1117;color:#e6edf3;font:14px/1.45 Consolas,monospace;padding:14px 16px;white-space:pre-wrap}}
.cmd{{color:#79c0ff}} .ok{{color:#56d364}} .bad{{color:#ff7b72}} .warn{{color:#e3b341}} .dim{{color:#8b949e}}
</style></head><body><div class="win" id="t"><div class="bar"><span class="dot" style="background:#ff5f56"></span>
<span class="dot" style="background:#ffbd2e"></span><span class="dot" style="background:#27c93f"></span>
<span class="src">{title}</span></div><pre>{body}</pre></div></body></html>"""


def colour(line):
    e = html.escape(line)
    if line.startswith("$ "):
        return f'<span class="cmd">{e}</span>'
    if re.search(r"ALERT|DENIED|BLOCKED|Permission denied|filtered|DROP|cleartext|leaked", line):
        return f'<span class="bad">{e}</span>' if "ALERT" in line or "leak" in line else f'<span class="warn">{e}</span>'
    if re.search(r"\bopen\b|ALLOWED|HTTP 200|ACCEPT|succeeded", line):
        return f'<span class="ok">{e}</span>'
    if line.startswith("###") or line.startswith("#"):
        return f'<span class="dim">{e}</span>'
    return e


def render_terminal(page, src_rel, lines, out_name, width=1060):
    title = f"Rendered from real output file: {src_rel}"
    page.set_content(TERM_HTML.format(w=width, title=html.escape(title),
                                      body="\n".join(colour(l[:125]) for l in lines)))
    page.locator("#t").screenshot(path=str(MEDIA / out_name))
    print("  " + out_name)


def pick(rel, regex=None, limit=40):
    lines = (ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    if regex:
        lines = [l for l in lines if re.search(regex, l)]
    return lines[:limit]


def evidence_media():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge")
        page = br.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1.5)
        k = "evidence/kali/"
        if (ROOT / k / "SUMMARY.txt").exists():
            render_terminal(page, k + "03_nmap_before.txt",
                            pick(k + "03_nmap_before.txt", r"^(\$ ip netns exec cs_untrusted nmap -Pn -sS|PORT|[0-9]+/tcp|Nmap done|Not shown)", 14),
                            "nmap-before.png")
            render_terminal(page, k + "07_nmap_after.txt",
                            pick(k + "07_nmap_after.txt", r"^(\$ ip netns exec cs_\w+ nmap|PORT|[0-9]+/tcp|Nmap done|Not shown|All [0-9]+ scanned)", 16),
                            "nmap-after.png")
            render_terminal(page, k + "06_firewall.txt + 09_firewall_removed.txt",
                            pick(k + "06_firewall.txt", r"^(-N|-A CS_LAB_IN|staff zone|untrusted|=>)", 14)
                            + pick(k + "09_firewall_removed.txt", r"untrusted", 4), "firewall-checks.png")
            render_terminal(page, k + "05_linux_permissions.txt",
                            pick(k + "05_linux_permissions.txt", r"^(-rw|drw|=>|[0-9]+$|.*Permission denied|BEFORE|AFTER)", 30),
                            "linux-permissions.png")
            render_terminal(page, k + "10_traffic_capture.txt",
                            pick(k + "10_traffic_capture.txt", r"^(\$ tshark -r|frame\.number|[0-9]+\s+10\.|HTTP requests readable|10\.10\.60)", 22),
                            "traffic-capture.png")
            render_terminal(page, k + "11_monitoring.txt",
                            pick(k + "11_monitoring.txt", r"attempt|ALERT|ACCOUNT_LOCKED events|failed logins found|DROP", 16),
                            "kali-monitoring-alert.png")
        render_terminal(page, "evidence/monitoring/detect_app_log_output.txt",
                        pick("evidence/monitoring/detect_app_log_output.txt", None, 19), "monitoring-alerts.png")
        br.close()


HERO_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0}} #h{{width:1600px;height:720px;background:#14213d;position:relative;overflow:hidden;font-family:Segoe UI,Arial}}
.t{{position:absolute;left:70px;top:90px;color:#fff}} h1{{font:700 84px Cambria,Georgia,serif;margin:0}}
.sub{{font-size:28px;color:#cfd8e6;margin:12px 0 40px}}
.stat{{display:flex;gap:26px}} .s{{background:#1f2f52;border-radius:14px;padding:16px 20px;width:150px}}
.s b{{display:block;font:700 34px Cambria,serif}} .s span{{font-size:15px;color:#cfd8e6}}
.r{{color:#ff8a8a}} .g{{color:#6fd3c4}}
.pill{{display:inline-block;border-radius:18px;padding:7px 16px;font-weight:700;font-size:17px;margin-right:10px;color:#fff}}
img{{position:absolute;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
.foot{{position:absolute;left:70px;bottom:40px;color:#8d99ae;font-size:16px}}
</style></head><body><div id="h"><div class="t"><h1>CampusShield</h1>
<div class="sub">Attack &middot; defend &middot; verify &mdash; a BCS303 security lab</div>
<span class="pill" style="background:#c1121f">vulnerable build</span><span class="pill" style="background:#2a9d8f">secure build</span>
<div class="stat" style="margin-top:34px">
<div class="s"><b class="r">360&rarr;0</b><span>rows leaked by SQL injection</span></div>
<div class="s"><b class="g">333,878&times;</b><span>slower password guessing</span></div>
<div class="s"><b class="g">100&rarr;0%</b><span>re-identifiable records</span></div></div></div>
<img src="{a}" style="left:840px;top:70px;width:700px">
<img src="{b}" style="left:930px;top:330px;width:620px">
<div class="foot">Real screenshots of the running portal &middot; synthetic data only</div></div></body></html>"""

SCORE_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;font-family:Segoe UI,Arial}} #s{{width:1200px;padding:24px;background:#fff}}
h2{{font:700 30px Cambria,serif;color:#14213d;margin:0 0 14px}}
table{{border-collapse:collapse;width:100%;font-size:17px}} th{{background:#14213d;color:#fff;text-align:left;padding:10px}}
td{{padding:9px 10px;border-bottom:1px solid #e3e7ee;vertical-align:top}} td.b{{color:#a4161a}} td.a{{color:#1f7a6f;font-weight:600}}
td.k{{font-weight:700;color:#14213d}} .src{{font-size:13px;color:#5c677d;margin-top:10px}}
</style></head><body><div id="s"><h2>Before / after security scorecard</h2><table>
<tr><th>Area</th><th>Before (baseline)</th><th>Control</th><th>After (re-test)</th></tr>{rows}</table>
<div class="src">Every value comes from a saved output file in evidence/ (see the report, Section 5.2).</div></div></body></html>"""


def extras(score_rows):
    import shutil
    from playwright.sync_api import sync_playwright
    shutil.copy(ROOT / "diagrams/architecture.png", MEDIA / "architecture.png")
    shutil.copy(ROOT / "diagrams/cloud_architecture.png", MEDIA / "cloud-architecture.png")
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge")
        page = br.new_page(viewport={"width": 1600, "height": 720})
        page.set_content(HERO_HTML.format(a=(MEDIA / "registrar-students.png").as_uri(),
                                          b=(MEDIA / "sqli-before-after.png").as_uri()))
        page.wait_for_timeout(300)
        page.locator("#h").screenshot(path=str(MEDIA / "campusshield-overview.png"))
        rows = "".join(f'<tr><td class="k">{html.escape(a)}</td><td class="b">{html.escape(b)}</td>'
                       f'<td>{html.escape(c)}</td><td class="a">{html.escape(d)}</td></tr>' for a, b, c, d in score_rows)
        page = br.new_page(viewport={"width": 1250, "height": 900}, device_scale_factor=1.5)
        page.set_content(SCORE_HTML.format(rows=rows))
        page.locator("#s").screenshot(path=str(MEDIA / "security-scorecard.png"))
        br.close()
    print("  architecture.png, cloud-architecture.png, campusshield-overview.png, security-scorecard.png")


if __name__ == "__main__":
    MEDIA.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("app", "all"):
        app_media()
    if what in ("evidence", "all"):
        evidence_media()
    if what in ("extras", "all"):
        import json
        extras(json.loads((ROOT / "docs/media/scorecard.json").read_text(encoding="utf-8")))
