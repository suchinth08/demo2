# Data Dictionary — Compliance BI Platform

**Document Type: Data Reference**
**Version: 1.0 | April 2026**
**Audience: Data Engineers, Analysts, QA, Developers**

---

## Overview

This data dictionary covers all 18 tables in the Compliance BI data model. All tables are governed by FDA 21 CFR Parts 210/211, 21 CFR Part 11 (for electronic records), ICH Q9, and ICH Q10 where applicable.

**Data Type Conventions:**
- `VARCHAR(n)` — Variable-length string, max n characters
- `TEXT` — Unlimited-length string (narrative fields)
- `INT` / `SERIAL` — 32-bit integer (SERIAL = auto-increment primary key)
- `DECIMAL(p,s)` — Fixed-precision decimal, p digits total, s after decimal
- `DATE` — Calendar date (YYYY-MM-DD)
- `BOOLEAN` — True/False

---

## Table: sites

**Description:** Master reference for all physical and virtual locations in the pharmaceutical quality system. Sites form the top-level dimension for all compliance data.

**Regulatory Reference:** FDA 21 CFR 211.42 (design and construction of premises), FDA Establishment Registration

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| site_id | VARCHAR(10) | Unique site identifier | SITE-US-01 | No | PRIMARY KEY |
| site_name | VARCHAR(100) | Full site name | Philadelphia Manufacturing | No | NOT NULL |
| country | VARCHAR(50) | Country of operation | USA | Yes | — |
| site_type | VARCHAR(30) | Function type | Manufacturing | Yes | Manufacturing / R&D / QC Lab / Distribution |
| gxp_scope | VARCHAR(100) | GxP scope of activities | GMP | Yes | GMP / GMP+GLP / GCP |
| fda_estab_id | VARCHAR(20) | FDA Establishment Identifier | 3003457890 | Yes | — |
| is_active | BOOLEAN | Whether site is operationally active | true | No | DEFAULT TRUE |

**Business Rules:**
- All compliance records reference a valid site_id.
- Sites with is_active = false are retained for historical data but excluded from active compliance dashboards.

**Relationships:**
- Referenced by: departments, employees, capa_records, deviation_records, batch_records, audit_findings (via audits), risk_register, change_requests, regulatory_inspections, documents, equipment

---

## Table: departments

**Description:** Organizational departments within sites. Supports parent-child hierarchy for nested org structures.

**Regulatory Reference:** FDA 21 CFR 211.22 (responsibilities of quality control unit)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| dept_id | SERIAL | Auto-increment department ID | 1 | No | PRIMARY KEY |
| dept_name | VARCHAR(100) | Department name | Manufacturing QC | No | NOT NULL |
| dept_code | VARCHAR(20) | Short code | MFG-QC | Yes | UNIQUE |
| site_id | VARCHAR(10) | Site this department belongs to | SITE-US-01 | Yes | FK → sites.site_id |
| parent_dept_id | INT | Parent department for hierarchy | 2 | Yes | FK → departments.dept_id (self-ref) |
| dept_head_id | INT | Employee ID of department head | 42 | Yes | FK → employees.employee_id |

**Business Rules:**
- Root departments have parent_dept_id = NULL.
- dept_head_id is set after employees are created (circular FK resolved via ALTER TABLE).

**Relationships:**
- Referenced by: capa_records, deviation_records, training_records (via employees), audit_findings (via process area)

---

## Table: employees

**Description:** All personnel in the pharmaceutical quality system, including GMP-classified roles. Required for training tracking, CAPA ownership, and regulatory attribution.

**Regulatory Reference:** FDA 21 CFR 211.68 (data integrity and record attributability), FDA 21 CFR Part 11

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| employee_id | SERIAL | Auto-increment employee ID | 1 | No | PRIMARY KEY |
| employee_number | VARCHAR(20) | HR employee number | EMP-0342 | Yes | UNIQUE |
| first_name | VARCHAR(50) | First name | John | Yes | — |
| last_name | VARCHAR(50) | Last name | Smith | Yes | — |
| department_id | INT | Department assignment | 5 | Yes | FK → departments.dept_id |
| site_id | VARCHAR(10) | Primary site | SITE-EU-02 | Yes | FK → sites.site_id |
| job_title | VARCHAR(100) | Job title | Senior QC Analyst | Yes | — |
| role_id | INT | Job role for training curriculum mapping | 12 | Yes | FK → job_roles.role_id |
| manager_id | INT | Direct manager | 15 | Yes | FK → employees.employee_id (self-ref) |
| hire_date | DATE | Date of hire | 2021-03-15 | Yes | — |
| gmp_role | VARCHAR(20) | GxP role classification | GMP | Yes | GMP / Non-GMP / GCP / GLP |
| is_active | BOOLEAN | Currently employed | true | No | DEFAULT TRUE |
| employment_type | VARCHAR(20) | Employment type | Full-Time | Yes | Full-Time / Contractor / Part-Time |

