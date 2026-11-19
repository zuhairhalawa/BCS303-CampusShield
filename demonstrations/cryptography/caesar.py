"""Caesar cipher: encrypt, decrypt, then break it by trying every shift.

Run:  python demonstrations/cryptography/caesar.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "evidence" / "cryptography" / "caesar_output.txt"
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


def caesar(text, shift):
    out = []
    for ch in text:
        if ch.isupper():
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        elif ch.islower():
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        else:
            out.append(ch)                  # digits, spaces and punctuation are not changed
    return "".join(out)


message = "Meet at the library at 3pm"
SHIFT = 7
cipher = caesar(message, SHIFT)
plain = caesar(cipher, -SHIFT)

say("=== Caesar cipher ===")
say(f"plaintext : {message}")
say(f"shift/key : {SHIFT}")
say(f"ciphertext: {cipher}")
say(f"decrypted : {plain}")
say(f"round trip OK: {plain == message}")
say()
say("=== Brute force: an attacker simply tries all 25 possible shifts ===")
for k in range(1, 26):
    guess = caesar(cipher, -k)
    mark = "   <-- readable English" if guess == message else ""
    say(f"shift {k:>2}: {guess}{mark}")
say()
say("Key space = 25 useful keys, so the cipher is broken instantly by hand or by a 1-line loop.")
say("Letter frequencies and word lengths are also preserved (e.g. 'at' -> 'ha' both times).")

LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {LOG.relative_to(ROOT)}]")
