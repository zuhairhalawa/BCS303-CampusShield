"""AES-256-GCM encryption and decryption of the synthetic CSV dataset.

GCM is an authenticated mode: it gives confidentiality (ciphertext is unreadable)
AND integrity (any change to the ciphertext makes decryption fail).

Output files (key and decrypted copy are git-ignored):
  output/records.enc                   = 12-byte nonce || ciphertext || 16-byte tag
  output/aes.key                       = 32-byte random key (NEVER commit)
  output/records_decrypted.csv         = decrypted copy for comparison
Run:  python demonstrations/cryptography/aes_gcm_demo.py
"""
import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "synthetic" / "campus_records.csv"
OUTDIR = Path(__file__).resolve().parent / "output"
LOG = ROOT / "evidence" / "cryptography" / "aes_gcm_output.txt"
OUTDIR.mkdir(exist_ok=True)
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


def sha256_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


plaintext = SRC.read_bytes()
key = AESGCM.generate_key(bit_length=256)          # random 256-bit key
(OUTDIR / "aes.key").write_bytes(key)
nonce = os.urandom(12)                              # 96-bit nonce, never reused with the same key
aad = b"CampusShield synthetic records v1"          # authenticated but not encrypted header

ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
enc_path = OUTDIR / "records.enc"
enc_path.write_bytes(nonce + ciphertext)

say("=== AES-256-GCM encryption of campus_records.csv ===")
say(f"plaintext size : {len(plaintext)} bytes")
say(f"key            : 256-bit random key stored in output/aes.key (git-ignored, not shown)")
say(f"nonce (hex)    : {nonce.hex()}")
say(f"encrypted file : {enc_path.relative_to(ROOT)} ({enc_path.stat().st_size} bytes = 12 nonce + {len(plaintext)} data + 16 tag)")
say(f"first line of plaintext : {plaintext.splitlines()[1].decode()}")
say(f"first 48 bytes of cipher: {ciphertext[:48].hex()}")
say(f"is the name 'Omar' visible in the ciphertext? {b'Omar' in ciphertext}")

# --- decrypt and prove the result is identical ---
blob = enc_path.read_bytes()
recovered = AESGCM(key).decrypt(blob[:12], blob[12:], aad)
dec_path = OUTDIR / "records_decrypted.csv"
dec_path.write_bytes(recovered)
say()
say("=== Decryption ===")
say(f"SHA-256 original : {sha256_file(SRC)}")
say(f"SHA-256 decrypted: {sha256_file(dec_path)}")
say(f"identical        : {recovered == plaintext}")

# --- tamper test: flip one bit in the ciphertext ---
tampered = bytearray(blob)
tampered[40] ^= 0x01
say()
say("=== Tamper test (one bit flipped at byte 40 of the encrypted file) ===")
try:
    AESGCM(key).decrypt(bytes(tampered[:12]), bytes(tampered[12:]), aad)
    say("decryption succeeded (unexpected)")
except InvalidTag:
    say("decryption refused: InvalidTag -> GCM detected the modification")

# --- wrong key test ---
try:
    AESGCM(AESGCM.generate_key(bit_length=256)).decrypt(blob[:12], blob[12:], aad)
    say("wrong key worked (unexpected)")
except InvalidTag:
    say("wrong key: InvalidTag -> data cannot be read without the right key")

LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {LOG.relative_to(ROOT)}]")
