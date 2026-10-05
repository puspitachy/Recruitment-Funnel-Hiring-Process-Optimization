# Power BI Dashboard Guide
**Recruitment Funnel & Hiring Process Optimization**

This guide walks you through building the final dashboard in Power BI Desktop from the files in `data/powerbi/`. It takes about 2–3 hours the first time. When you finish, save it as `powerbi/recruitment_dashboard.pbix`.

---

## 1. Files to load

| File | Rows | What it is | Table type |
|---|---|---|---|
| `fact_applications.csv` | 34,673 | One row per application: source, department, recruiter, stage flags, days per stage, offer, hire | Fact |
| `fact_stage_events.csv` | 52,128 | One row per stage a candidate entered, with result and days in stage | Fact |
| `fact_requisitions.csv` | 420 | One row per job opening: status, time to fill, applications, hires | Fact |
| `fact_source_spend.csv` | 165 | Monthly recruiting spend by source | Fact |
| `dim_departments.csv` | 9 | Departments | Dimension |
| `dim_recruiters.csv` | 10 | Recruiters and teams | Dimension |
| `dim_candidates.csv` | 33,292 | Candidate profile | Dimension |
| `theme/recruitment_theme.json` | – | Colour theme for the report | Theme |

**Get Data → Text/CSV** for each file → **Transform Data** (do not just click Load).

---

## 2. Power Query clean-up (Transform Data)

Do these in the Power Query editor before loading:

1. **Set data types**
   - All `*_date` columns → **Date**
   - `days_*`, `time_to_hire_days`, `time_to_fill_days`, `days_in_process`, `reached_*`, `is_hired`, `withdrew_flag`, `lost_to_speed_flag` → **Whole Number**
   - `expected_salary`, `offered_salary`, `amount` → **Fixed Decimal (Currency)**
   - `offer_vs_expected_pct` → **Decimal Number**
2. **fact_source_spend:** add a column `month_date` = `Date.FromText([month] & "-01")` and set it to **Date**.
3. **fact_applications:** add a conditional column `outcome_group`:
   - `Hired` → "Hired"; `Offer Declined` → "Lost - declined offer"; `Withdrew` → "Lost - withdrew"; `In Progress` → "In progress"; otherwise "Rejected".
4. Remove columns you will not use (`candidate_id` stays — it links to `dim_candidates`).
5. **Close & Apply.**

---

## 3. Extra tables (Modeling → New table)

### Date table
```DAX
Dim_Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2026, 3, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "mmm" ),
    "Year-Month", FORMAT ( [Date], "yyyy-mm" )
)
```
Mark it as a date table: **Table tools → Mark as date table → Date**. Sort `Month` by `Month Number`.

### Source table (shared by applications and spend)
```DAX
Dim_Source =
DISTINCT (
    UNION (
        SELECTCOLUMNS ( fact_applications, "source", fact_applications[source] ),
        SELECTCOLUMNS ( fact_source_spend, "source", fact_source_spend[source] )
    )
)
```

### Stage table (keeps funnel stages in the right order)
```DAX
Dim_Stage =
DATATABLE (
    "Stage", STRING, "Stage Order", INTEGER,
    {
        { "Resume Screen", 1 }, { "Phone Screen", 2 }, { "Skills Assessment", 3 },
        { "Onsite Interview", 4 }, { "Offer", 5 }
    }
)
```
Sort `Stage` by `Stage Order`.

---

## 4. Data model (Model view)

Create these relationships (all **one-to-many, single direction**, from the dimension to the fact):

| From (one side) | To (many side) |
|---|---|
| `Dim_Date[Date]` | `fact_applications[applied_date]` (active) |
| `Dim_Date[Date]` | `fact_applications[outcome_date]` (**inactive** – used for hires by month) |
| `Dim_Date[Date]` | `fact_requisitions[opened_date]` |
| `Dim_Date[Date]` | `fact_source_spend[month_date]` |
| `Dim_Source[source]` | `fact_applications[source]` |
| `Dim_Source[source]` | `fact_source_spend[source]` |
| `dim_departments[department_name]` | `fact_applications[department_name]` |
| `dim_departments[department_name]` | `fact_requisitions[department_name]` |
| `dim_recruiters[recruiter_id]` | `fact_applications[recruiter_id]` |
| `dim_recruiters[recruiter_name]` | `fact_requisitions[recruiter_name]` |
| `dim_candidates[candidate_id]` | `fact_applications[candidate_id]` |
| `fact_applications[application_id]` | `fact_stage_events[application_id]` |
| `Dim_Stage[Stage]` | `fact_stage_events[stage]` |

> `dim_recruiters` links to applications by `recruiter_id` and to requisitions by `recruiter_name` (names are unique in this dataset). In a real company you would add `recruiter_id` to the requisitions file and use the ID for both.

