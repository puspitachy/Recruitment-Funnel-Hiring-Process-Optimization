-- =====================================================================
-- 02_views.sql — reporting views used by the analysis queries, Python,
-- Excel and Power BI. Dates are compared with julianday() (SQLite);
-- in PostgreSQL use (date_a - date_b) instead.
-- =====================================================================

-- One row per application, with funnel flags and stage durations
DROP VIEW IF EXISTS vw_application_funnel;
CREATE VIEW vw_application_funnel AS
WITH stage_pivot AS (
    SELECT
        application_id,
        MAX(CASE WHEN stage = 'Phone Screen'      THEN 1 ELSE 0 END) AS reached_phone_screen,
        MAX(CASE WHEN stage = 'Skills Assessment' THEN 1 ELSE 0 END) AS reached_assessment,
        MAX(CASE WHEN stage = 'Onsite Interview'  THEN 1 ELSE 0 END) AS reached_onsite,
        MAX(CASE WHEN stage = 'Offer'             THEN 1 ELSE 0 END) AS reached_offer,
        SUM(CASE WHEN stage = 'Resume Screen'     THEN days_in_stage END) AS days_resume_screen,
        SUM(CASE WHEN stage = 'Phone Screen'      THEN days_in_stage END) AS days_phone_screen,
        SUM(CASE WHEN stage = 'Skills Assessment' THEN days_in_stage END) AS days_assessment,
        SUM(CASE WHEN stage = 'Onsite Interview'  THEN days_in_stage END) AS days_onsite,
        SUM(CASE WHEN stage = 'Offer'             THEN days_in_stage END) AS days_offer
    FROM stage_events
    GROUP BY application_id
)
SELECT
    a.application_id, a.candidate_id, a.requisition_id, a.source, a.applied_date,
    strftime('%Y-%m', a.applied_date)                     AS applied_month,
    a.current_stage, a.outcome, a.outcome_reason, a.outcome_date,
    r.job_title, r.job_level, r.location, r.status        AS requisition_status,
    d.department_name, rc.recruiter_id, rc.recruiter_name,
    c.gender, c.years_experience, c.highest_education, c.expected_salary,
    1                                                      AS reached_resume_screen,
    sp.reached_phone_screen, sp.reached_assessment, sp.reached_onsite, sp.reached_offer,
    CASE WHEN a.outcome = 'Hired' THEN 1 ELSE 0 END        AS is_hired,
    sp.days_resume_screen, sp.days_phone_screen, sp.days_assessment, sp.days_onsite, sp.days_offer,
    CASE WHEN a.outcome = 'Hired'
         THEN CAST(julianday(a.outcome_date) - julianday(a.applied_date) AS INTEGER) END AS time_to_hire_days,
    CAST(julianday(COALESCE(a.outcome_date, '2025-12-31')) - julianday(a.applied_date) AS INTEGER) AS days_in_process,
    o.offered_salary, o.offer_status, o.decline_reason,
    CASE WHEN o.offered_salary IS NOT NULL
         THEN ROUND(1.0 * (o.offered_salary - c.expected_salary) / c.expected_salary, 4) END AS offer_vs_expected_pct,
    h.hire_id, h.start_date, h.employment_status, h.exit_date, h.performance_rating_6m
FROM applications a
JOIN requisitions r  ON r.requisition_id = a.requisition_id
JOIN departments d   ON d.department_id  = r.department_id
JOIN recruiters rc   ON rc.recruiter_id  = r.recruiter_id
JOIN candidates c    ON c.candidate_id   = a.candidate_id
LEFT JOIN stage_pivot sp ON sp.application_id = a.application_id
LEFT JOIN offers o   ON o.application_id = a.application_id
LEFT JOIN hires h    ON h.application_id = a.application_id;


-- One row per requisition, with volume, hires and time-to-fill
DROP VIEW IF EXISTS vw_requisition_summary;
CREATE VIEW vw_requisition_summary AS
SELECT
    r.requisition_id, d.department_name, r.job_title, r.job_level, r.location,
    rc.recruiter_name, r.headcount, r.opened_date, r.closed_date, r.status,
    strftime('%Y-%m', r.opened_date)                       AS opened_month,
    COUNT(a.application_id)                                AS applications,
    SUM(CASE WHEN a.outcome = 'Hired' THEN 1 ELSE 0 END)   AS hires,
    CASE WHEN r.status = 'Filled'
         THEN CAST(julianday(r.closed_date) - julianday(r.opened_date) AS INTEGER) END AS time_to_fill_days,
    CAST(julianday(COALESCE(r.closed_date, '2025-12-31')) - julianday(r.opened_date) AS INTEGER) AS days_open
FROM requisitions r
JOIN departments d  ON d.department_id = r.department_id
JOIN recruiters rc  ON rc.recruiter_id = r.recruiter_id
LEFT JOIN applications a ON a.requisition_id = r.requisition_id
GROUP BY r.requisition_id;