**Business Rules:**
- is_active = false employees are excluded from open training compliance calculations.
- gmp_role determines which training curricula apply.
- Contractors are included in GMP training compliance unless explicitly excluded.

**Relationships:**
- Referenced by: training_records (employee_id and trainer_id), capa_records (owner_employee_id), deviation_records (detected_by), regulatory_commitments (committed_by), risk_register (risk_owner_id)

---

## Table: products

**Description:** Pharmaceutical products manufactured or in development at company sites. Links batch records and deviations to specific products for patient safety impact assessment.

**Regulatory Reference:** FDA 21 CFR 211.100 (written procedures), 21 CFR 314 (NDA/ANDA)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| product_id | SERIAL | Auto-increment product ID | 1 | No | PRIMARY KEY |
| product_code | VARCHAR(30) | Internal product code | PROD-001 | Yes | UNIQUE |
| product_name | VARCHAR(200) | Full product name | Lisinopril 10mg Tablets | Yes | — |
| product_type | VARCHAR(30) | Product category | Drug Product | Yes | Drug Substance / Drug Product / Biologic |
| dosage_form | VARCHAR(30) | Dosage form | Tablet | Yes | Tablet / Capsule / Injectable / Topical |
| therapeutic_area | VARCHAR(50) | Therapeutic category | Cardiovascular | Yes | — |
| nda_anda_number | VARCHAR(20) | Regulatory application number | ANDA-078921 | Yes | — |
| regulatory_status | VARCHAR(30) | Approval status | Approved | Yes | Approved / Investigational / Discontinued |
| is_gmp | BOOLEAN | Manufactured under GMP | true | No | DEFAULT TRUE |
| is_serialized | BOOLEAN | Subject to serialization/track-and-trace | false | No | DEFAULT FALSE |

**Relationships:**
- Referenced by: batch_records, deviation_records, risk_register

---

## Table: materials

**Description:** Raw materials and components used in pharmaceutical manufacturing. Critical materials require enhanced supplier and incoming inspection controls.

**Regulatory Reference:** FDA 21 CFR 211.80 (general requirements for components, drug product containers, closures, and labeling)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| material_id | SERIAL | Auto-increment material ID | 1 | No | PRIMARY KEY |
| material_code | VARCHAR(30) | Internal material code | MAT-API-001 | Yes | UNIQUE |
| material_name | VARCHAR(200) | Material name | Lisinopril API | Yes | — |
| material_type | VARCHAR(30) | Material category | API | Yes | API / Excipient / Packaging / Solvent |
| pharmacopeia | VARCHAR(30) | Applicable compendium | USP | Yes | USP / EP / JP / In-House |
| is_critical | BOOLEAN | Critical material designation | true | No | DEFAULT FALSE |

**Business Rules:**
- is_critical = true materials require enhanced incoming inspection and supplier qualification.

**Relationships:**
- Referenced by: supplier_incoming_inspections

---

## Table: equipment

**Description:** Equipment and instruments subject to qualification, calibration, and preventive maintenance. Equipment failures are a leading root cause category for deviations.

**Regulatory Reference:** FDA 21 CFR 211.63 (equipment design, size, and location), 21 CFR 211.68 (automatic, mechanical, electronic equipment)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| equipment_id | VARCHAR(20) | Equipment tag number | EQP-2047 | No | PRIMARY KEY |
| equipment_name | VARCHAR(100) | Equipment name | Tablet Press B | Yes | — |
| equipment_type | VARCHAR(50) | Equipment category | Tablet Press | Yes | Reactor / HPLC / Autoclave / Tablet Press / etc. |
| site_id | VARCHAR(10) | Location site | SITE-EU-02 | Yes | FK → sites.site_id |
| manufacturing_area | VARCHAR(50) | Area within site | Area B2 | Yes | — |
| qualification_status | VARCHAR(20) | Current qualification state | Overdue | Yes | Qualified / Overdue / Pending |
| last_qual_date | DATE | Date of last qualification | 2025-09-12 | Yes | — |
| next_qual_date | DATE | Scheduled next qualification | 2026-03-12 | Yes | — |

**Business Rules:**
- Equipment with qualification_status = 'Overdue' is a high-priority item for the Root Cause Investigator Agent when deviations involve that equipment.
- next_qual_date overdue by >30 days generates a Policy Engine alert.

**Relationships:**
- Referenced by: deviation_records (equipment_id)

---

## Table: documents

**Description:** Controlled documents in the pharmaceutical document management system, including SOPs, Work Instructions, Policies, Specifications, and Protocols. Subject to FDA 21 CFR Part 11 electronic records requirements.

