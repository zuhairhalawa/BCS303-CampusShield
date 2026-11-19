"""Shared helpers for the web demos: start the secure (port 5000) and vulnerable
(port 5001) builds on 127.0.0.1, log in over real HTTP, and record output."""
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import db  # noqa: E402

SECURE = "http://127.0.0.1:5000"
VULN = "http://127.0.0.1:5001"


def _wait_for_port(port: int, timeout: float = 15) -> None:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.3)
    raise RuntimeError(f"server on port {port} did not start")


def start_servers():
    """Start both builds as separate processes. Returns the Popen list."""
    procs = []
    for mode, port in (("secure", 5000), ("vulnerable", 5001)):
        procs.append(subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "run_app.py"), "--mode", mode, "--port", str(port)],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        _wait_for_port(port)
    return procs


def stop_servers(procs) -> None:
    for p in procs:
        p.terminate()
        p.wait(timeout=10)


def login(base: str, username: str) -> requests.Session:
    creds = db.read_credentials()
    s = requests.Session()
    r = s.post(f"{base}/login", data={"username": username, "password": creds[username]}, allow_redirects=False)
    if r.status_code != 302:
        raise RuntimeError(f"login failed for {username} on {base}: {r.status_code}")
    return s


class Recorder:
    """Print to the console and keep a copy for the evidence file."""

    def __init__(self, path: Path):
        self.path = path
        self.lines = []

    def __call__(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"\n[saved] {self.path.relative_to(ROOT)}")
