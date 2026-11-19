#!/usr/bin/env bash
# OpenSSL version of the same exercise (works in Kali and in Git Bash on Windows).
# The passphrase comes from an environment variable so it is never written to the repo.
#   export CS_LAB_PASS='some-lab-passphrase'
#   bash demonstrations/cryptography/openssl_demo.sh
set -u
cd "$(dirname "$0")/../.."
CSV=data/synthetic/campus_records.csv
OUT=demonstrations/cryptography/output
LOG=evidence/cryptography/openssl_output.txt
mkdir -p "$OUT" evidence/cryptography
: "${CS_LAB_PASS:?set CS_LAB_PASS first}"

{
echo "=== openssl version ==="
openssl version
echo
echo "=== 1. SHA-256 with openssl dgst ==="
echo '$ openssl dgst -sha256 data/synthetic/campus_records.csv'
openssl dgst -sha256 "$CSV"
echo
echo "=== 2. Encrypt: AES-256-CBC, key derived from passphrase with PBKDF2 (100000 iterations, random salt) ==="
echo '$ openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -in campus_records.csv -out records.ossl.enc -pass env:CS_LAB_PASS'
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -in "$CSV" -out "$OUT/records.ossl.enc" -pass env:CS_LAB_PASS
ls -l "$OUT/records.ossl.enc" | awk '{print $5" bytes  "$NF}'
echo "first 32 bytes of the encrypted file (starts with 'Salted__' + 8-byte salt):"
head -c 32 "$OUT/records.ossl.enc" | od -A x -t x1z | head -2
echo
echo "=== 3. Decrypt and compare ==="
echo '$ openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -in records.ossl.enc -out ossl_decrypted.csv -pass env:CS_LAB_PASS'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -in "$OUT/records.ossl.enc" -out "$OUT/ossl_decrypted.csv" -pass env:CS_LAB_PASS
if cmp -s "$CSV" "$OUT/ossl_decrypted.csv"; then echo "cmp: decrypted file is IDENTICAL to the original"; else echo "cmp: files DIFFER"; fi
openssl dgst -sha256 "$OUT/ossl_decrypted.csv"
echo
echo "=== 4. Wrong passphrase ==="
if openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -in "$OUT/records.ossl.enc" -out /dev/null -pass pass:wrong-passphrase 2>&1; then
  echo "decrypted with wrong passphrase (unexpected)"
else
  echo "decryption with the wrong passphrase failed (bad decrypt)"
fi
echo "Note: CBC has no authentication tag, so integrity must come from a separate hash/HMAC;"
echo "AES-GCM in aes_gcm_demo.py gives both confidentiality and integrity."
} 2>&1 | tee "$LOG"
rm -f "$OUT/ossl_decrypted.csv"