Hide the foreign-key columns in the fact tables (right-click → *Hide in report view*) so report builders use the dimension columns.

---

## 5. DAX measures

Create a blank table called `_Measures` (**Enter data** → one empty column → Load) and put all measures there. Format each one as shown.

### Volume
```DAX
Applications = COUNTROWS ( fact_applications )                                   -- Whole number

Hires = SUM ( fact_applications[is_hired] )                                       -- Whole number

Requisitions = COUNTROWS ( fact_requisitions )                                    -- Whole number

Open Requisitions =
CALCULATE ( [Requisitions], fact_requisitions[status] = "Open" )

Hires by Hire Date =                                                              -- use on monthly trend
CALCULATE (
    [Hires],
    USERELATIONSHIP ( Dim_Date[Date], fact_applications[outcome_date] )
)
```

### Funnel
```DAX
Reached Phone Screen = SUM ( fact_applications[reached_phone_screen] )
Reached Assessment   = SUM ( fact_applications[reached_assessment] )
Reached Onsite       = SUM ( fact_applications[reached_onsite] )
Reached Offer        = SUM ( fact_applications[reached_offer] )

Application to Hire % = DIVIDE ( [Hires], [Applications] )                        -- Percentage, 2 dp

Applications per Hire = DIVIDE ( [Applications], [Hires] )                        -- Whole number

Stage Pass Rate % =                                                               -- use with Dim_Stage
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_stage_events ),
                fact_stage_events[result] IN { "Passed", "Accepted" } ),
    COUNTROWS ( fact_stage_events )
)

Stage Withdrawal Rate % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_stage_events ), fact_stage_events[result] = "Withdrew" ),
    COUNTROWS ( fact_stage_events )
)
```

