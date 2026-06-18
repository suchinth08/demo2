-- ============================================================
-- PHARMA COMPLIANCE BI - COMPLETE DATABASE SCHEMA
-- Governed by: FDA 21 CFR 210/211, 21 CFR Part 11, ICH Q9/Q10
-- ============================================================

-- ─────────────────────────────────────────
-- REFERENCE / MASTER TABLES
-- ─────────────────────────────────────────

CREATE TABLE sites (
    site_id         VARCHAR(10) PRIMARY KEY,
    site_name       VARCHAR(100) NOT NULL,
    country         VARCHAR(50),
    site_type       VARCHAR(30),          -- Manufacturing | R&D | QC Lab | Distribution
    gxp_scope       VARCHAR(100),         -- GMP | GMP+GLP | GCP
    fda_estab_id    VARCHAR(20),
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE departments (
    dept_id         SERIAL PRIMARY KEY,
    dept_name       VARCHAR(100) NOT NULL,
    dept_code       VARCHAR(20) UNIQUE,
    site_id         VARCHAR(10) REFERENCES sites(site_id),
    parent_dept_id  INT REFERENCES departments(dept_id),
    dept_head_id    INT                   -- FK added after employees table
);

CREATE TABLE job_roles (
    role_id         SERIAL PRIMARY KEY,
    role_name       VARCHAR(100),
    gmp_role        VARCHAR(20),          -- GMP | Non-GMP | GCP | GLP
    department_id   INT REFERENCES departments(dept_id)
);

CREATE TABLE employees (
    employee_id     SERIAL PRIMARY KEY,
    employee_number VARCHAR(20) UNIQUE,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    department_id   INT REFERENCES departments(dept_id),
    site_id         VARCHAR(10) REFERENCES sites(site_id),
    job_title       VARCHAR(100),
    role_id         INT REFERENCES job_roles(role_id),
    manager_id      INT REFERENCES employees(employee_id),
    hire_date       DATE,
    gmp_role        VARCHAR(20),
    is_active       BOOLEAN DEFAULT TRUE,
    employment_type VARCHAR(20)           -- Full-Time | Contractor | Part-Time
);

-- Backfill FK after employees created
ALTER TABLE departments ADD CONSTRAINT fk_dept_head
    FOREIGN KEY (dept_head_id) REFERENCES employees(employee_id);

CREATE TABLE products (
    product_id          SERIAL PRIMARY KEY,
    product_code        VARCHAR(30) UNIQUE,
    product_name        VARCHAR(200),
    product_type        VARCHAR(30),      -- Drug Substance | Drug Product | Biologic
    dosage_form         VARCHAR(30),      -- Tablet | Capsule | Injectable | Topical
    therapeutic_area    VARCHAR(50),
    nda_anda_number     VARCHAR(20),
    regulatory_status   VARCHAR(30),      -- Approved | Investigational | Discontinued
    is_gmp              BOOLEAN DEFAULT TRUE,
    is_serialized       BOOLEAN DEFAULT FALSE
);

CREATE TABLE materials (
    material_id     SERIAL PRIMARY KEY,
    material_code   VARCHAR(30) UNIQUE,
    material_name   VARCHAR(200),
    material_type   VARCHAR(30),          -- API | Excipient | Packaging | Solvent
    pharmacopeia    VARCHAR(30),          -- USP | EP | JP | In-House
    is_critical     BOOLEAN DEFAULT FALSE
);

CREATE TABLE equipment (
    equipment_id        VARCHAR(20) PRIMARY KEY,
    equipment_name      VARCHAR(100),
    equipment_type      VARCHAR(50),      -- Reactor | HPLC | Autoclave | Tablet Press
    site_id             VARCHAR(10) REFERENCES sites(site_id),
    manufacturing_area  VARCHAR(50),
    qualification_status VARCHAR(20),     -- Qualified | Overdue | Pending
    last_qual_date      DATE,
    next_qual_date      DATE
);

-- ─────────────────────────────────────────
-- DOCUMENT CONTROL  (21 CFR 211.100 / Part 11)
-- ─────────────────────────────────────────

CREATE TABLE documents (
    doc_id              VARCHAR(20) PRIMARY KEY,
    doc_number          VARCHAR(30) UNIQUE,
    doc_title           VARCHAR(200),
    doc_type            VARCHAR(30),      -- SOP | Work Instruction | Policy | Form | Spec | Protocol
    business_function   VARCHAR(50),
    gxp_classification  VARCHAR(10),      -- GMP | GCP | GLP | GDP | Non-GxP
    current_version     VARCHAR(10),
    status              VARCHAR(20),      -- Draft | Under Review | Approved | Effective | Obsolete
    effective_date      DATE,
    next_review_date    DATE,
    last_review_date    DATE,
    review_freq_months  INT DEFAULT 24,
    owner_dept_id       INT REFERENCES departments(dept_id),
    doc_owner_id        INT REFERENCES employees(employee_id),
    regulatory_ref      VARCHAR(200),
    is_controlled       BOOLEAN DEFAULT TRUE,
    site_id             VARCHAR(10) REFERENCES sites(site_id),
    training_required   BOOLEAN DEFAULT TRUE
);

CREATE TABLE document_versions (
    version_id          SERIAL PRIMARY KEY,
    doc_id              VARCHAR(20) REFERENCES documents(doc_id),
    version_number      VARCHAR(10),
    change_summary      TEXT,
    revision_date       DATE,
    approved_by         INT REFERENCES employees(employee_id),
    retired_date        DATE,
    change_request_id   VARCHAR(20)       -- FK added after change_requests
);

-- ─────────────────────────────────────────
-- CAPA  (21 CFR 820.100 / ICH Q10)
-- ─────────────────────────────────────────

CREATE TABLE capa_records (
    capa_id                     VARCHAR(20) PRIMARY KEY,
    site_id                     VARCHAR(10) REFERENCES sites(site_id),
    department_id               INT REFERENCES departments(dept_id),
    source_type                 VARCHAR(30),  -- Audit | Deviation | Complaint | Inspection | Self-Identified
    source_reference_id         VARCHAR(20),
    severity                    VARCHAR(10),  -- Critical | Major | Minor
    root_cause_category         VARCHAR(50),  -- Training | Procedure | Equipment | System | Material | Human Error
    root_cause_detail           TEXT,
    description                 TEXT,
    initiated_by                VARCHAR(100),
    owner_employee_id           INT REFERENCES employees(employee_id),
    initiation_date             DATE,
    target_close_date           DATE,
    actual_close_date           DATE,
    status                      VARCHAR(20),  -- Open | In Progress | Pending Effectiveness | Closed | Overdue
    effectiveness_check_req     BOOLEAN DEFAULT FALSE,
    effectiveness_check_date    DATE,
    effectiveness_check_result  VARCHAR(10),  -- Pass | Fail | Pending
    reopen_count                INT DEFAULT 0,
    regulatory_notif_required   BOOLEAN DEFAULT FALSE
);

CREATE TABLE capa_action_items (
    action_id           SERIAL PRIMARY KEY,
    capa_id             VARCHAR(20) REFERENCES capa_records(capa_id),
    action_description  TEXT,
    action_type         VARCHAR(20),      -- Corrective | Preventive
    assigned_to         INT REFERENCES employees(employee_id),
    due_date            DATE,
    completion_date     DATE,
    status              VARCHAR(20),
    evidence_doc_id     VARCHAR(20) REFERENCES documents(doc_id)
);

-- ─────────────────────────────────────────
-- DEVIATION MANAGEMENT
-- ─────────────────────────────────────────

CREATE TABLE batch_records (
    batch_id            VARCHAR(30) PRIMARY KEY,
    product_id          INT REFERENCES products(product_id),
    batch_number        VARCHAR(30),
    manufacturing_date  DATE,
    release_date        DATE,
    expiry_date         DATE,
    batch_size          DECIMAL(12,3),
    batch_size_unit     VARCHAR(10),
    site_id             VARCHAR(10) REFERENCES sites(site_id),
    manufacturing_line  VARCHAR(30),
    batch_status        VARCHAR(20),      -- Released | Rejected | On Hold | In Process
    disposition_date    DATE
);

CREATE TABLE deviation_records (
    deviation_id            VARCHAR(20) PRIMARY KEY,
    site_id                 VARCHAR(10) REFERENCES sites(site_id),
    department_id           INT REFERENCES departments(dept_id),
    batch_id                VARCHAR(30) REFERENCES batch_records(batch_id),
    product_id              INT REFERENCES products(product_id),
    deviation_category      VARCHAR(30),  -- Equipment | Process | Personnel | Material | Environmental | Analytical
    deviation_type          VARCHAR(20),  -- Planned | Unplanned
    severity                VARCHAR(10),  -- Critical | Major | Minor
    description             TEXT,
    detected_by             INT REFERENCES employees(employee_id),
    detection_date          DATE,
    manufacturing_area      VARCHAR(50),
    equipment_id            VARCHAR(20) REFERENCES equipment(equipment_id),
    shift                   VARCHAR(10),  -- Day | Evening | Night
    gmp_classification      VARCHAR(10),  -- GMP | Non-GMP
    investigation_required  BOOLEAN DEFAULT TRUE,
    investigation_close_dt  DATE,
    root_cause_category     VARCHAR(50),
    root_cause_description  TEXT,
    capa_id                 VARCHAR(20) REFERENCES capa_records(capa_id),
    batch_disposition_impact VARCHAR(20), -- None | Hold | Reject | Conditional Release
    status                  VARCHAR(20)
);

-- ─────────────────────────────────────────
-- AUDIT MANAGEMENT
-- ─────────────────────────────────────────

CREATE TABLE suppliers (
    supplier_id             SERIAL PRIMARY KEY,
    supplier_code           VARCHAR(20) UNIQUE,
    supplier_name           VARCHAR(200),
    supplier_type           VARCHAR(30),  -- API | Excipient | Packaging | CRO | CMO | Service
    qualification_status    VARCHAR(20),  -- Approved | Conditional | Suspended | Disqualified | Pending
    qualification_date      DATE,
    requalification_due_dt  DATE,
    country                 VARCHAR(50),
    regulatory_approvals    VARCHAR(200),
    risk_rating             VARCHAR(10),  -- High | Medium | Low
    is_gmp_critical         BOOLEAN DEFAULT FALSE
);

CREATE TABLE audits (
    audit_id            VARCHAR(20) PRIMARY KEY,
    audit_type          VARCHAR(20),      -- Internal | External-Regulatory | Supplier | System
    auditing_body       VARCHAR(50),      -- FDA | EMA | ISO | Internal QA | Client
    site_id             VARCHAR(10) REFERENCES sites(site_id),
    supplier_id         INT REFERENCES suppliers(supplier_id),
    audit_scope         TEXT,
    regulatory_framework VARCHAR(50),     -- 21 CFR 211 | ICH Q10 | ISO 9001 | EU GMP
    lead_auditor        VARCHAR(100),
    audit_start_date    DATE,
    audit_end_date      DATE,
    audit_days          DECIMAL(4,1),
    overall_rating      VARCHAR(20),      -- Satisfactory | Acceptable | Unsatisfactory
    total_findings      INT DEFAULT 0,
    critical_findings   INT DEFAULT 0,
    major_findings      INT DEFAULT 0,
    minor_findings      INT DEFAULT 0,
    observations        INT DEFAULT 0,
    status              VARCHAR(20),      -- Planned | In Progress | Closed | Response Pending
    report_issue_date   DATE,
    response_due_date   DATE
);

CREATE TABLE audit_findings (
    finding_id          VARCHAR(20) PRIMARY KEY,
    audit_id            VARCHAR(20) REFERENCES audits(audit_id),
    finding_number      INT,
    classification      VARCHAR(15),      -- Critical | Major | Minor | Observation
    regulatory_ref      VARCHAR(50),      -- 21 CFR 211.68 | EU GMP Chapter 4
    process_area        VARCHAR(50),
    finding_description TEXT,
    root_cause          TEXT,
    is_repeat_finding   BOOLEAN DEFAULT FALSE,
    prior_finding_id    VARCHAR(20) REFERENCES audit_findings(finding_id),
    capa_id             VARCHAR(20) REFERENCES capa_records(capa_id),
    response_date       DATE,
    response_status     VARCHAR(20),      -- Open | Submitted | Accepted | Rejected
    close_date          DATE
);

-- ─────────────────────────────────────────
-- TRAINING COMPLIANCE  (21 CFR 211.68)
-- ─────────────────────────────────────────

CREATE TABLE training_curricula (
    curriculum_id       SERIAL PRIMARY KEY,
    curriculum_name     VARCHAR(100),
    role_id             INT REFERENCES job_roles(role_id),
    is_gmp_required     BOOLEAN DEFAULT TRUE,
    review_freq_months  INT DEFAULT 12,
    is_active           BOOLEAN DEFAULT TRUE
);

CREATE TABLE training_records (
    training_record_id  SERIAL PRIMARY KEY,
    employee_id         INT REFERENCES employees(employee_id),
    doc_id              VARCHAR(20) REFERENCES documents(doc_id),
    curriculum_id       INT REFERENCES training_curricula(curriculum_id),
    training_type       VARCHAR(30),      -- Initial | Refresher | Remedial | Change-Driven
    delivery_method     VARCHAR(20),      -- eLearning | Classroom | OJT | Read-and-Understand
    assigned_date       DATE,
    due_date            DATE,
    completion_date     DATE,
    assessment_score    DECIMAL(5,2),
    assessment_passed   BOOLEAN,
    attempt_number      INT DEFAULT 1,
    trainer_id          INT REFERENCES employees(employee_id),
    status              VARCHAR(20),      -- Assigned | In Progress | Completed | Overdue | Waived
    waiver_reason       TEXT
);

-- ─────────────────────────────────────────
-- CHANGE CONTROL  (ICH Q10 3.2.3)
-- ─────────────────────────────────────────

CREATE TABLE change_requests (
    change_id                   VARCHAR(20) PRIMARY KEY,
    change_title                VARCHAR(200),
    change_category             VARCHAR(30),  -- Process | Equipment | Material | Facility | Software | Labeling
    change_type                 VARCHAR(20),  -- Minor | Major | Critical | Emergency
    site_id                     VARCHAR(10) REFERENCES sites(site_id),
    initiating_dept_id          INT REFERENCES departments(dept_id),
    requestor_id                INT REFERENCES employees(employee_id),
    description                 TEXT,
    business_justification      TEXT,
    product_impact              BOOLEAN DEFAULT FALSE,
    regulatory_impact           BOOLEAN DEFAULT FALSE,
    regulatory_filing_required  VARCHAR(20),  -- CBE-30 | CBE-0 | PAS | None | TBD
    safety_impact               BOOLEAN DEFAULT FALSE,
    initiation_date             DATE,
    impact_assess_due_date      DATE,
    impact_assess_complete_dt   DATE,
    approval_date               DATE,
    implementation_date         DATE,
    close_date                  DATE,
    status                      VARCHAR(30),
    approved_by                 INT REFERENCES employees(employee_id),
    linked_capa_id              VARCHAR(20) REFERENCES capa_records(capa_id),
    linked_deviation_id         VARCHAR(20) REFERENCES deviation_records(deviation_id)
);

ALTER TABLE document_versions ADD CONSTRAINT fk_dv_chg
    FOREIGN KEY (change_request_id) REFERENCES change_requests(change_id);

-- ─────────────────────────────────────────
-- SUPPLIER QUALITY
-- ─────────────────────────────────────────

CREATE TABLE supplier_incoming_inspections (
    inspection_id       SERIAL PRIMARY KEY,
    supplier_id         INT REFERENCES suppliers(supplier_id),
    material_id         INT REFERENCES materials(material_id),
    po_number           VARCHAR(30),
    lot_number          VARCHAR(30),
    receipt_date        DATE,
    inspection_date     DATE,
    qty_received        DECIMAL(12,3),
    qty_unit            VARCHAR(10),
    inspection_result   VARCHAR(20),      -- Pass | Fail | Conditional Release | Pending
    rejection_reason    VARCHAR(100),
    coa_compliant       BOOLEAN,
    inspector_id        INT REFERENCES employees(employee_id),
    capa_triggered      VARCHAR(20) REFERENCES capa_records(capa_id)
);

-- ─────────────────────────────────────────
-- RISK MANAGEMENT  (ICH Q9)
-- ─────────────────────────────────────────

CREATE TABLE risk_register (
    risk_id                 VARCHAR(20) PRIMARY KEY,
    risk_title              VARCHAR(200),
    risk_description        TEXT,
    risk_category           VARCHAR(30),  -- Process | Product Quality | Regulatory | Patient Safety | Supply Chain | IT
    business_process        VARCHAR(100),
    product_id              INT REFERENCES products(product_id),
    site_id                 VARCHAR(10) REFERENCES sites(site_id),
    risk_owner_id           INT REFERENCES employees(employee_id),
    initial_severity        INT CHECK (initial_severity BETWEEN 1 AND 10),
    initial_occurrence      INT CHECK (initial_occurrence BETWEEN 1 AND 10),
    initial_detectability   INT CHECK (initial_detectability BETWEEN 1 AND 10),
    initial_rpn             INT,          -- S × O × D
    risk_controls           TEXT,
    residual_severity       INT CHECK (residual_severity BETWEEN 1 AND 10),
    residual_occurrence     INT CHECK (residual_occurrence BETWEEN 1 AND 10),
    residual_detectability  INT CHECK (residual_detectability BETWEEN 1 AND 10),
    residual_rpn            INT,
    risk_acceptance_status  VARCHAR(20),  -- Acceptable | Unacceptable | ALARP
    last_review_date        DATE,
    next_review_date        DATE,
    status                  VARCHAR(20),  -- Active | Closed | Transferred
    icq9_tool_used          VARCHAR(20),  -- FMEA | HACCP | FTA | PHA | HAZOP
    linked_capa_id          VARCHAR(20) REFERENCES capa_records(capa_id)
);

-- ─────────────────────────────────────────
-- REGULATORY INSPECTIONS
-- ─────────────────────────────────────────

CREATE TABLE regulatory_inspections (
    inspection_id               VARCHAR(20) PRIMARY KEY,
    site_id                     VARCHAR(10) REFERENCES sites(site_id),
    inspecting_authority        VARCHAR(30),  -- FDA | EMA | PMDA | MHRA | Health Canada | WHO
    inspection_type             VARCHAR(30),  -- Pre-Approval | Routine | For Cause | Follow-Up
    inspection_start_date       DATE,
    inspection_end_date         DATE,
    lead_investigator           VARCHAR(100),
    form_483_issued             BOOLEAN DEFAULT FALSE,
    form_483_observation_count  INT DEFAULT 0,
    warning_letter_issued       BOOLEAN DEFAULT FALSE,
    import_alert_issued         BOOLEAN DEFAULT FALSE,
    overall_outcome             VARCHAR(30),  -- NAI | VAI | OAI
    response_due_date           DATE
);

CREATE TABLE regulatory_commitments (
    commitment_id           VARCHAR(20) PRIMARY KEY,
    inspection_id           VARCHAR(20) REFERENCES regulatory_inspections(inspection_id),
    commitment_description  TEXT,
    regulatory_ref          VARCHAR(50),
    committed_date          DATE,
    committed_by            INT REFERENCES employees(employee_id),
    target_response_date    DATE,
    actual_response_date    DATE,
    status                  VARCHAR(20),  -- Open | Submitted | Accepted | Overdue
    capa_id                 VARCHAR(20) REFERENCES capa_records(capa_id)
);

-- ─────────────────────────────────────────
-- USEFUL VIEWS FOR CHATBOT QUERIES
-- ─────────────────────────────────────────

-- CAPA performance view
CREATE VIEW v_capa_metrics AS
SELECT
    c.capa_id,
    c.severity,
    c.source_type,
    c.root_cause_category,
    c.status,
    c.initiation_date,
    c.target_close_date,
    c.actual_close_date,
    c.reopen_count,
    c.effectiveness_check_result,
    s.site_name,
    d.dept_name,
    CASE WHEN c.actual_close_date IS NULL
         THEN CURRENT_DATE - c.initiation_date
         ELSE c.actual_close_date - c.initiation_date
    END AS age_days,
    CASE WHEN c.actual_close_date IS NULL AND c.target_close_date < CURRENT_DATE
         THEN TRUE ELSE FALSE
    END AS is_overdue,
    CASE WHEN c.actual_close_date <= c.target_close_date THEN TRUE
         WHEN c.actual_close_date IS NOT NULL THEN FALSE
         ELSE NULL
    END AS closed_on_time
FROM capa_records c
LEFT JOIN sites s USING (site_id)
LEFT JOIN departments d USING (dept_id);

-- Training compliance view
CREATE VIEW v_training_compliance AS
SELECT
    e.employee_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    e.job_title,
    d.dept_name,
    s.site_name,
    COUNT(tr.training_record_id) AS total_assigned,
    SUM(CASE WHEN tr.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN tr.status = 'Overdue' THEN 1 ELSE 0 END) AS overdue,
    ROUND(100.0 * SUM(CASE WHEN tr.status = 'Completed' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(tr.training_record_id), 0), 1) AS compliance_rate_pct
FROM employees e
LEFT JOIN training_records tr ON e.employee_id = tr.employee_id
LEFT JOIN departments d ON e.department_id = d.dept_id
LEFT JOIN sites s ON e.site_id = s.site_id
WHERE e.is_active = TRUE
GROUP BY e.employee_id, e.first_name, e.last_name, e.job_title, d.dept_name, s.site_name;

-- Integrated quality event view
CREATE VIEW v_quality_events AS
SELECT
    dev.deviation_id,
    dev.detection_date,
    dev.deviation_category,
    dev.severity,
    dev.batch_disposition_impact,
    prod.product_name,
    prod.dosage_form,
    s.site_name,
    d.dept_name,
    c.capa_id,
    c.status AS capa_status,
    c.root_cause_category,
    b.batch_number,
    b.batch_status
FROM deviation_records dev
LEFT JOIN products prod ON dev.product_id = prod.product_id
LEFT JOIN sites s ON dev.site_id = s.site_id
LEFT JOIN departments d ON dev.department_id = d.dept_id
LEFT JOIN capa_records c ON dev.capa_id = c.capa_id
LEFT JOIN batch_records b ON dev.batch_id = b.batch_id;
