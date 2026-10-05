-- =====================================================================
-- Recruitment Funnel & Hiring Process Optimization
-- 01_schema.sql — database schema
--
-- Standard SQL: runs in SQLite and PostgreSQL as written.
-- MySQL: change TEXT to VARCHAR(255) where used as a key.
--
--   departments 1──< requisitions >──1 recruiters
--   requisitions 1──< applications >──1 candidates
--   applications 1──< stage_events
--   applications 1──0..1 offers, 1──0..1 hires
--   source_spend: monthly recruiting spend by source
-- =====================================================================

DROP TABLE IF EXISTS hires;
DROP TABLE IF EXISTS offers;
DROP TABLE IF EXISTS stage_events;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS requisitions;
DROP TABLE IF EXISTS recruiters;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS source_spend;

CREATE TABLE departments (
    department_id    VARCHAR(5) PRIMARY KEY,
    department_name  VARCHAR(40) NOT NULL,
    department_head  VARCHAR(60)
);

CREATE TABLE recruiters (
    recruiter_id     VARCHAR(5) PRIMARY KEY,
    recruiter_name   VARCHAR(60) NOT NULL,
    team             VARCHAR(20),
    start_date       DATE
);

CREATE TABLE requisitions (
    requisition_id   VARCHAR(12) PRIMARY KEY,
    department_id    VARCHAR(5) NOT NULL REFERENCES departments(department_id),
    job_title        VARCHAR(60),
    job_level        VARCHAR(10),          -- Entry / Mid / Senior / Lead
    location         VARCHAR(20),          -- New York / Austin / Chicago / Remote
    recruiter_id     VARCHAR(5) REFERENCES recruiters(recruiter_id),
    hiring_manager   VARCHAR(10),
    headcount        INTEGER,
    salary_min       INTEGER,
    salary_max       INTEGER,
    opened_date      DATE NOT NULL,
    closed_date      DATE,                 -- NULL while open
    status           VARCHAR(10)           -- Filled / Cancelled / Open
);

CREATE TABLE candidates (
    candidate_id       VARCHAR(12) PRIMARY KEY,
    gender             VARCHAR(20),
    years_experience   DECIMAL(4,1),
    highest_education  VARCHAR(20),
    current_city       VARCHAR(40),
    expected_salary    INTEGER
);

CREATE TABLE applications (
    application_id   VARCHAR(12) PRIMARY KEY,
    candidate_id     VARCHAR(12) NOT NULL REFERENCES candidates(candidate_id),
    requisition_id   VARCHAR(12) NOT NULL REFERENCES requisitions(requisition_id),
    source           VARCHAR(30),
    applied_date     DATE NOT NULL,
    current_stage    VARCHAR(20),          -- furthest stage reached (or 'Hired')
    outcome          VARCHAR(20),          -- Hired / Rejected / Withdrew / Offer Declined / In Progress
    outcome_reason   VARCHAR(60),
    outcome_date     DATE
);

CREATE TABLE stage_events (
    event_id         INTEGER PRIMARY KEY,
    application_id   VARCHAR(12) NOT NULL REFERENCES applications(application_id),
    stage            VARCHAR(20) NOT NULL, -- Resume Screen / Phone Screen / Skills Assessment / Onsite Interview / Offer
    stage_order      INTEGER,
    entered_date     DATE,
    exited_date      DATE,                 -- NULL while in progress
    result           VARCHAR(15),          -- Passed / Rejected / Withdrew / Accepted / Declined / In Progress
    reason           VARCHAR(60),
    days_in_stage    INTEGER
);

CREATE TABLE offers (
    offer_id         VARCHAR(12) PRIMARY KEY,
    application_id   VARCHAR(12) NOT NULL REFERENCES applications(application_id),
    offer_date       DATE,
    offered_salary   INTEGER,
    response_date    DATE,
    offer_status     VARCHAR(10),          -- Accepted / Declined / Pending
    decline_reason   VARCHAR(60)
);

CREATE TABLE hires (
    hire_id                VARCHAR(12) PRIMARY KEY,
    application_id         VARCHAR(12) NOT NULL REFERENCES applications(application_id),
    start_date             DATE,
    employment_status      VARCHAR(10),    -- Active / Left
    exit_date              DATE,
    performance_rating_6m  INTEGER         -- 1-5, only once tenure >= 6 months
);

CREATE TABLE source_spend (
    month       CHAR(7),                   -- YYYY-MM
    source      VARCHAR(30),
    spend_type  VARCHAR(40),
    amount      DECIMAL(12,2)
);

CREATE INDEX idx_app_req     ON applications(requisition_id);
CREATE INDEX idx_app_cand    ON applications(candidate_id);
CREATE INDEX idx_events_app  ON stage_events(application_id);
CREATE INDEX idx_events_stg  ON stage_events(stage);
CREATE INDEX idx_offers_app  ON offers(application_id);
CREATE INDEX idx_hires_app   ON hires(application_id);