**Regulatory Reference:** FDA 21 CFR 211.100 (written procedures), FDA 21 CFR Part 11, ICH Q10 3.2.2 (document management)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| doc_id | VARCHAR(20) | Document identifier | DOC-SOP-MFG-042 | No | PRIMARY KEY |
| doc_number | VARCHAR(30) | Document control number | SOP-MFG-042 | Yes | UNIQUE |
| doc_title | VARCHAR(200) | Full document title | Tablet Compression Process | Yes | — |
| doc_type | VARCHAR(30) | Document category | SOP | Yes | SOP / Work Instruction / Policy / Form / Spec / Protocol |
| business_function | VARCHAR(50) | Functional area | Manufacturing | Yes | — |
| gxp_classification | VARCHAR(10) | GxP applicability | GMP | Yes | GMP / GCP / GLP / GDP / Non-GxP |
| current_version | VARCHAR(10) | Current effective version | Rev 5 | Yes | — |
| status | VARCHAR(20) | Document lifecycle status | Effective | Yes | Draft / Under Review / Approved / Effective / Obsolete |
| effective_date | DATE | Date document became effective | 2026-03-15 | Yes | — |
| next_review_date | DATE | Scheduled next review | 2028-03-15 | Yes | — |
| last_review_date | DATE | Date of last review | 2026-03-15 | Yes | — |
| review_freq_months | INT | Review cycle in months | 24 | Yes | DEFAULT 24 |
| owner_dept_id | INT | Owning department | 5 | Yes | FK → departments.dept_id |
| doc_owner_id | INT | Document owner employee | 42 | Yes | FK → employees.employee_id |
| regulatory_ref | VARCHAR(200) | Applicable regulatory sections | 21 CFR 211.100 | Yes | — |
| is_controlled | BOOLEAN | Under document control | true | Yes | DEFAULT TRUE |
| site_id | VARCHAR(10) | Site scope (null = enterprise-wide) | SITE-US-01 | Yes | FK → sites.site_id |
| training_required | BOOLEAN | Requires training on change | true | Yes | DEFAULT TRUE |

**Business Rules:**
- Effective documents with next_review_date < CURRENT_DATE are flagged as overdue for review.
- Documents with training_required = true trigger the Training Cascade Agent when status transitions to Effective with a new version.

**Relationships:**
- Referenced by: training_records, document_versions, capa_action_items

---

## Table: capa_records

**Description:** Corrective and Preventive Action records — the central quality system record for addressing root causes of compliance failures. CAPAs are a primary focus area for FDA inspections.

**Regulatory Reference:** FDA 21 CFR 820.100 (corrective and preventive action), ICH Q10 Section 3.2.3

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| capa_id | VARCHAR(20) | CAPA identifier | CAPA-2026-0112 | No | PRIMARY KEY |
| site_id | VARCHAR(10) | Site where CAPA originates | SITE-EU-02 | Yes | FK → sites.site_id |
| department_id | INT | Department responsible | 5 | Yes | FK → departments.dept_id |
| source_type | VARCHAR(30) | Event type that triggered CAPA | Deviation | Yes | Audit / Deviation / Complaint / Inspection / Self-Identified |
| source_reference_id | VARCHAR(20) | ID of the triggering event | DEV-2026-0847 | Yes | — |
| severity | VARCHAR(10) | CAPA severity classification | Critical | Yes | Critical / Major / Minor |
| root_cause_category | VARCHAR(50) | High-level root cause | Equipment | Yes | Training / Procedure / Equipment / System / Material / Human Error |
| root_cause_detail | TEXT | Narrative root cause description | Equipment qualification overdue 33 days | Yes | — |
| description | TEXT | Full CAPA problem statement | Tablet press EQP-2047 was not re-qualified per schedule | Yes | — |
| initiated_by | VARCHAR(100) | Name or ID of initiator | john.smith@company.com | Yes | — |
| owner_employee_id | INT | Responsible CAPA owner | 42 | Yes | FK → employees.employee_id |
| initiation_date | DATE | Date CAPA was opened | 2026-04-03 | Yes | — |
| target_close_date | DATE | Committed closure date | 2026-05-03 | Yes | — |
| actual_close_date | DATE | Actual closure date | null | Yes | — |
| status | VARCHAR(20) | Current status | Open | Yes | Open / In Progress / Pending Effectiveness / Closed / Overdue |
| effectiveness_check_req | BOOLEAN | Is effectiveness check required | true | Yes | DEFAULT FALSE |
| effectiveness_check_date | DATE | Date check was/is due | 2026-07-03 | Yes | — |
| effectiveness_check_result | VARCHAR(10) | Outcome of effectiveness check | null | Yes | Pass / Fail / Pending |
| reopen_count | INT | Number of times reopened | 0 | Yes | DEFAULT 0 |
| regulatory_notif_required | BOOLEAN | Requires regulatory notification | false | Yes | DEFAULT FALSE |

