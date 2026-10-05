-- =====================================================================
-- Recruitment Funnel & Hiring Process Optimization
-- 03_analysis_queries.sql — business questions answered in SQL
--
-- Dialect: SQLite (database: data/recruitment.db). Run 01_schema.sql and
-- 02_views.sql first. PostgreSQL: replace julianday(a) - julianday(b) with
-- (a - b), and strftime('%Y-%m', d) with to_char(d, 'YYYY-MM').
-- Each query begins with a "-- Qnn:" line; scripts/03_build_database.py
-- runs them all and saves results to sql/query_results/.
-- =====================================================================


-- Q01: Headline KPIs
SELECT
    (SELECT COUNT(*) FROM requisitions)                                    AS requisitions,
    (SELECT SUM(headcount) FROM requisitions)                              AS positions,
    (SELECT COUNT(*) FROM applications)                                    AS applications,
    (SELECT COUNT(*) FROM hires)                                           AS hires,
    ROUND(100.0 * (SELECT COUNT(*) FROM hires) / (SELECT COUNT(*) FROM applications), 2) AS application_to_hire_pct,
    ROUND(1.0 * (SELECT COUNT(*) FROM applications) / (SELECT COUNT(*) FROM hires), 1)   AS applications_per_hire,
    (SELECT ROUND(AVG(time_to_hire_days), 1) FROM vw_application_funnel WHERE is_hired = 1) AS avg_time_to_hire_days,
    (SELECT ROUND(AVG(time_to_fill_days), 1) FROM vw_requisition_summary WHERE status = 'Filled') AS avg_time_to_fill_days,
    (SELECT ROUND(100.0 * SUM(offer_status = 'Accepted') / SUM(offer_status IN ('Accepted', 'Declined')), 1)
       FROM offers)                                                        AS offer_acceptance_pct,
    (SELECT ROUND(100.0 * SUM(status = 'Filled') / SUM(status <> 'Open'), 1) FROM requisitions) AS fill_rate_pct,
    (SELECT ROUND(SUM(amount), 0) FROM source_spend)                       AS total_recruiting_spend,
    (SELECT ROUND(SUM(amount) / (SELECT COUNT(*) FROM hires), 0) FROM source_spend) AS cost_per_hire;


-- Q02: The hiring funnel — how many candidates reach each stage?
WITH stages AS (
    SELECT 1 AS step, 'Applied / Resume Screen' AS stage, COUNT(*) AS candidates FROM vw_application_funnel
    UNION ALL SELECT 2, 'Phone Screen',      SUM(reached_phone_screen) FROM vw_application_funnel
    UNION ALL SELECT 3, 'Skills Assessment', SUM(reached_assessment)   FROM vw_application_funnel
    UNION ALL SELECT 4, 'Onsite Interview',  SUM(reached_onsite)       FROM vw_application_funnel
    UNION ALL SELECT 5, 'Offer',             SUM(reached_offer)        FROM vw_application_funnel
    UNION ALL SELECT 6, 'Hired',             SUM(is_hired)             FROM vw_application_funnel
)
SELECT
    step, stage, candidates,
    ROUND(100.0 * candidates / LAG(candidates) OVER (ORDER BY step), 1) AS conversion_from_previous_pct,
    ROUND(100.0 * candidates / FIRST_VALUE(candidates) OVER (ORDER BY step), 2) AS conversion_from_applied_pct
FROM stages
ORDER BY step;


-- Q03: What happens at each stage? (pass / reject / withdraw)
SELECT
    stage_order, stage,
    COUNT(*)                                                       AS entered,
    SUM(result IN ('Passed', 'Accepted'))                          AS passed_or_accepted,
    SUM(result = 'Rejected')                                       AS rejected,
    SUM(result = 'Withdrew')                                       AS withdrew,
    SUM(result = 'Declined')                                       AS declined_offer,
    ROUND(100.0 * SUM(result IN ('Passed', 'Accepted')) / COUNT(*), 1) AS pass_rate_pct,
    ROUND(100.0 * SUM(result = 'Withdrew') / COUNT(*), 1)          AS withdrawal_rate_pct
FROM stage_events
GROUP BY stage_order, stage
ORDER BY stage_order;


