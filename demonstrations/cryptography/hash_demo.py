"""SHA-256 integrity hash of the synthetic CSV: generate, verify, then detect a change.

Writes data/synthetic/campus_records.csv.sha256 in the usual "hash  filename" format,
so it can also be checked with:  sha256sum -c campus_records.csv.sha256
Run:  python demonstrations/cryptography/hash_demo.py
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "synthetic" / "campus_records.csv"
SUMFILE = CSV.with_name(CSV.name + ".sha256")
OUTDIR = Path(__file__).resolve().parent / "output"
LOG = ROOT / "evidence" / "cryptography" / "hash_output.txt"
OUTDIR.mkdir(exist_ok=True)
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


def sha256_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# 1. generate and store the reference hash
digest = sha256_file(CSV)
SUMFILE.write_text(f"{digest}  {CSV.name}\n", encoding="utf-8")
say("=== 1. Generate SHA-256 ===")
say(f"{digest}  {CSV.name}")
say(f"saved to {SUMFILE.relative_to(ROOT)}")

# 2. verify the untouched file
stored = SUMFILE.read_text().split()[0]
say()
say("=== 2. Verify original file ===")
say(f"stored : {stored}")
say(f"current: {sha256_file(CSV)}")
say(f"result : {'OK - file unchanged' if sha256_file(CSV) == stored else 'MISMATCH'}")

# 3. change one GPA in a copy and verify again
rows = CSV.read_text(encoding="utf-8").splitlines()
fields = rows[1].split(",")
old_gpa = fields[4]
fields[4] = "4.00"
rows[1] = ",".join(fields)
modified = OUTDIR / "records_modified.csv"
modified.write_text("\n".join(rows) + "\n", encoding="utf-8")
say()
say("=== 3. Verify a modified copy (one GPA changed) ===")
say(f"changed {fields[0]} GPA from {old_gpa} to 4.00")
say(f"stored : {stored}")
say(f"current: {sha256_file(modified)}")
say(f"result : {'OK' if sha256_file(modified) == stored else 'MISMATCH - integrity violation detected'}")
diff_bits = bin(int(stored, 16) ^ int(sha256_file(modified), 16)).count("1")
say(f"bits that differ between the two hashes: {diff_bits} of 256 (avalanche effect)")

LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {LOG.relative_to(ROOT)}]")
