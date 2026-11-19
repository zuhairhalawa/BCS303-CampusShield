"""Task 4 - reflected XSS before/after test.

Precondition for the attack: a logged-in registrar opens a crafted link
(for example from a phishing e-mail) to /search?q=<payload>.
The payload is harmless: it only writes a red banner into the page.

Step 1 checks the raw HTTP response (is the markup reflected unencoded? which
security headers are sent?). Step 2 loads the same link in a real browser
(Microsoft Edge driven by Playwright) and checks whether the script ran.
"""
import datetime
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab_servers import ROOT, SECURE, VULN, Recorder, db, login, start_servers, stop_servers  # noqa: E402
import requests  # noqa: E402

PAYLOAD = ("<script>document.body.insertAdjacentHTML('afterbegin','<h2 id=\"xss-proof\" style=\"color:#a4161a\">"
           "XSS DEMO: script from the link ran. document.cookie = ['+document.cookie+']</h2>')</script>")
HEADERS = ["Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"]
SHOTS = ROOT / "evidence" / "screenshots"


def browser_check(out, sessions):
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        for build, base in (("VULNERABLE", VULN), ("SECURE", SECURE)):
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            # log in through the real form so the browser receives the real cookie flags
            page.goto(f"{base}/login")
            page.fill("input[name=username]", "registrar1")
            page.fill("input[name=password]", db.read_credentials()["registrar1"])
            page.click("button[type=submit]")
            page.wait_for_url(f"{base}/students")
            csp_errors = []
            page.on("console", lambda m: csp_errors.append(m.text) if "Content Security Policy" in m.text else None)
            page.goto(f"{base}/search?q={quote(PAYLOAD)}")
            ran = page.locator("#xss-proof").count() > 0
            shown = page.locator("#query").inner_text()[:70]
            out(f"  [{build:<10}] script executed in browser: {ran}")
            if ran:
                out(f"               injected text: {page.locator('#xss-proof').inner_text()[:110]}")
            else:
                out(f"               page shows the input as text: {shown}...")
            page.screenshot(path=str(SHOTS / f"xss_{build.lower()}.png"))
            ctx.close()
        browser.close()


def main():
    out = Recorder(ROOT / "evidence" / "web_security" / "xss_results.txt")
    out(f"CampusShield reflected XSS test - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    out("Target: /search?q=<payload> as registrar1 (registrar-only page)")
    out(f"Payload: {PAYLOAD}\n")
    procs = start_servers()
    try:
        sessions = {"VULNERABLE": login(VULN, "registrar1"), "SECURE": login(SECURE, "registrar1")}
        out("Step 1 - raw HTTP response")
        for build, base in (("VULNERABLE", VULN), ("SECURE", SECURE)):
            r = sessions[build].get(f"{base}/search", params={"q": PAYLOAD})
            raw = "<script>document.body" in r.text
            enc = "&lt;script&gt;" in r.text
            out(f"  [{build:<10}] HTTP {r.status_code} | raw <script> reflected: {raw} | HTML-encoded copy: {enc}")
            for h in HEADERS:
                v = r.headers.get(h, "(missing)")
                out(f"               {h}: {v[:90]}")
        out("")
        for build, base in (("VULNERABLE", VULN), ("SECURE", SECURE)):
            r = requests.post(f"{base}/login", data={"username": "registrar1",
                              "password": db.read_credentials()["registrar1"]}, allow_redirects=False)
            flags = [f.strip() for f in r.headers.get("Set-Cookie", "").split(";")[1:]]
            out(f"  [{build:<10}] session cookie flags set at login: {flags}")
        out("\nStep 2 - real browser (Edge via Playwright)")
        browser_check(out, sessions)
        out("\nStep 3 - normal search still works on the secure build")
        r = sessions["SECURE"].get(f"{SECURE}/search", params={"q": "O'Neill"})
        import re
        found = re.search(r"\((\d+) found\)", r.text).group(1)
        out(f"  search 'O'Neill' -> {found} result(s), page HTTP {r.status_code}")
        r = sessions["SECURE"].get(f"{SECURE}/search", params={"q": "Haddad"})
        out(f"  search 'Haddad'  -> {re.search(r'[(](\d+) found[)]', r.text).group(1)} result(s)")
    finally:
        stop_servers(procs)
    out.save()


if __name__ == "__main__":
    main()
