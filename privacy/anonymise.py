"""Task 5.4 - measure re-identification exposure, de-identify, measure again.

Steps
  1. Load the synthetic dataset (data/synthetic/privacy_students.csv).
  2. BEFORE: group records by the quasi-identifiers (QIs) and measure k-anonymity.
  3. Suppress direct identifiers and pseudonymise student_id (keyed HMAC-SHA256).
  4. Generalise the QIs one level at a time. Stop at the first level where at most
     MAX_SUPPRESS_PCT of the records are still in a group smaller than K_TARGET,
     then suppress (remove) those few records.
  5. AFTER: same metrics + a simple utility check (GPA per programme).

Output: privacy/output/privacy_students_anonymised.csv,
        evidence/privacy/privacy_output.txt, evidence/privacy/k_anonymity_before_after.png
"""
import hashlib
import hmac
import os
import secrets
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "synthetic" / "privacy_students.csv"
OUT_CSV = ROOT / "privacy" / "output" / "privacy_students_anonymised.csv"
EVID = ROOT / "evidence" / "privacy"
K_TARGET = int(os.environ.get("CAMPUSHIELD_K", "2"))   # each released record shares its QI values with >= K-1 others
MAX_SUPPRESS_PCT = 20        # we accept losing at most 20% of the rows

lines = []


def log(text=""):
    print(text)
    lines.append(str(text))


def metrics(df, qi):
    """k-anonymity style numbers for a table and a list of quasi-identifier columns."""
    sizes = df.groupby(qi)[qi[0]].transform("size")      # equivalence-class size of each record
    return {
        "records": len(df),
        "classes": df.groupby(qi).ngroups,
        "unique_records": int((sizes == 1).sum()),
        "pct_unique": round(100 * (sizes == 1).mean(), 1),
        "below_k": int((sizes < K_TARGET).sum()),
        "k": int(sizes.min()),
        "avg_risk_pct": round(100 * (1 / sizes).mean(), 1),   # average chance of a correct re-identification
        "max_risk_pct": round(100 * (1 / sizes).max(), 1),
    }


def show(title, m):
    log(f"--- {title}")
    log(f"records={m['records']}  equivalence classes={m['classes']}  k={m['k']}  "
        f"records in groups smaller than {K_TARGET}: {m['below_k']}")
    log(f"records unique on QIs = {m['unique_records']} ({m['pct_unique']}%)")
    log(f"average re-identification risk = {m['avg_risk_pct']}%   maximum = {m['max_risk_pct']}%")


# Generalisation hierarchies
REGION = {"Emirati": "Gulf", "Jordanian": "Levant", "Lebanese": "Levant", "Syrian": "Levant",
          "Egyptian": "North Africa", "Moroccan": "North Africa",
          "Indian": "South Asia", "Pakistani": "South Asia"}
WIDE_REGION = {"Gulf": "MENA", "Levant": "MENA", "North Africa": "MENA", "South Asia": "South Asia"}
EMIRATE = {"Dubai Marina": "Dubai", "Deira": "Dubai", "Al Barsha": "Dubai", "Jumeirah": "Dubai",
           "Mirdif": "Dubai", "Al Nahda (Sharjah)": "Sharjah", "Al Majaz": "Sharjah",
           "Al Khan": "Sharjah", "Muwaileh": "Sharjah"}


def band(dob, width):
    year = int(dob[:4])
    start = year - (year - 2002) % width          # bands start at 2002: 2002-2003 or 2002-2005
    return f"{start}-{start + width - 1}"


def generalise(df, level):
    """Return the QI columns generalised to the given level (1, 2 or 3)."""
    out = pd.DataFrame(index=df.index)
    out["birth_band"] = df["date_of_birth"].map(lambda d: band(d, 2 if level == 1 else 4))
    out["gender"] = df["gender"]
    region = df["nationality"].map(REGION)
    out["region"] = region if level == 1 else region.map(WIDE_REGION)
    out["emirate"] = df["home_area"].map(EMIRATE) if level < 3 else "UAE"
    out["programme"] = df["programme"]
    return out


LEVEL_TEXT = {
    1: "DOB -> 2-year band, nationality -> region (Gulf/Levant/North Africa/South Asia), home_area -> emirate",
    2: "DOB -> 4-year band, region -> MENA / South Asia, emirate kept",
    3: "as level 2 and emirate suppressed (all 'UAE')",
}