-- Q04: BOTTLENECK — average days spent in each stage
SELECT
    stage,
    COUNT(*)                          AS completed_stages,
    ROUND(AVG(days_in_stage), 1)      AS avg_days,
    MAX(days_in_stage)                AS max_days,
    ROUND(100.0 * AVG(days_in_stage) /
          (SELECT SUM(avg_d) FROM (SELECT AVG(days_in_stage) AS avg_d FROM stage_events
                                   WHERE days_in_stage IS NOT NULL GROUP BY stage)), 1) AS share_of_total_pct
FROM stage_events
WHERE days_in_stage IS NOT NULL
GROUP BY stage, stage_order
ORDER BY stage_order;


-- Q05: BOTTLENECK by department — average days per stage (hired candidates only)
SELECT
    department_name,
    COUNT(*)                                AS hires,
    ROUND(AVG(days_resume_screen), 1)       AS resume_screen,
    ROUND(AVG(days_phone_screen), 1)        AS phone_screen,
    ROUND(AVG(days_assessment), 1)          AS assessment,
    ROUND(AVG(days_onsite), 1)              AS onsite_interview,
    ROUND(AVG(days_offer), 1)               AS offer,
    ROUND(AVG(time_to_hire_days), 1)        AS avg_time_to_hire
FROM vw_application_funnel
WHERE is_hired = 1
GROUP BY department_name
ORDER BY avg_time_to_hire DESC;


-- Q06: Does waiting cause drop-off? Withdrawal rate at the interview stages,
--      by how many days the candidate had already been in the process when
--      the stage began (measured at entry, so it is known before the outcome)
WITH s AS (
    SELECT
        e.result,
        julianday(e.entered_date) - julianday(a.applied_date) AS days_already_waiting
    FROM stage_events e
    JOIN applications a ON a.application_id = e.application_id
    WHERE e.stage IN ('Phone Screen', 'Skills Assessment', 'Onsite Interview')
)
SELECT
    CASE
        WHEN days_already_waiting < 7  THEN '1. 0-6 days'
        WHEN days_already_waiting < 14 THEN '2. 7-13 days'
        WHEN days_already_waiting < 21 THEN '3. 14-20 days'
        ELSE                                '4. 21+ days'
    END                                                   AS days_in_process_band,
    COUNT(*)                                              AS stage_records,
    SUM(result = 'Withdrew')                              AS withdrew,
    ROUND(100.0 * SUM(result = 'Withdrew') / COUNT(*), 1) AS withdrawal_rate_pct
FROM s
GROUP BY days_in_process_band
ORDER BY days_in_process_band;


-- Q07: Why do candidates withdraw?
SELECT
    outcome_reason                                         AS withdrawal_reason,
    COUNT(*)                                               AS candidates,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS share_pct,
    ROUND(AVG(days_in_process), 1)                         AS avg_days_in_process
FROM vw_application_funnel
WHERE outcome = 'Withdrew'
GROUP BY outcome_reason
ORDER BY candidates DESC;


-- Q08: SOURCE effectiveness — volume, conversion and speed
SELECT
    source,
    COUNT(*)                                               AS applications,
    ROUND(100.0 * SUM(reached_phone_screen) / COUNT(*), 1) AS resume_pass_pct,
    SUM(reached_onsite)                                    AS reached_onsite,
    SUM(is_hired)                                          AS hires,
    ROUND(100.0 * SUM(is_hired) / COUNT(*), 2)             AS application_to_hire_pct,
    ROUND(1.0 * COUNT(*) / NULLIF(SUM(is_hired), 0), 0)    AS applications_per_hire,
    ROUND(AVG(time_to_hire_days), 1)                       AS avg_time_to_hire,
    ROUND(100.0 * SUM(offer_status = 'Accepted')
          / NULLIF(SUM(offer_status IN ('Accepted', 'Declined')), 0), 1) AS offer_acceptance_pct
FROM vw_application_funnel
GROUP BY source
ORDER BY application_to_hire_pct DESC;


-- Q09: SOURCE cost — spend, cost per hire, cost per application
WITH spend AS (SELECT source, SUM(amount) AS spend FROM source_spend GROUP BY source),
     vol   AS (SELECT source, COUNT(*) AS applications, SUM(is_hired) AS hires
               FROM vw_application_funnel GROUP BY source)