**Business Rules:**
- Critical CAPAs must have target_close_date ≤ 30 days from initiation_date.
- Major CAPAs must have target_close_date ≤ 60 days from initiation_date.
- status must be set to 'Overdue' when actual_close_date IS NULL AND target_close_date < CURRENT_DATE.
- CAPA may not be closed without root_cause_category and root_cause_detail populated.
- effectiveness_check_req = true is mandatory for all Critical and Major CAPAs.

**Key Derived Metrics:**
- `on_time_closure_rate`: % of closed CAPAs where actual_close_date <= target_close_date
- `capa_cycle_time`: average days from initiation_date to actual_close_date (closed CAPAs)
- `recurrence_rate`: % of closed CAPAs with reopen_count > 0

**Relationships:**
- Referenced by: deviation_records (capa_id), audit_findings (capa_id), risk_register (linked_capa_id), change_requests (linked_capa_id), regulatory_commitments (capa_id)

---

## Table: deviation_records

**Description:** Records of unplanned events or departures from approved procedures, specifications, or standards during manufacturing. Primary source of quality system workload.

**Regulatory Reference:** FDA 21 CFR 211.192 (production record review), FDA 21 CFR 211.110

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| deviation_id | VARCHAR(20) | Deviation identifier | DEV-2026-0847 | No | PRIMARY KEY |
| site_id | VARCHAR(10) | Site where deviation occurred | SITE-EU-02 | Yes | FK → sites.site_id |
| department_id | INT | Originating department | 5 | Yes | FK → departments.dept_id |
| batch_id | VARCHAR(30) | Affected batch (if applicable) | BATCH-2026-1847 | Yes | FK → batch_records.batch_id |
| product_id | INT | Affected product | 3 | Yes | FK → products.product_id |
| deviation_category | VARCHAR(30) | Category of event | Equipment | Yes | Equipment / Process / Personnel / Material / Environmental / Analytical |
| deviation_type | VARCHAR(20) | Planned vs unplanned | Unplanned | Yes | Planned / Unplanned |
| severity | VARCHAR(10) | Impact classification | Critical | Yes | Critical / Major / Minor |
| description | TEXT | Full event description | Tablet press EQP-2047 produced out-of-spec tablets | Yes | — |
| detected_by | INT | Employee who detected event | 42 | Yes | FK → employees.employee_id |
| detection_date | DATE | Date event was detected | 2026-04-01 | Yes | — |
| manufacturing_area | VARCHAR(50) | Physical area | Area B2 | Yes | — |
| equipment_id | VARCHAR(20) | Involved equipment | EQP-2047 | Yes | FK → equipment.equipment_id |
| shift | VARCHAR(10) | Shift when event occurred | Day | Yes | Day / Evening / Night |
| gmp_classification | VARCHAR(10) | GMP vs non-GMP event | GMP | Yes | GMP / Non-GMP |
| investigation_required | BOOLEAN | Formal investigation needed | true | Yes | DEFAULT TRUE |
| investigation_close_dt | DATE | Date investigation completed | null | Yes | — |
| root_cause_category | VARCHAR(50) | Root cause category | Equipment | Yes | (same as CAPA root cause values) |
| root_cause_description | TEXT | Narrative root cause | Equipment EQP-2047 was 33 days overdue for qualification | Yes | — |
| capa_id | VARCHAR(20) | Linked CAPA (if initiated) | null | Yes | FK → capa_records.capa_id |
| batch_disposition_impact | VARCHAR(20) | Impact on batch | Hold | Yes | None / Hold / Reject / Conditional Release |
| status | VARCHAR(20) | Current status | Under Investigation | Yes | Open / Under Investigation / Investigation Complete / Closed |

**Business Rules:**
- Critical deviations must have a linked CAPA within 48 hours of detection.
- Deviations with batch_disposition_impact != 'None' require a Quality Disposition Review.
- GMP-classified deviations with severity = Critical must be reported to site QA Director within 24 hours.

**Relationships:**
- References: capa_records, batch_records, products, equipment, employees, sites, departments

---

## Table: audit_findings

**Description:** Individual findings from internal, external, or regulatory audits. Each finding may require a CAPA. Repeat findings are a key compliance risk indicator.

