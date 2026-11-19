"""Generate a small SYNTHETIC student dataset for the privacy exercise (Task 5.4).

Every name, ID, e-mail and grade is invented. E-mails use the reserved .test domain.
Output: data/synthetic/privacy_students.csv (24 records)
"""
import csv
import datetime
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "synthetic" / "privacy_students.csv"

rng = random.Random(2026)          # fixed seed -> same dataset every run

FIRST = ["Omar", "Lina", "Yousef", "Maya", "Karim", "Sara", "Hadi", "Nour", "Rami", "Dana",
         "Tariq", "Leila", "Samir", "Hana", "Faris", "Rania", "Adam", "Zainab", "Bilal",
         "Aisha", "Khalid", "Mariam", "Ziad", "Huda"]
LAST = ["Haddad", "Khalil", "Nasser", "Saleh", "Rahman", "Aziz", "Farouk", "Mansour",
        "Qasim", "Darwish", "Hamdan", "Yassin", "Barakat", "Sabri", "Jaber", "Hijazi",
        "Shami", "Amin", "Toukan", "Odeh", "Masri", "Kanaan", "Issa", "Zaher"]
GENDER = {"Omar": "M", "Lina": "F", "Yousef": "M", "Maya": "F", "Karim": "M", "Sara": "F",
          "Hadi": "M", "Nour": "F", "Rami": "M", "Dana": "F", "Tariq": "M", "Leila": "F",
          "Samir": "M", "Hana": "F", "Faris": "M", "Rania": "F", "Adam": "M", "Zainab": "F",
          "Bilal": "M", "Aisha": "F", "Khalid": "M", "Mariam": "F", "Ziad": "M", "Huda": "F"}
NATIONALITIES = ["Emirati", "Jordanian", "Egyptian", "Lebanese", "Syrian", "Indian",
                 "Pakistani", "Moroccan"]
AREAS = ["Dubai Marina", "Deira", "Al Barsha", "Jumeirah", "Mirdif",      # Dubai
         "Al Nahda (Sharjah)", "Al Majaz", "Al Khan", "Muwaileh"]          # Sharjah
PROGRAMMES = ["BSc Cybersecurity", "BSc Computer Science", "BSc Information Systems"]

rows = []
for i in range(24):
    first, last = FIRST[i], LAST[i]
    dob = datetime.date(2002, 1, 1) + datetime.timedelta(days=rng.randint(0, 4 * 365))
    rows.append({
        "full_name": f"{first} {last}",
        "student_id": f"S2026{i + 101:03d}",
        "email": f"{first.lower()}.{last.lower()}@student.campushield.test",
        "date_of_birth": dob.isoformat(),
        "gender": GENDER[first],
        "nationality": rng.choices(NATIONALITIES, weights=[30, 15, 15, 8, 8, 12, 7, 5])[0],
        "home_area": rng.choices(AREAS, weights=[10, 14, 12, 8, 10, 14, 10, 8, 14])[0],
        "programme": rng.choice(PROGRAMMES),
        "year": rng.randint(1, 4),
        "gpa": round(rng.uniform(2.0, 4.0), 2),
        "scholarship": rng.choices(["none", "merit", "need-based", "sports"], weights=[55, 25, 15, 5])[0],
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} synthetic records to {OUT.relative_to(ROOT)}")
