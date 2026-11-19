"""Offline password-strength audit on SYNTHETIC lab accounts only.

1. Build a "legacy" table of unsalted SHA-256 hashes (self-generated, no real users).
2. Run a small dictionary + mutation attack against those hashes, offline.
3. Check every password against the CampusShield password policy.
4. Compare how fast SHA-256 and PBKDF2 (600,000 iterations) can be computed.
5. Show the safer design: random salt per password + PBKDF2 verification.

Run:  python demonstrations/authentication/password_audit.py
"""
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import security  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / "evidence" / "authentication" / "password_audit_output.txt"
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


# Synthetic lab users and passwords (invented for this exercise only).
LAB_USERS = {
    "lab_amal":    "campus123",
    "lab_basel":   "Summer2026",
    "lab_chadi":   "qwerty123",
    "lab_dima":    "P@ssw0rd",
    "lab_eyad":    "library",
    "lab_farah":   "Dubai2026!",
    "lab_ghassan": "campus123",           # same password as lab_amal on purpose
    "lab_huda":    "Football1",
    "lab_issa":    "t7#Rq9!vLm2@Xp",
    "lab_jana":    "Correct-Horse-Battery-42",
    "lab_khaled":  "w8$Kd!3zQe&Pn5",
    "lab_lama":    "Registrar!2026",
}


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def mutations(word):
    """Simple rules that real cracking tools also use."""
    leet = str.maketrans({"a": "@", "o": "0", "e": "3", "i": "1", "s": "$"})
    bases = {word, word.capitalize(), word.upper(), word.translate(leet), word.capitalize().translate(leet)}
    suffixes = ["", "1", "12", "123", "!", "1!", "2025", "2026", "2026!", "@2026"]
    for b in bases:
        for s in suffixes:
            yield b + s


say("=== 1. Legacy table: unsalted SHA-256 (synthetic lab accounts) ===")
legacy = {u: sha256(p) for u, p in LAB_USERS.items()}
for u, h in legacy.items():
    say(f"{u:<12} {h}")
say()
say("Same password -> same hash (no salt):")
say(f"  lab_amal    {legacy['lab_amal']}")
say(f"  lab_ghassan {legacy['lab_ghassan']}")
say(f"  identical? {legacy['lab_amal'] == legacy['lab_ghassan']}")

say()
say("=== 2. Offline dictionary + mutation audit ===")
words = [w.strip() for w in (HERE / "wordlist.txt").read_text().splitlines() if w.strip()]
target = {}
for u, h in legacy.items():
    target.setdefault(h, []).append(u)
cracked, guesses = {}, 0
start = time.perf_counter()
for w in words:
    for cand in mutations(w):
        guesses += 1
        h = sha256(cand)
        if h in target and h not in cracked:
            cracked[h] = cand
elapsed = time.perf_counter() - start
say(f"wordlist words: {len(words)}, candidate guesses tried: {guesses}, time: {elapsed:.3f} s")
for h, pw in cracked.items():
    for u in target[h]:
        say(f"  CRACKED  {u:<12} -> {pw}")
not_cracked = [u for u, h in legacy.items() if h not in cracked]
for u in not_cracked:
    say(f"  survived {u}")
cracked_users = sum(len(target[h]) for h in cracked)
say(f"Result: {cracked_users} of {len(LAB_USERS)} accounts cracked in {elapsed:.3f} seconds")

say()
say("=== 3. CampusShield password policy check ===")
for u, p in LAB_USERS.items():
    problems = security.check_password_policy(p, u)
    status = "PASS" if not problems else "FAIL: " + ", ".join(problems)
    say(f"{u:<12} {p:<26} {status}")

say()
say("=== 4. Speed: fast hash vs password KDF on this machine ===")
n = 200_000
t = time.perf_counter()
for i in range(n):
    hashlib.sha256(b"campus123" + str(i).encode()).digest()
sha_rate = n / (time.perf_counter() - t)
m = 5
t = time.perf_counter()
for i in range(m):
    hashlib.pbkdf2_hmac("sha256", b"campus123", b"0123456789abcdef", security.PBKDF2_ITERATIONS)
kdf_rate = m / (time.perf_counter() - t)
say(f"SHA-256 (single pass):           {sha_rate:,.0f} hashes/second")
say(f"PBKDF2-HMAC-SHA256 ({security.PBKDF2_ITERATIONS:,} it.): {kdf_rate:,.2f} hashes/second")
say(f"PBKDF2 is roughly {sha_rate / kdf_rate:,.0f}x slower per guess for an attacker")

say()
say("=== 5. Safer design: random salt + PBKDF2 (app/security.py) ===")
h1 = security.hash_password("campus123")
h2 = security.hash_password("campus123")
say(f"hash #1 of 'campus123': {h1}")
say(f"hash #2 of 'campus123': {h2}")
say(f"same password, different stored value? {h1 != h2}")
say(f"verify_password('campus123', hash #1)  -> {security.verify_password('campus123', h1)}")
say(f"verify_password('Campus123', hash #1)  -> {security.verify_password('Campus123', h1)}")
say(f"verify_password('wrong-guess', hash #2) -> {security.verify_password('wrong-guess', h2)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {OUT.relative_to(ROOT)}]")