**Regulatory Reference:** FDA 21 CFR 211.192 (production record review), EU GMP Annex 16, ICH Q10 3.3 (management review)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| finding_id | VARCHAR(20) | Finding identifier | AFND-2025-0045 | No | PRIMARY KEY |
| audit_id | VARCHAR(20) | Parent audit | AUD-2025-0012 | Yes | FK → audits.audit_id |
| finding_number | INT | Sequential number within audit | 3 | Yes | — |
| classification | VARCHAR(15) | Severity classification | Major | Yes | Critical / Major / Minor / Observation |
| regulatory_ref | VARCHAR(50) | Applicable regulation | 21 CFR 211.68 | Yes | — |
| process_area | VARCHAR(50) | Process area where finding applies | Laboratory Controls | Yes | — |
| finding_description | TEXT | Full finding description | Computer system validation documentation incomplete | Yes | — |
| root_cause | TEXT | Identified root cause | Validation master plan not updated after system upgrade | Yes | — |
| is_repeat_finding | BOOLEAN | Has this finding appeared before | false | No | DEFAULT FALSE |
| prior_finding_id | VARCHAR(20) | Prior finding this repeats | null | Yes | FK → audit_findings.finding_id (self-ref) |
| capa_id | VARCHAR(20) | Linked CAPA | null | Yes | FK → capa_records.capa_id |
| response_date | DATE | Date response submitted | null | Yes | — |
| response_status | VARCHAR(20) | Status of response | Open | Yes | Open / Submitted / Accepted / Rejected |
| close_date | DATE | Date finding closed | null | Yes | — |

**Business Rules:**
- is_repeat_finding = true when the same observation in the same process area has appeared in a prior audit within 3 years.
- repeat_finding_rate = % of findings with is_repeat_finding = true.
- Critical findings must have a CAPA initiated within 24 hours.

**Relationships:**
- References: audits, capa_records

---

## Table: training_records

**Description:** Individual training completion records. The primary evidence of employee qualification to perform GMP activities. Subject to 21 CFR Part 11 electronic records requirements.

**Regulatory Reference:** FDA 21 CFR 211.68 (employee qualification), FDA 21 CFR 211.192, FDA 21 CFR Part 11

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| training_record_id | SERIAL | Auto-increment ID | 1 | No | PRIMARY KEY |
| employee_id | INT | Employee who was trained | 42 | Yes | FK → employees.employee_id |
| doc_id | VARCHAR(20) | Document trained on | DOC-SOP-MFG-042 | Yes | FK → documents.doc_id |
| curriculum_id | INT | Curriculum this record belongs to | 5 | Yes | FK → training_curricula.curriculum_id |
| training_type | VARCHAR(30) | Why this training was assigned | Change-Driven | Yes | Initial / Refresher / Remedial / Change-Driven |
| delivery_method | VARCHAR(20) | How training was delivered | Read-and-Understand | Yes | eLearning / Classroom / OJT / Read-and-Understand |
| assigned_date | DATE | Date training was assigned | 2026-04-03 | Yes | — |
| due_date | DATE | Required completion date | 2026-04-17 | Yes | — |
| completion_date | DATE | Date training was completed | null | Yes | — |
| assessment_score | DECIMAL(5,2) | Score on assessment (if applicable) | null | Yes | — |
| assessment_passed | BOOLEAN | Did employee pass the assessment | null | Yes | — |
| attempt_number | INT | Attempt number (for remedial tracking) | 1 | Yes | DEFAULT 1 |
| trainer_id | INT | Trainer employee (for OJT/Classroom) | null | Yes | FK → employees.employee_id |
| status | VARCHAR(20) | Current status | Assigned | Yes | Assigned / In Progress / Completed / Overdue / Waived |
| waiver_reason | TEXT | Justification if training waived | null | Yes | — |

**Business Rules:**
- status must be updated to 'Overdue' when completion_date IS NULL AND due_date < CURRENT_DATE.
- Waived training records require waiver_reason to be populated.
- training_compliance_rate = completed / total_assigned × 100 (per employee, department, site).

**Relationships:**
- References: employees, documents, training_curricula

---

## Table: batch_records

**Description:** Manufacturing batch records. Required by FDA 21 CFR 211.188. Each batch has a lifecycle from manufacturing through disposition. Batch status is a key quality indicator.

**Regulatory Reference:** FDA 21 CFR 211.188 (batch production and control records), 21 CFR 211.192 (production record review)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| batch_id | VARCHAR(30) | Batch identifier | BATCH-2026-1847 | No | PRIMARY KEY |
| product_id | INT | Product manufactured | 3 | Yes | FK → products.product_id |
| batch_number | VARCHAR(30) | Batch/lot number | 2026B1847 | Yes | — |
| manufacturing_date | DATE | Date manufacturing started | 2026-03-28 | Yes | — |
| release_date | DATE | Date batch was released | null | Yes | — |
| expiry_date | DATE | Expiry date | 2028-03-28 | Yes | — |
| batch_size | DECIMAL(12,3) | Batch quantity | 500000.000 | Yes | — |
| batch_size_unit | VARCHAR(10) | Unit of measure | Units | Yes | — |
| site_id | VARCHAR(10) | Manufacturing site | SITE-EU-02 | Yes | FK → sites.site_id |
| manufacturing_line | VARCHAR(30) | Specific line or suite | Line B-2 | Yes | — |
| batch_status | VARCHAR(20) | Current batch status | On Hold | Yes | Released / Rejected / On Hold / In Process |
| disposition_date | DATE | Date of disposition decision | null | Yes | — |