def main():
    df = pd.read_csv(SRC, dtype=str)
    df["gpa"] = df["gpa"].astype(float)
    qi_before = ["date_of_birth", "gender", "nationality", "home_area", "programme"]
    qi_after = ["birth_band", "gender", "region", "emirate", "programme"]

    log("CampusShield privacy evaluation (synthetic data only)")
    log(f"input: {SRC.relative_to(ROOT).as_posix()}  records: {len(df)}")
    log("direct identifiers: full_name, student_id, email")
    log(f"quasi-identifiers : {', '.join(qi_before)}")
    log(f"sensitive attribute: scholarship   target: k >= {K_TARGET}, suppress at most {MAX_SUPPRESS_PCT}% of rows")
    log()
    before = metrics(df, qi_before)
    show("BEFORE (raw data)", before)
    log()

    # ---- suppression of direct identifiers + keyed pseudonym
    key_env = os.environ.get("CAMPUSHIELD_PSEUDO_KEY")
    key = key_env.encode() if key_env else secrets.token_bytes(32)
    log("step 1: drop full_name and email; student_id -> HMAC-SHA256 pseudonym "
        f"({'key from CAMPUSHIELD_PSEUDO_KEY' if key_env else 'random 256-bit key for this run, not saved'})")
    pseudo = [hmac.new(key, sid.encode(), hashlib.sha256).hexdigest()[:12] for sid in df["student_id"]]
    log()

    # ---- generalise level by level
    stages = [("Raw data", before)]
    chosen = None
    for level in (1, 2, 3):
        qi = generalise(df, level)
        m = metrics(qi, qi_after)
        log(f"step 2.{level}: generalisation level {level}: {LEVEL_TEXT[level]}")
        show(f"AFTER level-{level} generalisation", m)
        log()
        stages.append((f"Generalised L{level}", m))
        if 100 * m["below_k"] / len(df) <= MAX_SUPPRESS_PCT:
            chosen = level
            break
    if chosen is None:
        chosen = 3
    qi = generalise(df, chosen)

    anon = pd.concat([pd.Series(pseudo, name="pseudo_id", index=df.index), qi,
                      df[["year", "gpa", "scholarship"]]], axis=1)

    # ---- suppress records still in groups smaller than K_TARGET
    sizes = anon.groupby(qi_after)["pseudo_id"].transform("size")
    suppressed = int((sizes < K_TARGET).sum())
    final = anon[sizes >= K_TARGET].reset_index(drop=True)
    log(f"step 3: kept generalisation level {chosen}; suppressed {suppressed} record(s) "
        f"({round(100 * suppressed / len(df), 1)}%) still in groups smaller than {K_TARGET}")
    after = metrics(final, qi_after)
    show("AFTER (final released table)", after)
    stages.append((f"Final (L{chosen} + suppression)", after))
    log()

    # l-diversity check on the sensitive attribute
    groups = final.groupby(qi_after)["scholarship"].nunique()
    log(f"homogeneity check: {int((groups == 1).sum())} of {len(groups)} released groups have only one "
        "scholarship value (an attacker who places someone in that group learns it)")
    log()

    # ---- utility check
    log("--- Utility check: mean GPA per programme")
    util = pd.DataFrame({"gpa_before": df.groupby("programme")["gpa"].mean().round(2),
                         "gpa_after": final.groupby("programme")["gpa"].mean().round(2),
                         "n_before": df.groupby("programme").size(),
                         "n_after": final.groupby("programme").size()})
    log(util.to_string())
    log(f"scholarship counts before: {df['scholarship'].value_counts().to_dict()}")
    log(f"scholarship counts after : {final['scholarship'].value_counts().to_dict()}")
    log("no longer possible after release: exact age, nationality-level statistics,")
    log("neighbourhood-level analysis, contacting a student, joining with other data by student_id.")
    log()
    log("NOTE: pseudo_id is a keyed pseudonym. Anyone holding the key (or a lookup table)")
    log("can re-link it to the student. This is pseudonymisation, not full anonymisation.")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUT_CSV, index=False)
    log(f"released table written to {OUT_CSV.relative_to(ROOT).as_posix()} ({len(final)} rows)")

    # ---- chart
    EVID.mkdir(parents=True, exist_ok=True)
    labels = ["Records unique on QIs (%)", "Average re-id risk (%)", "Maximum re-id risk (%)"]
    keys = ["pct_unique", "avg_risk_pct", "max_risk_pct"]
    colours = ["#a4161a", "#e08e0b", "#d4b106", "#5b8db8", "#1f4e79"]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    width = 0.8 / len(stages)
    for i, (name, m) in enumerate(stages):
        xs = [j + i * width for j in range(len(keys))]
        bars = ax.bar(xs, [m[k] for k in keys], width, label=f"{name}: k={m['k']}, n={m['records']}",
                      color=colours[i % len(colours)])
        ax.bar_label(bars, fmt="%.0f", fontsize=8)
    ax.set_xticks([j + width * (len(stages) - 1) / 2 for j in range(len(keys))])
    ax.set_xticklabels(labels)
    ax.set_ylabel("percent of records")
    ax.set_ylim(0, 115)
    ax.set_title("Re-identification exposure before and after de-identification (synthetic data)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    fig.tight_layout()
    fig.savefig(EVID / "k_anonymity_before_after.png", dpi=150)
    log(f"chart written to {(EVID / 'k_anonymity_before_after.png').relative_to(ROOT).as_posix()}")

    # ---- sensitivity: what each k would cost at each generalisation level
    log()
    log("--- Cost of stronger protection (rows that would have to be suppressed)")
    log("level | k=2 suppressed | k=3 suppressed")
    for level in (1, 2, 3):
        s = generalise(df, level).groupby(qi_after)["gender"].transform("size")
        log(f"  L{level}  |      {int((s < 2).sum()):>2}/{len(df)}     |      {int((s < 3).sum()):>2}/{len(df)}")

    (EVID / "privacy_output.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