SELECT
    v.source, v.applications, v.hires,
    ROUND(s.spend, 0)                               AS total_spend,
    ROUND(s.spend / NULLIF(v.hires, 0), 0)          AS cost_per_hire,
    ROUND(s.spend / v.applications, 2)              AS cost_per_application
FROM vol v
LEFT JOIN spend s ON s.source = v.source
ORDER BY cost_per_hire;


-- Q10: SOURCE quality — 12-month retention and 6-month performance
--      (retention only for hires who started on or before 2024-12-31,
--       so everyone has had a full 12 months)
SELECT
    source,
    COUNT(hire_id)                                                   AS hires,
    SUM(start_date <= '2024-12-31')                                  AS hires_with_12m_history,
    ROUND(100.0 * SUM(start_date <= '2024-12-31'
                      AND (exit_date IS NULL OR julianday(exit_date) - julianday(start_date) >= 365))
          / NULLIF(SUM(start_date <= '2024-12-31'), 0), 1)           AS retained_12m_pct,
    ROUND(AVG(performance_rating_6m), 2)                             AS avg_performance_6m
FROM vw_application_funnel
WHERE is_hired = 1
GROUP BY source
HAVING COUNT(hire_id) >= 10          -- too few hires to judge the others
ORDER BY retained_12m_pct DESC;


-- Q11: OFFERS — acceptance rate by department
SELECT
    department_name,
    SUM(offer_status IN ('Accepted', 'Declined'))                    AS offers_decided,
    SUM(offer_status = 'Accepted')                                   AS accepted,
    ROUND(100.0 * SUM(offer_status = 'Accepted')
          / SUM(offer_status IN ('Accepted', 'Declined')), 1)        AS acceptance_pct,
    ROUND(AVG(offered_salary), 0)                                    AS avg_offer
FROM vw_application_funnel
WHERE reached_offer = 1
GROUP BY department_name
ORDER BY acceptance_pct;


-- Q12: OFFERS — why are offers declined?
SELECT
    decline_reason,
    COUNT(*)                                            AS offers_declined,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS share_pct
FROM offers
WHERE offer_status = 'Declined'
GROUP BY decline_reason
ORDER BY offers_declined DESC;


-- Q13: OFFERS — acceptance by salary gap and by total process length
SELECT 'Salary vs expectation' AS factor,
    CASE
        WHEN offer_vs_expected_pct < -0.10 THEN '1. >10% below expected'
        WHEN offer_vs_expected_pct < -0.05 THEN '2. 5-10% below'
        WHEN offer_vs_expected_pct < 0     THEN '3. 0-5% below'
        ELSE                                    '4. At or above expected'
    END AS band,
    COUNT(*) AS offers,
    ROUND(100.0 * SUM(offer_status = 'Accepted') / COUNT(*), 1) AS acceptance_pct
FROM vw_application_funnel
WHERE offer_status IN ('Accepted', 'Declined')
GROUP BY band
UNION ALL
SELECT 'Days from application to decision',
    CASE
        WHEN days_in_process < 30 THEN '1. < 30 days'
        WHEN days_in_process < 40 THEN '2. 30-39 days'
        WHEN days_in_process < 50 THEN '3. 40-49 days'
        ELSE                           '4. 50+ days'
    END,
    COUNT(*),
    ROUND(100.0 * SUM(offer_status = 'Accepted') / COUNT(*), 1)
FROM vw_application_funnel
WHERE offer_status IN ('Accepted', 'Declined')
GROUP BY 2
ORDER BY 1, 2;


-- Q14: RECRUITER scorecard
SELECT
    f.recruiter_name,
    COUNT(DISTINCT f.requisition_id)                         AS requisitions,
    COUNT(*)                                                 AS applications,
    ROUND(AVG(f.days_resume_screen), 1)                      AS avg_resume_screen_days,
    ROUND(AVG(f.days_phone_screen), 1)                       AS avg_phone_screen_days,
    SUM(f.is_hired)                                          AS hires,
    ROUND(AVG(f.time_to_hire_days), 1)                       AS avg_time_to_hire,
    ROUND(100.0 * SUM(f.outcome = 'Withdrew') / COUNT(*), 2) AS withdrawal_pct,
    (SELECT ROUND(100.0 * SUM(r.status = 'Filled') / SUM(r.status <> 'Open'), 1)
       FROM vw_requisition_summary r WHERE r.recruiter_name = f.recruiter_name) AS fill_rate_pct
