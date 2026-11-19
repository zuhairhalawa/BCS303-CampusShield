"""Create a synthetic CSV of student records for the encryption and hashing exercises.

Every value is invented. E-mails use the reserved .test domain and phone numbers
use the obviously fake 050-000-xxxx pattern.
Run:  python demonstrations/cryptography/make_dataset.py
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "synthetic" / "campus_records.csv"

FIRST = ["Omar", "Lina", "Yousef", "Maya", "Karim", "Sara", "Hadi", "Nour", "Rami", "Dana",
         "Tariq", "Leila", "Samir", "Hana", "Faris", "Rania", "Adam", "Zainab", "Bilal",
         "Aisha", "Jad", "Reem", "Ziad", "Mona", "Fadi"]
LAST = ["Haddad", "Khalil", "Nasser", "Saleh", "Rahman", "Aziz", "Farouk", "Mansour", "Qasim",
        "Darwish", "Hamdan", "Yassin", "Barakat", "Sabri", "Jaber", "Hijazi", "Shami", "Amin",
        "Toukan", "Odeh", "Karam", "Nimer", "Sharif", "Tamimi", "Zayed"]
PROGRAMMES = ["BSc Cybersecurity", "BSc Computer Science", "BSc Information Systems"]

rng = random.Random(2026)
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["student_id", "full_name", "email", "programme", "gpa", "phone"])
    for i in range(25):
        first, last = FIRST[i], LAST[i]
        w.writerow([f"S2026{i + 1:03d}", f"{first} {last}",
                    f"{first.lower()}.{last.lower()}@student.campushield.test",
                    rng.choice(PROGRAMMES), f"{rng.uniform(2.0, 4.0):.2f}",
                    f"050-000-{rng.randint(0, 9999):04d}"])
print(f"Wrote 25 synthetic records to {OUT.relative_to(ROOT)}")