**Business Rules:**
- batch_rejection_rate = rejected / total_batches × 100.
- Batches with batch_status = 'On Hold' that are older than 30 days require management review.

**Relationships:**
- Referenced by: deviation_records

---

## Table: suppliers

**Description:** Approved vendor list. All suppliers of APIs, excipients, packaging, CROs, and CMOs. Qualification status is a regulatory requirement for critical suppliers.

**Regulatory Reference:** FDA 21 CFR 211.84 (testing and approval or rejection of components), FDA Quality Systems (supplier qualification)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| supplier_id | SERIAL | Auto-increment supplier ID | 1 | No | PRIMARY KEY |
| supplier_code | VARCHAR(20) | Internal supplier code | SUP-API-001 | Yes | UNIQUE |
| supplier_name | VARCHAR(200) | Full supplier name | Sigma API Solutions | Yes | — |
| supplier_type | VARCHAR(30) | Supplier category | API | Yes | API / Excipient / Packaging / CRO / CMO / Service |
| qualification_status | VARCHAR(20) | Current qualification status | Approved | Yes | Approved / Conditional / Suspended / Disqualified / Pending |
| qualification_date | DATE | Date of qualification | 2023-06-15 | Yes | — |
| requalification_due_dt | DATE | Due date for requalification | 2026-06-15 | Yes | — |
| country | VARCHAR(50) | Country of manufacture | India | Yes | — |
| regulatory_approvals | VARCHAR(200) | Regulatory clearances held | FDA DMF 12345, CEP | Yes | — |
| risk_rating | VARCHAR(10) | Supplier risk tier | High | Yes | High / Medium / Low |
| is_gmp_critical | BOOLEAN | GMP critical supplier | true | No | DEFAULT FALSE |

**Business Rules:**
- Suspended or Disqualified suppliers must not receive new purchase orders.
- Suppliers with requalification_due_dt < CURRENT_DATE + 60 days are flagged by Supplier Risk Monitor Agent.

**Relationships:**
- Referenced by: audits (supplier_id), supplier_incoming_inspections

---

## Table: supplier_incoming_inspections

**Description:** Records of incoming material inspections for each lot received from a supplier. The primary source for supplier quality metrics (rejection rate, CoA compliance).

**Regulatory Reference:** FDA 21 CFR 211.84 (testing and approval or rejection of components)

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| inspection_id | SERIAL | Auto-increment ID | 1 | No | PRIMARY KEY |
| supplier_id | INT | Supplying vendor | 1 | Yes | FK → suppliers.supplier_id |
| material_id | INT | Material received | 5 | Yes | FK → materials.material_id |
| po_number | VARCHAR(30) | Purchase order number | PO-2026-08471 | Yes | — |
| lot_number | VARCHAR(30) | Supplier lot number | SIG-API-2026-847 | Yes | — |
| receipt_date | DATE | Date received | 2026-03-15 | Yes | — |
| inspection_date | DATE | Date of inspection | 2026-03-17 | Yes | — |
| qty_received | DECIMAL(12,3) | Quantity received | 250.000 | Yes | — |
| qty_unit | VARCHAR(10) | Unit of measure | kg | Yes | — |
| inspection_result | VARCHAR(20) | Inspection outcome | Fail | Yes | Pass / Fail / Conditional Release / Pending |
| rejection_reason | VARCHAR(100) | Reason for rejection | Out of Spec - Purity | Yes | — |
| coa_compliant | BOOLEAN | Certificate of Analysis compliant | true | Yes | — |
| inspector_id | INT | QC inspector | 42 | Yes | FK → employees.employee_id |
| capa_triggered | VARCHAR(20) | CAPA initiated for this failure | CAPA-0087 | Yes | FK → capa_records.capa_id |

**Key Derived Metrics:**
- `supplier_rejection_rate`: failed_lots / total_lots × 100
- `coa_compliance_rate`: coa_compliant=true / total_lots × 100

**Relationships:**
- References: suppliers, materials, employees, capa_records

---

## Table: risk_register

**Description:** ICH Q9-aligned risk register. Captures quality risks with initial and residual RPN scoring (Severity × Occurrence × Detectability). Required for ICH Q10 pharmaceutical quality system.

