"""
01_generate_data.py
Generates a realistic synthetic recruitment dataset (Jan 2024 - Dec 2025) for the
Recruitment Funnel & Hiring Process Optimization capstone.

Output (data/raw/):
  departments.csv, recruiters.csv, requisitions.csv, candidates.csv,
  applications.csv, stage_events.csv, offers.csv, hires.csv, source_spend.csv

Hiring stages (each application moves through them in order):
  Resume Screen -> Phone Screen -> Skills Assessment -> Onsite Interview -> Offer -> Hired

Patterns deliberately built in for the analysis to discover:
  - Onsite Interview is the bottleneck (panel scheduling), worst in Engineering / Data
  - The longer candidates wait, the more of them withdraw (often to accept another offer)
  - Offers below the candidate's expected salary, and slow processes, get declined
  - Referrals convert better, hire faster, cost less and stay longer; job boards bring
    volume but low conversion; agencies convert well but are expensive
  - Recruiters with heavy workloads move candidates more slowly
  - December slows everything down (holidays)
The raw files also contain data-quality problems for the cleaning step.
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(2024)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

START, SNAPSHOT = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
N_REQS = 420
STAGES = ["Resume Screen", "Phone Screen", "Skills Assessment", "Onsite Interview", "Offer"]

# ------------------------------------------------------------------ departments
DEPTS = pd.DataFrame([
    # id, name, req weight, applicants per req, resume-screen factor, base salary (Mid level), onsite extra days
    ("D01", "Engineering",       0.24, 70, 0.80, 135000, 7),
    ("D02", "Data & Analytics",  0.10, 75, 0.85, 120000, 6),
    ("D03", "Product",           0.07, 80, 0.75, 130000, 3),
    ("D04", "Sales",             0.16, 60, 1.15,  85000, 0),
    ("D05", "Marketing",         0.09, 85, 0.95,  90000, 1),
    ("D06", "Customer Support",  0.14, 95, 1.25,  55000, 0),
    ("D07", "Finance",           0.07, 60, 1.00,  95000, 1),
    ("D08", "Human Resources",   0.05, 70, 1.05,  80000, 0),
    ("D09", "Operations",        0.08, 65, 1.10,  75000, 0),
], columns=["department_id", "department_name", "w", "apps", "screen_f", "salary", "onsite_extra"])
departments = DEPTS[["department_id", "department_name"]].copy()
departments["department_head"] = [f"Head of {d}" for d in departments.department_name]

# ------------------------------------------------------------------ recruiters
REC_NAMES = ["Maya Patel", "Jordan Lee", "Sofia Ramirez", "Ethan Brooks", "Priya Nair",
             "Lucas Martin", "Hannah Cole", "Omar Haddad", "Grace Chen", "Daniel Reyes"]
recruiters = pd.DataFrame({
    "recruiter_id": [f"R{i+1:02d}" for i in range(10)],
    "recruiter_name": REC_NAMES,
    "team": ["Tech", "Tech", "Tech", "Tech", "Business", "Business", "Business", "Business", "G&A", "G&A"],
    "start_date": pd.to_datetime(["2019-03-04", "2021-06-14", "2022-09-12", "2023-11-06", "2018-01-15",
                                  "2020-08-03", "2023-02-20", "2021-04-12", "2017-10-02", "2022-05-16"]).date,
})
REC_SPEED = dict(zip(recruiters.recruiter_id, [0.85, 1.0, 1.05, 1.25, 0.9, 1.0, 1.2, 0.95, 0.9, 1.1]))
TEAM_DEPTS = {"Tech": ["Engineering", "Data & Analytics", "Product"],
              "Business": ["Sales", "Marketing", "Customer Support"],
              "G&A": ["Finance", "Human Resources", "Operations"]}
REC_TEAM = dict(zip(recruiters.recruiter_id, recruiters.team))
# uneven workload: some recruiters get many more requisitions
REC_LOAD_W = dict(zip(recruiters.recruiter_id, [1.0, 1.6, 0.8, 0.9, 1.0, 1.7, 0.7, 1.0, 1.2, 0.8]))

# ------------------------------------------------------------------ titles / levels
TITLES = {
    "Engineering": ["Software Engineer", "Backend Engineer", "Frontend Engineer", "DevOps Engineer", "QA Engineer"],
    "Data & Analytics": ["Data Analyst", "Data Engineer", "Data Scientist", "BI Developer"],
    "Product": ["Product Manager", "Product Designer", "UX Researcher"],
    "Sales": ["Account Executive", "Sales Development Rep", "Account Manager"],
    "Marketing": ["Marketing Specialist", "Content Strategist", "Growth Marketer"],
    "Customer Support": ["Support Specialist", "Customer Success Manager", "Support Team Lead"],
    "Finance": ["Financial Analyst", "Accountant", "FP&A Manager"],
    "Human Resources": ["HR Generalist", "Talent Partner", "Payroll Specialist"],
    "Operations": ["Operations Analyst", "Project Coordinator", "Procurement Specialist"],
}
LEVELS = ["Entry", "Mid", "Senior", "Lead"]
LEVEL_P = [0.25, 0.40, 0.25, 0.10]
LEVEL_SAL = {"Entry": 0.72, "Mid": 1.0, "Senior": 1.3, "Lead": 1.55}
LEVEL_EXP = {"Entry": (0, 2), "Mid": (2, 5), "Senior": (5, 9), "Lead": (8, 15)}
LEVEL_APPS = {"Entry": 1.4, "Mid": 1.0, "Senior": 0.75, "Lead": 0.5}
LOCATIONS = ["New York", "Austin", "Chicago", "Remote"]

# ------------------------------------------------------------------ sources
SOURCES = pd.DataFrame([
    # name, share, resume pass, later-stage bonus, accept bonus, monthly attrition, perf mean
    ("LinkedIn",            0.29, 0.30, 0.00, 0.0, 0.014, 3.30),
    ("Job Boards",          0.33, 0.17, -0.04, -0.1, 0.028, 3.00),
    ("Company Website",     0.14, 0.27, 0.00, 0.2, 0.015, 3.30),
    ("Employee Referral",   0.08, 0.55, 0.10, 0.8, 0.005, 3.65),
    ("Recruitment Agency",  0.06, 0.50, 0.05, 0.0, 0.028, 3.35),
    ("Campus Recruiting",   0.05, 0.36, -0.02, 0.3, 0.020, 3.20),
    ("Social Media",        0.05, 0.14, -0.05, -0.1, 0.028, 3.00),
], columns=["source", "share", "resume_p", "bonus", "accept_b", "attr", "perf"]).set_index("source")

DECLINE = ["Compensation below expectations", "Accepted another offer", "Counter-offer from current employer",
           "Role/fit concerns", "Location or work-mode preference"]
WITHDRAW_SLOW = ["Accepted another offer", "Process took too long"]
WITHDRAW_OTHER = ["Lost interest in role", "Personal reasons", "Compensation expectations", "Relocation not possible"]
REJECT = {"Resume Screen": "Does not meet requirements", "Phone Screen": "Communication or motivation fit",
          "Skills Assessment": "Did not pass assessment", "Onsite Interview": "Not selected after interviews",
          "Offer": "Offer rescinded"}

# ------------------------------------------------------------------ requisitions
open_days = pd.date_range(START, "2025-12-12", freq="D")
w = np.where(open_days.month == 12, 0.4, 1.0) * np.where(open_days.dayofweek < 5, 1, 0.05)
req_dates = np.sort(rng.choice(open_days, N_REQS, p=w / w.sum()))
dept_rows = DEPTS.sample(N_REQS, replace=True, weights="w", random_state=3).reset_index(drop=True)
reqs = []
for i, (d_open, dept) in enumerate(zip(req_dates, dept_rows.itertuples())):
    team = next(t for t, ds in TEAM_DEPTS.items() if dept.department_name in ds)
    recs = [r for r in REC_TEAM if REC_TEAM[r] == team]
    rw = np.array([REC_LOAD_W[r] for r in recs])
    level = rng.choice(LEVELS, p=LEVEL_P)
    mid = dept.salary * LEVEL_SAL[level]
    reqs.append({
        "requisition_id": f"REQ-{1001 + i}",
        "department_id": dept.department_id,
        "job_title": ("Senior " if level == "Senior" else "Lead " if level == "Lead" else "Junior " if level == "Entry" else "")
                     + rng.choice(TITLES[dept.department_name]),
        "job_level": level,
        "location": rng.choice(LOCATIONS, p=[0.3, 0.2, 0.2, 0.3]),
        "recruiter_id": rng.choice(recs, p=rw / rw.sum()),
        "hiring_manager": f"HM-{dept.department_id[1:]}{rng.integers(1, 6)}",
        "headcount": int(rng.choice([1, 1, 1, 1, 2, 2, 3])) if level in ("Entry", "Mid") else 1,
        "salary_min": int(round(mid * 0.88, -3)), "salary_max": int(round(mid * 1.12, -3)),
        "opened_date": pd.Timestamp(d_open),
    })
reqs = pd.DataFrame(reqs)
dept_info = DEPTS.set_index("department_id")

# recruiter workload = concurrent open requisitions (approximation: reqs opened in the trailing 90 days)
def workload(rec, date):
    r = reqs[(reqs.recruiter_id == rec) & (reqs.opened_date <= date) & (reqs.opened_date > date - pd.Timedelta(days=90))]
    return len(r)

# ------------------------------------------------------------------ helpers
def holiday_mult(t):
    return 1.35 if (t.month == 12 and t.day >= 10) or (t.month == 1 and t.day <= 5) else 1.0

def gamma_days(mean, shape=2.2):
    return max(0.5, rng.gamma(shape, mean / shape))

candidates, apps, events, offers = [], [], [], []
cand_pool = []  # reuse some candidates across applications
cid = aid = eid = oid = 0

for req in reqs.itertuples():
    dept = dept_info.loc[req.department_id]
    load = workload(req.recruiter_id, req.opened_date)
    rec_f = REC_SPEED[req.recruiter_id] * (1 + 0.035 * max(0, load - 8))   # heavy workload -> slower
    n = int(rng.poisson(dept.apps * LEVEL_APPS[req.job_level] * (1.7 if req.location == "Remote" else 1.0)))
    n = max(n, 8)
    applied = np.sort(req.opened_date + pd.to_timedelta(np.minimum(rng.exponential(13, n), 75), unit="D"))
    src_p = SOURCES.share.copy()
    if req.job_level == "Entry":
        src_p["Campus Recruiting"] *= 5; src_p["Recruitment Agency"] *= 0.2
    elif req.job_level in ("Senior", "Lead"):
        src_p["Campus Recruiting"] = 0; src_p["Recruitment Agency"] *= 2.5
    src_p /= src_p.sum()
    req_apps = []
    for a_date in applied:
        a_date = pd.Timestamp(a_date).normalize()
        src = rng.choice(SOURCES.index, p=src_p)
        S = SOURCES.loc[src]
        # candidate
        if cand_pool and rng.random() < 0.08:
            cand = cand_pool[int(rng.integers(len(cand_pool)))]
        else:
            lo, hi = LEVEL_EXP[req.job_level]
            exp_yrs = max(0, round(rng.uniform(lo - 1.5, hi + 2), 1))
            mid = (req.salary_min + req.salary_max) / 2
            cand = {"candidate_id": f"CAND-{100001 + cid}",
                    "gender": rng.choice(["Female", "Male", "Non-binary", "Prefer not to say"], p=[0.45, 0.49, 0.02, 0.04]),
                    "years_experience": exp_yrs,
                    "highest_education": rng.choice(["High School", "Bachelor's", "Master's", "PhD"], p=[0.08, 0.6, 0.28, 0.04]),
                    "current_city": rng.choice(["New York", "Austin", "Chicago", "Boston", "Seattle", "Denver",
                                                "Atlanta", "Los Angeles", "Miami", "Dallas"]),
                    "expected_salary": int(round(mid * rng.normal(1.04, 0.10), -3))}
            cid += 1
            candidates.append(cand); cand_pool.append(cand)
        lo, hi = LEVEL_EXP[req.job_level]
        fit = 0.65 if cand["years_experience"] < lo else 1.0
        aid += 1
        app = {"application_id": f"APP-{200000 + aid}", "candidate_id": cand["candidate_id"],
               "requisition_id": req.requisition_id, "source": src, "applied_date": a_date}
        # walk the stages (contiguous: a stage is entered when the previous one is completed)
        t, path = a_date, []
        for k, stage in enumerate(STAGES):
            if stage == "Resume Screen":
                dur = gamma_days(4.0 * rec_f); p_pass = S.resume_p * dept.screen_f * fit
            elif stage == "Phone Screen":
                dur = gamma_days(6.0 * rec_f); p_pass = 0.62 + S.bonus
            elif stage == "Skills Assessment":
                dur = gamma_days(7.0); p_pass = 0.58 + S.bonus
            elif stage == "Onsite Interview":
                dur = gamma_days(11.0 + dept.onsite_extra + (3 if req.job_level in ("Senior", "Lead") else 0), shape=3)
                p_pass = 0.47 + S.bonus * 1.5
            else:  # Offer: approvals + candidate decision
                dur = gamma_days(6.0 + (3.0 if req.job_level in ("Senior", "Lead") else 0)) + gamma_days(3.0)
            dur *= holiday_mult(t)
            elapsed = (t - a_date).days
            p_w = 0.004 if stage == "Resume Screen" else min(0.5, 0.010 + 0.0050 * dur + 0.0065 * elapsed)
            if stage == "Offer":
                offered = int(round(min(req.salary_max, max(req.salary_min,
                              (req.salary_min + req.salary_max) / 2 * rng.normal(1.0, 0.06))), -3))
                gap = max(0.0, (cand["expected_salary"] - offered) / cand["expected_salary"])
                days_total = elapsed + dur
                logit = (1.7 - 9.0 * gap - 0.045 * max(0, days_total - 30) + S.accept_b
                         - (0.6 if dept.department_name == "Sales" else 0) + (0.3 if req.location == "Remote" else 0))
                accept = rng.random() < 1 / (1 + np.exp(-logit))
                if accept:
                    res, reason = "Accepted", None
                else:
                    if gap > 0.05 and rng.random() < 0.65: reason = DECLINE[0]
                    elif days_total > 38 and rng.random() < 0.6: reason = DECLINE[1]
                    else: reason = rng.choice(DECLINE, p=[0.2, 0.25, 0.25, 0.15, 0.15])
                    res = "Declined"
                path.append([stage, t, t + pd.Timedelta(days=dur), res, reason,
                             {"offered_salary": offered, "offer_date": t + pd.Timedelta(days=dur * 0.6)}])
                break
            if rng.random() < p_w:
                reason = rng.choice(WITHDRAW_SLOW) if (elapsed + dur > 22 and rng.random() < 0.7) else rng.choice(WITHDRAW_OTHER)
                path.append([stage, t, t + pd.Timedelta(days=dur * rng.uniform(0.3, 1)), "Withdrew", reason, None]); break
            if rng.random() < p_pass:
                path.append([stage, t, t + pd.Timedelta(days=dur), "Passed", None, None]); t = t + pd.Timedelta(days=dur)
            else:
                path.append([stage, t, t + pd.Timedelta(days=dur), "Rejected", REJECT[stage], None]); break
        req_apps.append((app, path))

    # ---- fill the requisition: first `headcount` accepted offers (by acceptance date) are hires
    accepts = sorted([p[-1][2] for _, p in req_apps if p[-1][3] == "Accepted"])
    if len(accepts) >= req.headcount and accepts[req.headcount - 1] <= SNAPSHOT:
        cutoff, status, cut_reason = accepts[req.headcount - 1], "Filled", "Position filled"
    elif req.opened_date + pd.Timedelta(days=180) <= SNAPSHOT:
        cutoff, status, cut_reason = req.opened_date + pd.Timedelta(days=180), "Cancelled", "Requisition cancelled"
    else:
        cutoff, status, cut_reason = SNAPSHOT, "Open", None
    reqs.loc[req.Index, "status"] = status
    reqs.loc[req.Index, "closed_date"] = cutoff if status != "Open" else pd.NaT

    hired_count = 0
    for app, path in req_apps:
        if app["applied_date"] > cutoff:
            continue  # posting was closed
        kept = []
        for stage, ent, ext, res, reason, extra in path:
            if ent > cutoff:
                break
            if ext > cutoff and not (res == "Accepted" and ext == cutoff and hired_count < req.headcount):
                if status == "Open":
                    kept.append([stage, ent, None, "In Progress", None, extra if stage == "Offer" and extra["offer_date"] <= cutoff else None])
                elif stage != "Offer":  # an offer not yet made is simply never extended
                    kept.append([stage, ent, cutoff, "Rejected", cut_reason, None])
                break
            kept.append([stage, ent, ext, res, reason, extra])
        if status != "Open" and kept[-1][3] == "Passed":
            # passed a stage but the role closed before the next step
            kept[-1][3], kept[-1][4] = "Rejected", cut_reason
        if kept and kept[-1][3] == "Accepted":
            hired_count += 1
        last = kept[-1]
        outcome = {"Passed": "In Progress", "In Progress": "In Progress", "Rejected": "Rejected",
                   "Withdrew": "Withdrew", "Accepted": "Hired", "Declined": "Offer Declined"}[last[3]]
        app.update({"current_stage": "Hired" if outcome == "Hired" else last[0], "outcome": outcome,
                    "outcome_reason": last[4], "outcome_date": last[2]})
        apps.append(app)
        for order, (stage, ent, ext, res, reason, extra) in enumerate(kept, 1):
            eid += 1
            events.append({"event_id": eid, "application_id": app["application_id"], "stage": stage,
                           "stage_order": order, "entered_date": ent, "exited_date": ext,
                           "result": res, "reason": reason})
            if stage == "Offer" and extra is not None:
                oid += 1
                offers.append({"offer_id": f"OFR-{5001 + oid}", "application_id": app["application_id"],
                               "offer_date": extra["offer_date"].normalize(), "offered_salary": extra["offered_salary"],
                               "response_date": ext.normalize() if ext is not None else None,
                               "offer_status": {"Accepted": "Accepted", "Declined": "Declined",
                                                "In Progress": "Pending", "Rejected": "Rescinded"}[res],
                               "decline_reason": reason if res == "Declined" else None})

applications = pd.DataFrame(apps)
stage_events = pd.DataFrame(events)
offers_df = pd.DataFrame(offers)
candidates_df = pd.DataFrame(candidates)
for c in ["entered_date", "exited_date"]:
    stage_events[c] = pd.to_datetime(stage_events[c]).dt.normalize()
stage_events = stage_events[stage_events.entered_date <= SNAPSHOT]

# ------------------------------------------------------------------ hires + quality
hired = applications[applications.outcome == "Hired"].merge(offers_df[offers_df.offer_status == "Accepted"],
                                                            on="application_id")
hire_rows = []
for i, h in enumerate(hired.itertuples()):
    S = SOURCES.loc[h.source]
    start = pd.Timestamp(h.response_date) + pd.Timedelta(days=int(rng.integers(14, 36)))
    months_to_exit = rng.exponential(1 / S.attr)
    exit_date = start + pd.Timedelta(days=int(months_to_exit * 30.4))
    active = exit_date > SNAPSHOT or start > SNAPSHOT
    tenure_m = ((min(exit_date, SNAPSHOT) - start).days / 30.4)
    perf = int(np.clip(round(rng.normal(S.perf, 0.8)), 1, 5)) if tenure_m >= 6 else None
    hire_rows.append({"hire_id": f"HIRE-{3001 + i}", "application_id": h.application_id,
                      "start_date": start.date(),
                      "employment_status": "Active" if active else "Left",
                      "exit_date": None if active else exit_date.date(),
                      "performance_rating_6m": perf})
hires = pd.DataFrame(hire_rows)

# ------------------------------------------------------------------ source spend (monthly)
months = pd.period_range("2024-01", "2025-12", freq="M")
spend = []
fixed = {"LinkedIn": 7000, "Job Boards": 4500, "Social Media": 1800, "Company Website": 1000}
for m in months:
    for s, base in fixed.items():
        spend.append((str(m), s, "Subscription / advertising", round(base * rng.uniform(0.9, 1.1), 2)))
    spend.append((str(m), "Campus Recruiting", "Career fairs & events",
                  round((9500 if m.month in (3, 4, 9, 10) else 600) * rng.uniform(0.9, 1.1), 2)))
hm = hired.assign(month=pd.to_datetime(hired.response_date).dt.to_period("M").astype(str))
for r in hm.itertuples():
    if r.source == "Recruitment Agency":
        spend.append((r.month, r.source, "Agency fee (20% of salary)", round(0.20 * r.offered_salary, 2)))
    elif r.source == "Employee Referral":
        spend.append((r.month, r.source, "Referral bonus", 2500.0))
source_spend = (pd.DataFrame(spend, columns=["month", "source", "spend_type", "amount"])
                .groupby(["month", "source", "spend_type"], as_index=False).amount.sum())

# ------------------------------------------------------------------ finalise + inject data-quality issues
reqs["opened_date"] = reqs.opened_date.dt.date
reqs["closed_date"] = pd.to_datetime(reqs.closed_date).dt.date
applications["applied_date"] = applications.applied_date.dt.date
applications["outcome_date"] = pd.to_datetime(applications.outcome_date).dt.date
reqs = reqs[["requisition_id", "department_id", "job_title", "job_level", "location", "recruiter_id", "hiring_manager",
             "headcount", "salary_min", "salary_max", "opened_date", "closed_date", "status"]]

raw_apps = applications.copy().astype({"applied_date": object})
variants = {"LinkedIn": ["linkedin", "LinkedIn ", "Linked In"], "Job Boards": ["Job Board", "job boards", "Indeed/Job Boards"],
            "Employee Referral": ["Referral", "employee referral"], "Company Website": ["Careers Site", "company website"]}
idx = raw_apps.sample(frac=0.06, random_state=1).index
raw_apps.loc[idx, "source"] = [rng.choice(variants[s]) if s in variants else s for s in raw_apps.loc[idx, "source"]]
idx = raw_apps.sample(frac=0.03, random_state=2).index                               # US-style date text
raw_apps.loc[idx, "applied_date"] = [pd.Timestamp(d).strftime("%m/%d/%Y") for d in raw_apps.loc[idx, "applied_date"]]
idx = raw_apps.sample(frac=0.004, random_state=3).index; raw_apps.loc[idx, "source"] = None   # missing source
raw_apps = pd.concat([raw_apps, raw_apps.sample(frac=0.008, random_state=4)])          # duplicate rows
raw_apps = raw_apps.sample(frac=1, random_state=5).reset_index(drop=True)

raw_cands = candidates_df.copy().astype({"expected_salary": object})
idx = raw_cands.sample(frac=0.02, random_state=6).index                               # "$95k" text salaries
raw_cands.loc[idx, "expected_salary"] = [f"${v // 1000}k" for v in raw_cands.loc[idx, "expected_salary"]]
idx = raw_cands.sample(frac=0.01, random_state=7).index; raw_cands.loc[idx, "gender"] = None

raw_events = stage_events.copy()
idx = raw_events[raw_events.exited_date.notna()].sample(n=80, random_state=8).index    # swapped dates
raw_events.loc[idx, ["entered_date", "exited_date"]] = raw_events.loc[idx, ["exited_date", "entered_date"]].values
raw_events = pd.concat([raw_events, raw_events.sample(n=150, random_state=9)])         # duplicate events
for c in ["entered_date", "exited_date"]:
    raw_events[c] = pd.to_datetime(raw_events[c]).dt.date

departments.to_csv(OUT / "departments.csv", index=False)
recruiters.to_csv(OUT / "recruiters.csv", index=False)
reqs.to_csv(OUT / "requisitions.csv", index=False)
raw_cands.to_csv(OUT / "candidates.csv", index=False)
raw_apps.to_csv(OUT / "applications.csv", index=False)
raw_events.to_csv(OUT / "stage_events.csv", index=False)
offers_df.to_csv(OUT / "offers.csv", index=False)
hires.to_csv(OUT / "hires.csv", index=False)
source_spend.to_csv(OUT / "source_spend.csv", index=False)

print(f"requisitions {len(reqs)} ({reqs.status.value_counts().to_dict()})")
print(f"candidates {len(candidates_df):,} | applications {len(applications):,} | events {len(stage_events):,}")
print(f"offers {len(offers_df):,} ({offers_df.offer_status.value_counts().to_dict()}) | hires {len(hires):,}")
print(applications.outcome.value_counts().to_dict())
