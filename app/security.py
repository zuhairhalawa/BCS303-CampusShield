"""Password storage, password policy and login-throttling helpers for CampusShield.

Passwords are never stored in plain text. Each password gets its own random
16-byte salt and is stretched with PBKDF2-HMAC-SHA256 (Python standard library).
"""
import base64
import hashlib
import hmac
import os
import re
import string

PBKDF2_ITERATIONS = 600_000      # OWASP Password Storage Cheat Sheet value for PBKDF2-HMAC-SHA256
SALT_BYTES = 16
MAX_FAILED_ATTEMPTS = 5          # lock the account after 5 wrong passwords in a row
LOCKOUT_MINUTES = 15
MIN_LENGTH = 12

# Small list of passwords that appear at the top of public breach lists.
COMMON_PASSWORDS = {
    "123456", "password", "123456789", "qwerty", "12345678", "111111", "abc123",
    "password1", "iloveyou", "admin", "welcome", "letmein", "monkey", "dragon",
    "football", "campus123", "student123", "password123", "admin123", "qwerty123",
    "welcome1", "p@ssw0rd", "passw0rd", "summer2026", "university1",
}


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Return 'pbkdf2_sha256$iterations$salt$hash' with a fresh random salt."""
    salt = os.urandom(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, stored: str) -> bool:
    """Recompute the hash with the stored salt and compare in constant time."""
    try:
        scheme, iterations, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(candidate, expected)


def check_password_policy(password: str, username: str = "") -> list:
    """Return a list of policy problems. An empty list means the password is acceptable."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"shorter than {MIN_LENGTH} characters")
    if not re.search(r"[a-z]", password):
        problems.append("no lowercase letter")
    if not re.search(r"[A-Z]", password):
        problems.append("no uppercase letter")
    if not re.search(r"\d", password):
        problems.append("no digit")
    if not any(ch in string.punctuation for ch in password):
        problems.append("no symbol")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("appears in common-password list")
    if username and username.lower() in password.lower():
        problems.append("contains the username")
    return problems


def generate_lab_password(length: int = 16) -> str:
    """Random password that always satisfies the policy (used for dummy lab accounts)."""
    import secrets
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if not check_password_policy(pw):
            return pw