**Regulatory Reference:** ICH Q9 Quality Risk Management, ICH Q10 Section 3.1

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| risk_id | VARCHAR(20) | Risk identifier | RSK-0089 | No | PRIMARY KEY |
| risk_title | VARCHAR(200) | Short risk description | Tablet Press Preventive Maintenance Gap | Yes | — |
| risk_description | TEXT | Full risk description | Failure to maintain PM schedule for tablet presses increases deviation risk | Yes | — |
| risk_category | VARCHAR(30) | Risk category | Process | Yes | Process / Product Quality / Regulatory / Patient Safety / Supply Chain / IT |
| business_process | VARCHAR(100) | Affected process | Solid Dose Manufacturing | Yes | — |
| product_id | INT | Affected product | 3 | Yes | FK → products.product_id |
| site_id | VARCHAR(10) | Affected site | SITE-EU-02 | Yes | FK → sites.site_id |
| risk_owner_id | INT | Risk owner employee | 42 | Yes | FK → employees.employee_id |
| initial_severity | INT | Pre-control severity score | 8 | Yes | CHECK 1–10 |
| initial_occurrence | INT | Pre-control occurrence score | 6 | Yes | CHECK 1–10 |
| initial_detectability | INT | Pre-control detectability score | 4 | Yes | CHECK 1–10 |
| initial_rpn | INT | S × O × D (initial) | 192 | Yes | — |
| risk_controls | TEXT | Implemented controls | Quarterly PM audit; automated overdue alert | Yes | — |
| residual_severity | INT | Post-control severity | 8 | Yes | CHECK 1–10 |
| residual_occurrence | INT | Post-control occurrence | 3 | Yes | CHECK 1–10 |
| residual_detectability | INT | Post-control detectability | 6 | Yes | CHECK 1–10 |
| residual_rpn | INT | S × O × D (residual) | 144 | Yes | — |
| risk_acceptance_status | VARCHAR(20) | Acceptability determination | Unacceptable | Yes | Acceptable / Unacceptable / ALARP |
| last_review_date | DATE | Date of last risk review | 2025-08-15 | Yes | — |
| next_review_date | DATE | Scheduled next review | 2026-08-15 | Yes | — |
| status | VARCHAR(20) | Risk lifecycle status | Active | Yes | Active / Closed / Transferred |
| icq9_tool_used | VARCHAR(20) | ICH Q9 risk tool | FMEA | Yes | FMEA / HACCP / FTA / PHA / HAZOP |
| linked_capa_id | VARCHAR(20) | CAPA addressing this risk | null | Yes | FK → capa_records.capa_id |

**Business Rules:**
- Risks with residual_rpn > 100 must have risk_controls documented.
- Risks with risk_acceptance_status = 'Unacceptable' must have a linked_capa_id.
- Risks with next_review_date < CURRENT_DATE generate a Policy Engine reminder.
- initial_rpn and residual_rpn should equal S × O × D — enforced by data quality checks.

**Relationships:**
- References: products, sites, employees, capa_records

---

## Table: regulatory_inspections

**Description:** Records of inspections by regulatory authorities (FDA, EMA, PMDA, etc.). Outcome data drives the Inspection Readiness Agent and regulatory commitment tracking.

**Regulatory Reference:** FDA 21 CFR 510(k), FDA inspection authority under FD&C Act Section 704

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| inspection_id | VARCHAR(20) | Inspection identifier | INSP-2024-FDA-01 | No | PRIMARY KEY |
| site_id | VARCHAR(10) | Inspected site | SITE-US-01 | Yes | FK → sites.site_id |
| inspecting_authority | VARCHAR(30) | Regulatory agency | FDA | Yes | FDA / EMA / PMDA / MHRA / Health Canada / WHO |
| inspection_type | VARCHAR(30) | Type of inspection | Routine | Yes | Pre-Approval / Routine / For Cause / Follow-Up |
| inspection_start_date | DATE | First day of inspection | 2024-03-18 | Yes | — |
| inspection_end_date | DATE | Last day of inspection | 2024-03-22 | Yes | — |
| lead_investigator | VARCHAR(100) | Lead FDA investigator name | Dr. Sarah Chen | Yes | — |
| form_483_issued | BOOLEAN | Was a Form 483 issued | true | No | DEFAULT FALSE |
| form_483_observation_count | INT | Number of 483 observations | 3 | Yes | DEFAULT 0 |
| warning_letter_issued | BOOLEAN | Was a Warning Letter issued | false | No | DEFAULT FALSE |
| import_alert_issued | BOOLEAN | Was an import alert issued | false | No | DEFAULT FALSE |
| overall_outcome | VARCHAR(30) | NAI/VAI/OAI outcome | VAI | Yes | NAI (No Action Indicated) / VAI (Voluntary Action Indicated) / OAI (Official Action Indicated) |
| response_due_date | DATE | FDA response deadline | 2024-04-22 | Yes | — |

**Business Rules:**
- OAI outcome is the most serious — may lead to Warning Letter or import alert.
- Repeat VAI outcome at the same site is a risk indicator for OAI escalation.

**Relationships:**
- Referenced by: regulatory_commitments

---

## Table: regulatory_commitments

**Description:** Specific regulatory commitments made in response to FDA 483 observations or other inspection findings. These are legally binding commitments with firm response deadlines.

