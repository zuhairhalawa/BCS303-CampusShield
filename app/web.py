"""CampusShield attendance / registration portal (Flask).

The same application can start in two modes:

* secure      - default. Parameterised SQL, auto-escaped output, security headers.
* vulnerable  - LAB ONLY. Re-introduces two deliberate weaknesses so we can show
                the attack before the fix:
                  1. SQL injection in the student attendance lookup (/attendance)
                  2. Reflected XSS in the registrar student search (/search)
                and sends no browser security headers.

Everything else (login, lockout, RBAC, logging) is identical in both modes, so a
before/after test only changes the code under test.
"""
import datetime
import functools
import logging
import os
import re
import secrets
import sqlite3
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from markupsafe import Markup

from . import db as dbmod
from . import security

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.environ.get("CAMPUSHIELD_LOG_DIR", ROOT / "logs"))
COURSE_RE = re.compile(r"^[A-Z]{3}\d{3}$")
ROLE_HOME = {"admin": "admin_users", "registrar": "students", "student": "attendance"}


def _make_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("campushield")
    if not logger.handlers:
        handler = logging.FileHandler(LOG_DIR / "campushield.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s campushield[%(process)d]: %(message)s", "%Y-%m-%dT%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def create_app(mode: str = "secure") -> Flask:
    if mode not in ("secure", "vulnerable"):
        raise ValueError("mode must be 'secure' or 'vulnerable'")
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("CAMPUSHIELD_SECRET") or secrets.token_hex(32),  # never hard-coded
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MODE=mode,
        VULNERABLE=(mode == "vulnerable"),
    )
    log = _make_logger()

    # ------------------------------------------------------------------ helpers
    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = dbmod.connect()
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    def audit(event: str, username: str = None, detail: str = "") -> None:
        ip = request.remote_addr if request else "-"
        log.info("%s user=%s ip=%s %s", event, username or "-", ip, detail)
        conn = get_db()
        conn.execute("INSERT INTO audit_log (ts, username, event, detail, ip) VALUES (?, ?, ?, ?, ?)",
                     (datetime.datetime.now().isoformat(timespec="seconds"), username, event, detail, ip))
        conn.commit()

    def require_roles(*roles):
        """RBAC decorator: user must be logged in AND hold one of the listed roles."""
        def wrap(view):
            @functools.wraps(view)
            def inner(*args, **kwargs):
                if g.user is None:
                    return redirect(url_for("login"))
                if g.user["role"] not in roles:
                    audit("ACCESS_DENIED", g.user["username"],
                          f"role={g.user['role']} path={request.path}")
                    abort(403)
                return view(*args, **kwargs)
            return inner
        return wrap

    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("uid")
        if uid is not None:
            g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if request.method == "POST" and request.endpoint != "login":
            if request.form.get("csrf_token") != session.get("csrf_token"):
                abort(400, "CSRF token missing or wrong")

    @app.context_processor
    def inject_globals():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        return {"user": g.user, "mode": app.config["MODE"], "csrf_token": session["csrf_token"]}

    @app.after_request
    def security_headers(resp):
        if not app.config["VULNERABLE"]:
            # FIX for the web weakness: tell the browser to refuse inline script,
            # framing (clickjacking) and MIME sniffing.
            resp.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; object-src 'none'; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
            resp.headers["X-Frame-Options"] = "DENY"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["Referrer-Policy"] = "no-referrer"
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ------------------------------------------------------------------ auth
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            conn = get_db()
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            now = datetime.datetime.now()
            if row and row["locked_until"] and datetime.datetime.fromisoformat(row["locked_until"]) > now:
                audit("LOGIN_BLOCKED_LOCKED", username, f"locked_until={row['locked_until']}")
                flash("Invalid username or password, or the account is temporarily locked.")
                return render_template("login.html"), 401
            if row and security.verify_password(password, row["password_hash"]):
                conn.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
                conn.commit()
                session.clear()
                session["uid"] = row["id"]
                audit("LOGIN_SUCCESS", username, f"role={row['role']}")
                return redirect(url_for("home"))
            if row:
                attempts = row["failed_attempts"] + 1
                locked = None
                if attempts >= security.MAX_FAILED_ATTEMPTS:
                    locked = (now + datetime.timedelta(minutes=security.LOCKOUT_MINUTES)).isoformat(timespec="seconds")
                conn.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                             (attempts, locked, row["id"]))
                conn.commit()
                audit("LOGIN_FAILED", username, f"attempts={attempts}")
                if locked:
                    audit("ACCOUNT_LOCKED", username, f"until={locked}")
            else:
                audit("LOGIN_FAILED", username or "<empty>", "attempts=unknown_user")
            # Same message for every failure so usernames cannot be enumerated.
            flash("Invalid username or password, or the account is temporarily locked.")
            return render_template("login.html"), 401
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        if g.user:
            audit("LOGOUT", g.user["username"])
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def home():
        if g.user is None:
            return redirect(url_for("login"))
        return redirect(url_for(ROLE_HOME[g.user["role"]]))

    # ------------------------------------------------------------------ student
    @app.route("/attendance")
    @require_roles("student")
    def attendance():
        sid = g.user["student_id"]
        course = request.args.get("course", "")
        conn = get_db()
        courses = conn.execute(
            "SELECT c.code, c.title FROM registrations r JOIN courses c ON c.code = r.course_code "
            "WHERE r.student_id = ? ORDER BY c.code", (sid,)).fetchall()
        rows, error, sql_shown = [], None, None
        if course:
            if app.config["VULNERABLE"]:
                # VULNERABLE (lab only): user input is pasted straight into the SQL text.
                sql = ("SELECT a.student_id, s.full_name, a.course_code, a.session_date, a.status "
                       "FROM attendance a JOIN students s ON s.student_id = a.student_id "
                       f"WHERE a.student_id = '{sid}' AND a.course_code = '{course}' "
                       "ORDER BY a.student_id, a.session_date")
                sql_shown = sql
                try:
                    rows = conn.execute(sql).fetchall()
                except sqlite3.Error as exc:
                    error = f"Database error: {exc}"        # verbose error = extra information leak
            else:
                # FIXED: allow-list validation for a friendly message + parameterised query.
                if not COURSE_RE.fullmatch(course):
                    error = "Course code must look like BCS303."
                else:
                    rows = conn.execute(
                        "SELECT a.student_id, s.full_name, a.course_code, a.session_date, a.status "
                        "FROM attendance a JOIN students s ON s.student_id = a.student_id "
                        "WHERE a.student_id = ? AND a.course_code = ? "
                        "ORDER BY a.student_id, a.session_date", (sid, course)).fetchall()
            audit("ATTENDANCE_QUERY", g.user["username"], f"course={course!r} rows={len(rows)}")
        return render_template("attendance.html", courses=courses, rows=rows, course=course,
                               error=error, sql_shown=sql_shown)

    # ------------------------------------------------------------------ registrar
    @app.route("/students")
    @require_roles("registrar")
    def students():
        rows = get_db().execute(
            "SELECT student_id, full_name, email, programme, year FROM students ORDER BY student_id").fetchall()
        return render_template("students.html", rows=rows)

    @app.route("/search")
    @require_roles("registrar")
    def search():
        q = request.args.get("q", "")
        rows = []
        if q:
            rows = get_db().execute(
                "SELECT student_id, full_name, email, programme, year FROM students "
                "WHERE full_name LIKE ? ORDER BY student_id", (f"%{q}%",)).fetchall()
        if app.config["VULNERABLE"]:
            # VULNERABLE (lab only): the search term is marked as trusted HTML,
            # so any markup in ?q= is reflected into the page and executed.
            shown_query = Markup(q)
        else:
            # FIXED: leave it as plain text; Jinja2 auto-escapes < > & ' " for HTML.
            shown_query = q
        return render_template("search.html", rows=rows, q=q, shown_query=shown_query)

    @app.route("/registrar/attendance", methods=["GET", "POST"])
    @require_roles("registrar")
    def mark_attendance():
        conn = get_db()
        if request.method == "POST":
            sid = request.form.get("student_id", "")
            course = request.form.get("course_code", "")
            date = request.form.get("session_date", "")
            status = request.form.get("status", "")
            ok = (re.fullmatch(r"S\d{7}", sid) and COURSE_RE.fullmatch(course)
                  and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) and status in ("present", "absent", "late"))
            registered = ok and conn.execute(
                "SELECT 1 FROM registrations WHERE student_id = ? AND course_code = ?", (sid, course)).fetchone()
            if not registered:
                flash("Rejected: invalid input or student is not registered in that course.")
            else:
                conn.execute("INSERT INTO attendance (student_id, course_code, session_date, status) "
                             "VALUES (?, ?, ?, ?)", (sid, course, date, status))
                conn.commit()
                audit("ATTENDANCE_MARKED", g.user["username"], f"{sid} {course} {date} {status}")
                flash(f"Recorded {status} for {sid} in {course} on {date}.")
            return redirect(url_for("mark_attendance"))
        recent = conn.execute(
            "SELECT student_id, course_code, session_date, status FROM attendance ORDER BY id DESC LIMIT 10").fetchall()
        courses = conn.execute("SELECT code, title FROM courses ORDER BY code").fetchall()
        return render_template("mark_attendance.html", recent=recent, courses=courses)

    @app.route("/registrar/register", methods=["POST"])
    @require_roles("registrar")
    def register_course():
        sid = request.form.get("student_id", "")
        course = request.form.get("course_code", "")
        conn = get_db()
        exists = conn.execute("SELECT 1 FROM students WHERE student_id = ?", (sid,)).fetchone()
        if not exists or not COURSE_RE.fullmatch(course):
            flash("Rejected: unknown student or bad course code.")
        else:
            conn.execute("INSERT OR IGNORE INTO registrations VALUES (?, ?, ?)", (sid, course, dbmod.TERM))
            conn.commit()
            audit("COURSE_REGISTERED", g.user["username"], f"{sid} {course}")
            flash(f"{sid} registered in {course}.")
        return redirect(url_for("mark_attendance"))

    # ------------------------------------------------------------------ admin
    @app.route("/admin/users", methods=["GET", "POST"])
    @require_roles("admin")
    def admin_users():
        conn = get_db()
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            role = request.form.get("role", "")
            problems = security.check_password_policy(password, username)
            if not re.fullmatch(r"[a-z0-9_]{3,32}", username) or role not in ("registrar", "student", "admin"):
                flash("Rejected: bad username or role.")
            elif problems:
                flash("Rejected by password policy: " + ", ".join(problems))
                audit("PASSWORD_POLICY_REJECT", g.user["username"], f"new_user={username}")
            else:
                try:
                    conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                                 (username, security.hash_password(password), role))
                    conn.commit()
                    audit("USER_CREATED", g.user["username"], f"new_user={username} role={role}")
                    flash(f"Created {role} account {username}.")
                except sqlite3.IntegrityError:
                    flash("That username already exists.")
            return redirect(url_for("admin_users"))
        users = conn.execute(
            "SELECT username, role, student_id, failed_attempts, locked_until FROM users ORDER BY id").fetchall()
        return render_template("admin_users.html", users=users)

    @app.route("/admin/unlock/<username>", methods=["POST"])
    @require_roles("admin")
    def admin_unlock(username):
        conn = get_db()
        conn.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?", (username,))
        conn.commit()
        audit("ACCOUNT_UNLOCKED", g.user["username"], f"target={username}")
        flash(f"Unlocked {username}.")
        return redirect(url_for("admin_users"))

    @app.route("/admin/audit")
    @require_roles("admin")
    def admin_audit():
        rows = get_db().execute("SELECT ts, username, event, detail, ip FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()
        return render_template("audit.html", rows=rows)

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="Your role is not allowed to open this page."), 403

    return app