FROM vw_application_funnel f
GROUP BY f.recruiter_name
ORDER BY requisitions DESC;


-- Q15: REQUISITIONS — status, fill rate and time-to-fill by department
SELECT
    department_name,
    COUNT(*)                                                       AS requisitions,
    SUM(status = 'Filled')                                         AS filled,
    SUM(status = 'Cancelled')                                      AS cancelled_unfilled,
    SUM(status = 'Open')                                           AS still_open,
    ROUND(100.0 * SUM(status = 'Filled') / SUM(status <> 'Open'), 1) AS fill_rate_pct,
    ROUND(AVG(time_to_fill_days), 1)                               AS avg_time_to_fill,
    ROUND(AVG(applications), 0)                                    AS avg_applications_per_req
FROM vw_requisition_summary
GROUP BY department_name
ORDER BY fill_rate_pct;


-- Q16: TREND — monthly applications, hires and time-to-hire
SELECT
    m.month,
    m.applications,
    COALESCE(h.hires, 0)       AS hires,
    h.avg_time_to_hire
FROM (SELECT applied_month AS month, COUNT(*) AS applications
      FROM vw_application_funnel GROUP BY applied_month) m
LEFT JOIN (SELECT strftime('%Y-%m', outcome_date) AS month, COUNT(*) AS hires,
                  ROUND(AVG(time_to_hire_days), 1) AS avg_time_to_hire
           FROM vw_application_funnel WHERE is_hired = 1 GROUP BY 1) h ON h.month = m.month
ORDER BY m.month;


-- Q17: LOCATION / work mode — remote roles attract more applicants
SELECT
    location,
    COUNT(*)                                    AS requisitions,
    ROUND(AVG(applications), 0)                 AS avg_applications_per_req,
    ROUND(AVG(time_to_fill_days), 1)            AS avg_time_to_fill,
    ROUND(100.0 * SUM(status = 'Filled') / SUM(status <> 'Open'), 1) AS fill_rate_pct
FROM vw_requisition_summary
GROUP BY location
ORDER BY avg_applications_per_req DESC;


-- Q18: JOB LEVEL — seniority vs speed and difficulty
SELECT
    job_level,
    COUNT(*)                                    AS requisitions,
    ROUND(AVG(applications), 0)                 AS avg_applications_per_req,
    ROUND(AVG(time_to_fill_days), 1)            AS avg_time_to_fill,
    ROUND(100.0 * SUM(status = 'Filled') / SUM(status <> 'Open'), 1) AS fill_rate_pct
FROM vw_requisition_summary
GROUP BY job_level
ORDER BY CASE job_level WHEN 'Entry' THEN 1 WHEN 'Mid' THEN 2 WHEN 'Senior' THEN 3 ELSE 4 END;


-- Q19: FAIRNESS — stage pass-through rates by gender
SELECT
    gender,
    COUNT(*)                                                                 AS applications,
    ROUND(100.0 * SUM(reached_phone_screen) / COUNT(*), 1)                   AS resume_pass_pct,
    ROUND(100.0 * SUM(reached_onsite) / NULLIF(SUM(reached_phone_screen), 0), 1) AS phone_to_onsite_pct,
    ROUND(100.0 * SUM(reached_offer) / NULLIF(SUM(reached_onsite), 0), 1)    AS onsite_to_offer_pct,
    ROUND(100.0 * SUM(is_hired) / COUNT(*), 2)                               AS application_to_hire_pct
FROM vw_application_funnel
GROUP BY gender
ORDER BY applications DESC;


-- Q20: Lost good candidates — people who passed onsite or got an offer but did not join
SELECT
    department_name,
    SUM(reached_offer = 1 AND outcome = 'Offer Declined')                  AS declined_offers,
    SUM(reached_onsite = 1 AND outcome = 'Withdrew')                       AS withdrew_at_onsite_or_later,
    SUM(outcome_reason IN ('Accepted another offer', 'Process took too long')) AS lost_to_speed,
    SUM(is_hired)                                                          AS hires
FROM vw_application_funnel
GROUP BY department_name
ORDER BY lost_to_speed DESC;