For the funnel visual, make one more table so the stages appear as rows:
```DAX
Funnel Steps =
DATATABLE ( "Step", INTEGER, "Stage", STRING,
    { { 1, "Applied" }, { 2, "Phone Screen" }, { 3, "Skills Assessment" },
      { 4, "Onsite Interview" }, { 5, "Offer" }, { 6, "Hired" } } )

Funnel Candidates =
SWITCH (
    SELECTEDVALUE ( 'Funnel Steps'[Step] ),
    1, [Applications],
    2, [Reached Phone Screen],
    3, [Reached Assessment],
    4, [Reached Onsite],
    5, [Reached Offer],
    6, [Hires]
)
```
(`Funnel Steps` has no relationships — it only drives the visual's rows. Sort `Stage` by `Step`.)

### Speed
```DAX
Avg Time to Hire (days) =
CALCULATE ( AVERAGE ( fact_applications[time_to_hire_days] ), fact_applications[is_hired] = 1 )   -- 1 dp

Avg Time to Fill (days) =
CALCULATE ( AVERAGE ( fact_requisitions[time_to_fill_days] ), fact_requisitions[status] = "Filled" )

Avg Days in Stage = AVERAGE ( fact_stage_events[days_in_stage] )                  -- 1 dp

Avg Onsite Days (hired) =
CALCULATE ( AVERAGE ( fact_applications[days_onsite] ), fact_applications[is_hired] = 1 )

Time to Hire vs 30-day Target =
[Avg Time to Hire (days)] - 30
```

### Offers
```DAX
Offers Accepted = CALCULATE ( COUNTROWS ( fact_applications ), fact_applications[offer_status] = "Accepted" )
Offers Declined = CALCULATE ( COUNTROWS ( fact_applications ), fact_applications[offer_status] = "Declined" )

Offer Acceptance % = DIVIDE ( [Offers Accepted], [Offers Accepted] + [Offers Declined] )     -- Percentage, 1 dp

Fill Rate % =
DIVIDE (
    CALCULATE ( [Requisitions], fact_requisitions[status] = "Filled" ),
    CALCULATE ( [Requisitions], fact_requisitions[status] <> "Open" )
)
```

### Cost and quality
```DAX
Recruiting Spend = SUM ( fact_source_spend[amount] )                              -- Currency, 0 dp

Cost per Hire = DIVIDE ( [Recruiting Spend], [Hires] )                            -- Currency, 0 dp

Hires with 12m History =
CALCULATE ( [Hires], fact_applications[start_date] <= DATE ( 2024, 12, 31 ) )

Retained 12m =
CALCULATE (
    [Hires],
    fact_applications[start_date] <= DATE ( 2024, 12, 31 ),
    FILTER (
        fact_applications,
        ISBLANK ( fact_applications[exit_date] )
            || fact_applications[exit_date] - fact_applications[start_date] >= 365
    )
)

12-Month Retention % = DIVIDE ( [Retained 12m], [Hires with 12m History] )        -- Percentage, 0 dp

Avg Performance (6m) = AVERAGE ( fact_applications[performance_rating_6m] )      -- 2 dp
```

### Lost candidates
```DAX
Withdrawals = SUM ( fact_applications[withdrew_flag] )

Lost to Speed = SUM ( fact_applications[lost_to_speed_flag] )    -- withdrew/declined: "accepted another offer" or "process too long"

Withdrawal Rate % = DIVIDE ( [Withdrawals], [Applications] )
```

---

## 6. Report pages

Apply the theme first: **View → Themes → Browse for themes → `powerbi/theme/recruitment_theme.json`**.

Put the same slicers on every page (use **View → Sync slicers**): `Dim_Date[Year]`, `dim_departments[department_name]`, `Dim_Source[source]`, `fact_applications[job_level]`.

### Page 1 — Executive Overview
| Position | Visual | Fields |
|---|---|---|
| Top row | 6 **Card** visuals | `Applications`, `Hires`, `Avg Time to Hire (days)`, `Offer Acceptance %`, `Fill Rate %`, `Cost per Hire` |
| Middle left | **Funnel** | Category `Funnel Steps[Stage]`, Values `Funnel Candidates` |
| Middle right | **Line chart** | X `Dim_Date[Year-Month]`, Y `Hires by Hire Date` |
| Bottom | **Clustered bar** | Y `dim_departments[department_name]`, X `Avg Time to Hire (days)`; add a constant line at 30 (Analytics pane) labelled "Target" |

### Page 2 — Bottlenecks & Speed
| Visual | Fields |
|---|---|
| **Clustered column** | X `Dim_Stage[Stage]`, Y `Avg Days in Stage` — Onsite Interview stands out |
| **Matrix** (heatmap) | Rows `department_name`, Columns `Dim_Stage[Stage]`, Values `Avg Days in Stage`; Conditional formatting → Background colour → gradient white → blue |
| **Clustered column** | X `Dim_Stage[Stage]`, Y `Stage Withdrawal Rate %` |
| **Card** | `Lost to Speed` with subtitle "candidates lost to slow process / competing offers" |
| **Table** | `fact_requisitions` with `status = "Open"` filter: requisition, department, recruiter, `days_open` — sorted descending (aging open roles) |

### Page 3 — Source Effectiveness
| Visual | Fields |
|---|---|
| **Table** (scorecard) | `Dim_Source[source]`, `Applications`, `Hires`, `Application to Hire %`, `Cost per Hire`, `12-Month Retention %`, `Avg Performance (6m)`; data bars on `Application to Hire %` |
| **Scatter chart** | Values `Dim_Source[source]`, X `Cost per Hire`, Y `Application to Hire %`, Size `Hires` (set X axis to log scale) |
| **Stacked column** | X `Dim_Date[Year-Month]`, Y `Recruiting Spend`, Legend `Dim_Source[source]` |

### Page 4 — Offers
| Visual | Fields |
|---|---|
| **Cards** | `Offer Acceptance %`, `Offers Declined` |
| **Bar chart** | Y `fact_applications[decline_reason]` (filter: not blank), X `Offers Declined` |
| **Column chart** | X a grouping of `offer_vs_expected_pct` (right-click column → New group → bins of 0.05), Y `Offer Acceptance %` |
| **Column chart** | X bins of `days_in_process` (size 10), Y `Offer Acceptance %` |
| **Clustered bar** | Y `department_name`, X `Offer Acceptance %` |

### Page 5 — Recruiters
| Visual | Fields |
|---|---|
| **Table** | `recruiter_name`, `Requisitions`, `Applications`, `Hires`, `Avg Time to Hire (days)`, `Fill Rate %`, `Withdrawal Rate %` with conditional colouring (orange = worse) |
| **Scatter** | X `Requisitions`, Y `Avg Time to Hire (days)`, Values `recruiter_name` — shows workload vs speed |

---

## 7. Finishing touches
- **Titles that state the insight**, e.g. "Onsite interviews take 11 days — the slowest stage" rather than "Days by stage".
- Add a **text box** on page 1 with the 3 key findings and 3 recommendations from the README.
- **Tooltips:** add `Applications` and `Hires` to tooltips of every chart.
- **Drill-through:** create a page "Requisition detail" with drill-through field `fact_requisitions[requisition_id]`, showing that requisition's funnel and candidate list.
- Use **bookmarks** to make a "Before vs After" button for the what-if scenario (onsite stage 5 days faster) from the Python notebook.
- Publish to Power BI Service (optional) and add the link to your portfolio.

## 8. Expected numbers (to check your model)
With no filters applied, your cards should show: **34,673 applications · 382 hires · 33.9 days avg time to hire · 67.5% offer acceptance · 73.9% fill rate · $4,773 cost per hire.** If a number is different, check data types (Step 2) and relationships (Step 4).