**Regulatory Reference:** FDA Warning Letter policy, FDA Close-out procedures for 483 responses

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| commitment_id | VARCHAR(20) | Commitment identifier | RCOM-0012 | No | PRIMARY KEY |
| inspection_id | VARCHAR(20) | Parent inspection | INSP-2024-FDA-01 | Yes | FK → regulatory_inspections.inspection_id |
| commitment_description | TEXT | What the company committed to | Complete computer system validation update by June 2024 | Yes | — |
| regulatory_ref | VARCHAR(50) | Regulatory section cited | 21 CFR 211.68 | Yes | — |
| committed_date | DATE | Date commitment was made | 2024-04-15 | Yes | — |
| committed_by | INT | Employee who made commitment | 15 | Yes | FK → employees.employee_id |
| target_response_date | DATE | Committed response date | 2024-06-30 | Yes | — |
| actual_response_date | DATE | Date response was submitted | null | Yes | — |
| status | VARCHAR(20) | Current status | Overdue | Yes | Open / Submitted / Accepted / Overdue |
| capa_id | VARCHAR(20) | Linked CAPA | null | Yes | FK → capa_records.capa_id |

**Business Rules:**
- status = 'Overdue' when actual_response_date IS NULL AND target_response_date < CURRENT_DATE.
- Overdue regulatory commitments are a critical risk factor for escalation to Warning Letter.
- All commitments should have a linked CAPA within 30 days of being made.

**Relationships:**
- References: regulatory_inspections, employees, capa_records

---

## Table: change_requests

**Description:** Change Control records. All changes to processes, equipment, materials, facilities, software, or labeling require documented change control per ICH Q10.

**Regulatory Reference:** ICH Q10 Section 3.2.3 (change management), FDA 21 CFR 314.70 (supplements and other changes), 21 CFR 211.100

| Column | Type | Description | Example | Nullable | Constraints |
|---|---|---|---|---|---|
| change_id | VARCHAR(20) | Change control identifier | CC-2026-0234 | No | PRIMARY KEY |
| change_title | VARCHAR(200) | Short description | Tablet Press B Speed Parameter Change | Yes | — |
| change_category | VARCHAR(30) | Category of change | Equipment | Yes | Process / Equipment / Material / Facility / Software / Labeling |
| change_type | VARCHAR(20) | Impact magnitude | Major | Yes | Minor / Major / Critical / Emergency |
| site_id | VARCHAR(10) | Site where change occurs | SITE-EU-02 | Yes | FK → sites.site_id |
| initiating_dept_id | INT | Department initiating change | 5 | Yes | FK → departments.dept_id |
| requestor_id | INT | Employee requesting change | 42 | Yes | FK → employees.employee_id |
| description | TEXT | Full change description | Change tablet press speed from 45 to 50 rpm | Yes | — |
| business_justification | TEXT | Why change is needed | Productivity improvement, validated range 40-55 rpm | Yes | — |
| product_impact | BOOLEAN | Does change affect product | true | Yes | DEFAULT FALSE |
| regulatory_impact | BOOLEAN | Does change require regulatory submission | true | Yes | DEFAULT FALSE |
| regulatory_filing_required | VARCHAR(20) | Type of submission required | CBE-30 | Yes | CBE-30 / CBE-0 / PAS / None / TBD |
| safety_impact | BOOLEAN | Does change impact patient safety | false | Yes | DEFAULT FALSE |
| initiation_date | DATE | Date change request opened | 2026-03-01 | Yes | — |
| impact_assess_due_date | DATE | Due date for impact assessment | 2026-03-15 | Yes | — |
| impact_assess_complete_dt | DATE | Date assessment completed | 2026-03-14 | Yes | — |
| approval_date | DATE | Date change was approved | 2026-03-20 | Yes | — |
| implementation_date | DATE | Date change was implemented | 2026-04-01 | Yes | — |
| close_date | DATE | Date change was closed | null | Yes | — |
| status | VARCHAR(30) | Current status | Implemented | Yes | Initiated / Under Review / Approved / Implemented / Closed / Rejected |
| approved_by | INT | Approving employee | 15 | Yes | FK → employees.employee_id |
| linked_capa_id | VARCHAR(20) | Related CAPA if change is corrective | null | Yes | FK → capa_records.capa_id |
| linked_deviation_id | VARCHAR(20) | Related deviation if change is corrective | null | Yes | FK → deviation_records.deviation_id |

**Business Rules:**
- Changes with regulatory_impact = true must have regulatory_filing_required assessed within 5 business days.
- Emergency changes must be assessed for GMP impact within 24 hours.

**Relationships:**
- References: sites, departments, employees, capa_records, deviation_records
- Referenced by: document_versions (change_request_id)

---

*Data Dictionary Lead: Compliance BI Platform Team | April 2026*
*Schema version: v1.0 | Source of truth: schema/compliance_schema.sql*
