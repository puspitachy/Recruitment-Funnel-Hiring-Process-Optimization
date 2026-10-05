"""
02_clean_data.py
Cleans the raw recruitment files and writes analysis-ready CSVs to data/clean/.
Every fix is logged to data/clean/cleaning_log.csv for the report.
"""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW, CLEAN = BASE / "data" / "raw", BASE / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)
log = []

def note(table, step, rows, detail):
    log.append({"table": table, "step": step, "rows_affected": int(rows), "detail": detail})
    print(f"[{table}] {step}: {rows:,} - {detail}")

t = {n: pd.read_csv(RAW / f"{n}.csv") for n in
     ["departments", "recruiters", "requisitions", "candidates", "applications", "stage_events", "offers", "hires",
      "source_spend"]}
for n, df in t.items():
    note(n, "Loaded", len(df), "raw rows")

# ---------------------------------------------------------------- candidates
c = t["candidates"]
txt = c.expected_salary.astype(str).str.contains(r"[$k]", na=False)
c["expected_salary"] = pd.to_numeric(
    c.expected_salary.astype(str).str.replace("$", "", regex=False).str.replace("k", "000", regex=False))
note("candidates", "Converted salary text", txt.sum(), "'$95k' -> 95000")
miss = c.gender.isna().sum()
c["gender"] = c.gender.fillna("Not recorded")
note("candidates", "Filled missing gender", miss, "blank -> 'Not recorded' (kept separate from 'Prefer not to say')")

# ---------------------------------------------------------------- applications
a = t["applications"]
d = a.duplicated().sum(); a = a.drop_duplicates()
note("applications", "Removed duplicate rows", d, "exact duplicate application records")
src_map = {"linkedin": "LinkedIn", "linked in": "LinkedIn", "job board": "Job Boards", "job boards": "Job Boards",
           "indeed/job boards": "Job Boards", "referral": "Employee Referral", "employee referral": "Employee Referral",
           "careers site": "Company Website", "company website": "Company Website"}
key = a.source.str.strip().str.lower()
fix = key.isin(src_map) & ~a.source.isin(src_map.values())
a.loc[fix, "source"] = key[fix].map(src_map)
note("applications", "Standardised source names", fix.sum(), "e.g. 'linkedin', 'Linked In' -> 'LinkedIn'")
miss = a.source.isna().sum(); a["source"] = a.source.fillna("Unknown")
note("applications", "Filled missing source", miss, "blank -> 'Unknown'")
us = a.applied_date.str.contains("/", na=False)
a["applied_date"] = pd.to_datetime(a.applied_date, format="mixed")
note("applications", "Fixed date format", us.sum(), "MM/DD/YYYY text converted to a real date")
a["outcome_date"] = pd.to_datetime(a.outcome_date)

# ---------------------------------------------------------------- stage events
e = t["stage_events"]
d = e.duplicated().sum(); e = e.drop_duplicates()
note("stage_events", "Removed duplicate rows", d, "exact duplicate stage records")
e["entered_date"] = pd.to_datetime(e.entered_date); e["exited_date"] = pd.to_datetime(e.exited_date)
sw = e.exited_date < e.entered_date
e.loc[sw, ["entered_date", "exited_date"]] = e.loc[sw, ["exited_date", "entered_date"]].values
note("stage_events", "Fixed swapped dates", sw.sum(), "exit date before entry date -> swapped back")
e["days_in_stage"] = (e.exited_date - e.entered_date).dt.days
e = e.sort_values(["application_id", "stage_order"])

# ---------------------------------------------------------------- integrity checks
assert a.application_id.is_unique and c.candidate_id.is_unique
assert a.requisition_id.isin(t["requisitions"].requisition_id).all()
assert a.candidate_id.isin(c.candidate_id).all()
assert e.application_id.isin(a.application_id).all()
assert (e.days_in_stage.dropna() >= 0).all()
assert set(a.source) <= {"LinkedIn", "Job Boards", "Company Website", "Employee Referral", "Recruitment Agency",
                         "Campus Recruiting", "Social Media", "Unknown"}
note("applications", "Final clean rows", len(a), f"{(a.outcome == 'Hired').sum():,} hires")

for n, df in {**t, "candidates": c, "applications": a, "stage_events": e}.items():
    df.to_csv(CLEAN / f"{n}.csv", index=False, date_format="%Y-%m-%d")
pd.DataFrame(log).to_csv(CLEAN / "cleaning_log.csv", index=False)
