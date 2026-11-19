"""Take report screenshots of the running CampusShield builds with Edge (Playwright).

Also performs a controlled lockout test: 5 wrong passwords for s2026002 on the
secure build, screenshot of the admin view, then the admin unlocks the account.
Output: evidence/screenshots/*.png
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab_servers import ROOT, SECURE, VULN, db, start_servers, stop_servers  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SHOTS = ROOT / "evidence" / "screenshots"
CREDS = db.read_credentials()


def login(page, base, user):
    page.goto(f"{base}/login")
    page.fill("input[name=username]", user)
    page.fill("input[name=password]", CREDS[user])
    page.click("button[type=submit]")
    page.wait_for_load_state()


def shot(page, name, full=False):
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)
    print("saved", name)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    procs = start_servers()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            new = lambda: browser.new_context(viewport={"width": 1280, "height": 720}).new_page()  # noqa: E731

            page = new()
            page.goto(f"{SECURE}/login")
            shot(page, "app_login_secure")

            # Student: normal query, then SQLi on both builds
            for base, tag in ((VULN, "vulnerable"), (SECURE, "secure")):
                page = new()
                login(page, base, "s2026001")
                course = page.locator("code").first.inner_text()
                if tag == "secure":
                    page.goto(f"{base}/attendance?course={course}")
                    shot(page, "sqli_normal_query_secure")
                page.goto(f"{base}/attendance?course={quote(course + chr(39) + ' OR ' + chr(39) + '1' + chr(39) + '=' + chr(39) + '1')}")
                shot(page, f"sqli_tautology_{tag}")
                page.goto(f"{base}/attendance?course=" + quote("x' UNION SELECT username, role, password_hash, 'leak', 'leak' FROM users --"))
                shot(page, f"sqli_union_{tag}")
                if tag == "secure":
                    page.goto(f"{base}/students")          # student trying a registrar page
                    shot(page, "rbac_student_denied_403")

            # Registrar view
            page = new()
            login(page, SECURE, "registrar1")
            page.goto(f"{SECURE}/search?q={quote(chr(79) + chr(39) + 'Neill')}")
            shot(page, "registrar_search_normal_secure")
            page.goto(f"{SECURE}/admin/users")                # registrar trying an admin page
            shot(page, "rbac_registrar_denied_403")

            # Lockout: 5 wrong passwords for s2026002 on the secure build
            page = new()
            for i in range(5):
                page.goto(f"{SECURE}/login")
                page.fill("input[name=username]", "s2026002")
                page.fill("input[name=password]", f"WrongGuess-{i}!")
                page.click("button[type=submit]")
            page.goto(f"{SECURE}/login")
            page.fill("input[name=username]", "s2026002")
            page.fill("input[name=password]", CREDS["s2026002"])   # correct password, still refused
            page.click("button[type=submit]")
            page.wait_for_load_state()
            shot(page, "lockout_correct_password_refused")

            admin = new()
            login(admin, SECURE, "admin1")
            admin.goto(f"{SECURE}/admin/users")
            shot(admin, "admin_accounts_locked", full=True)
            admin.goto(f"{SECURE}/admin/audit")
            shot(admin, "admin_audit_log")
            admin.goto(f"{SECURE}/admin/users")
            admin.click("form[action$='/admin/unlock/s2026002'] button")
            shot(admin, "admin_unlocked_account", full=True)
            browser.close()
    finally:
        stop_servers(procs)


if __name__ == "__main__":
    main()
