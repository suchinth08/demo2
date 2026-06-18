# Data Sources & Integration Guide — Compliance BI Platform

**Document Type: Data Engineering Reference**
**Version: 1.0 | April 2026**
**Audience: Data Engineers, IT, Integration Architects**

---

## Data Source Inventory

### Current State: CSV / DuckDB (Phase 1)

The current architecture uses flat CSV files as the data layer, read at runtime by DuckDB via `read_csv_auto()`. This provides zero-infrastructure analytical capability suitable for development, demonstration, and initial production deployment with manageable data volumes.

| Data Source | Format | Location | Refresh Pattern | Owner |
|---|---|---|---|---|
| capa_records | CSV | /data/csv/capa_records.csv | Manual / generated | QA Systems |
| deviation_records | CSV | /data/csv/deviation_records.csv | Manual / generated | QA Systems |
| audit_findings | CSV | /data/csv/audit_findings.csv | Manual / generated | Internal Audit |
| audits | CSV | /data/csv/audits.csv | Manual / generated | Internal Audit |
| training_records | CSV | /data/csv/training_records.csv | Manual / generated | Training / HR |
| batch_records | CSV | /data/csv/batch_records.csv | Manual / generated | Manufacturing |
| supplier_inspections | CSV | /data/csv/supplier_inspections.csv | Manual / generated | Supplier Quality |
| suppliers | CSV | /data/csv/suppliers.csv | Manual / generated | Procurement |
| risk_register | CSV | /data/csv/risk_register.csv | Manual / generated | QRM |
| change_requests | CSV | /data/csv/change_requests.csv | Manual / generated | Change Control |
| regulatory_inspections | CSV | /data/csv/regulatory_inspections.csv | Manual / generated | Regulatory Affairs |
| regulatory_commitments | CSV | /data/csv/regulatory_commitments.csv | Manual / generated | Regulatory Affairs |
| documents | CSV | /data/csv/documents.csv | Manual / generated | Document Control |
| employees | CSV | /data/csv/employees.csv | Manual / generated | HR |
| departments | CSV | /data/csv/departments.csv | Manual / generated | HR |
| sites | CSV | /data/csv/sites.csv | Manual / generated | IT |
| products | CSV | /data/csv/products.csv | Manual / generated | Regulatory Affairs |
| suppliers | CSV | /data/csv/suppliers.csv | Manual / generated | Supplier Quality |

### Future State: System Integration (Phase 2–3)

| Source System | Data Domains | Integration Type | Phase | Priority |
|---|---|---|---|---|
| EQMS (Veeva Vault QMS) | CAPA, Deviations, Audits, Change Control | REST API (Vault REST API v24) | 2 | High |
| Training Management System (LMS/TMS) | Training Records, Curricula | REST API or JDBC | 2 | High |
| EDMS (Veeva Vault RIM / OpenText) | Documents, Document Versions | REST API | 2 | High |
| LIMS (LabVantage / SampleManager) | Batch Records, OOS/OOT results | REST API or JDBC | 2 | Medium |
| SAP ERP (S/4HANA) | Suppliers, Purchase Orders, Materials | BAPI / RFC / JDBC | 3 | Medium |
| Regulatory Database (FDA 483/Warning Letter DB) | Regulatory Benchmarking | Web scraping / FDA openFDA API | 3 | Low |
| Environmental Monitoring System | Environmental Data (deviation correlation) | REST API | 3 | Low |
| CMMS (Maximo / SAP PM) | Equipment, Calibration, PM Records | REST API / JDBC | 3 | Medium |

---

## Data Quality Rules Per Domain

### CAPA Records

| Rule ID | Rule Description | Severity | Action |
|---|---|---|---|
| DQ-CAPA-001 | severity is NOT NULL for all records | Critical | Reject record |
| DQ-CAPA-002 | initiation_date <= target_close_date | Critical | Reject record |
| DQ-CAPA-003 | status is from approved enumeration | Major | Flag for review |
| DQ-CAPA-004 | root_cause_category is NOT NULL for Closed records | Major | Alert data steward |
| DQ-CAPA-005 | owner_employee_id references a valid active employee | Major | Alert data steward |
| DQ-CAPA-006 | actual_close_date >= initiation_date (if present) | Critical | Reject record |
| DQ-CAPA-007 | reopen_count >= 0 | Major | Set to 0, flag |
| DQ-CAPA-008 | Critical CAPA: target_close_date - initiation_date <= 30 days | Minor | Policy violation (see Policy Engine) |

### Deviation Records

| Rule ID | Rule Description | Severity | Action |
|---|---|---|---|
| DQ-DEV-001 | severity is NOT NULL | Critical | Reject record |
| DQ-DEV-002 | detection_date is NOT NULL | Critical | Reject record |
| DQ-DEV-003 | deviation_category is from approved enumeration | Major | Flag for review |
| DQ-DEV-004 | gmp_classification is NOT NULL | Major | Alert data steward |
| DQ-DEV-005 | batch_disposition_impact is from approved enumeration | Major | Flag for review |
| DQ-DEV-006 | severity = Critical → investigation_required = true | Major | Auto-correct + alert |
| DQ-DEV-007 | site_id references a valid active site | Critical | Reject record |

### Training Records

| Rule ID | Rule Description | Severity | Action |
|---|---|---|---|
| DQ-TRN-001 | employee_id references a valid employee | Critical | Reject record |
| DQ-TRN-002 | doc_id references a valid document | Major | Alert data steward |
| DQ-TRN-003 | due_date >= assigned_date | Critical | Reject record |
| DQ-TRN-004 | completion_date >= assigned_date (if present) | Critical | Reject record |
| DQ-TRN-005 | assessment_score BETWEEN 0 AND 100 (if present) | Major | Reject record |
| DQ-TRN-006 | status is from approved enumeration | Major | Alert |
| DQ-TRN-007 | Waived records must have waiver_reason populated | Minor | Alert data steward |

### Risk Register

| Rule ID | Rule Description | Severity | Action |
|---|---|---|---|
| DQ-RSK-001 | initial_severity, initial_occurrence, initial_detectability all between 1 and 10 | Critical | Reject record |
| DQ-RSK-002 | initial_rpn = initial_severity × initial_occurrence × initial_detectability | Major | Auto-correct + alert |
| DQ-RSK-003 | residual_rpn = residual_severity × residual_occurrence × residual_detectability | Major | Auto-correct + alert |
| DQ-RSK-004 | residual_rpn <= initial_rpn (controls should reduce risk) | Minor | Flag for review |
| DQ-RSK-005 | risk_acceptance_status is from approved enumeration | Major | Flag |
| DQ-RSK-006 | Unacceptable risks must have risk_controls populated | Major | Policy violation |

### Supplier Inspections

| Rule ID | Rule Description | Severity | Action |
|---|---|---|---|
| DQ-SUP-001 | supplier_id references a valid supplier | Critical | Reject record |
| DQ-SUP-002 | inspection_result is from approved enumeration | Critical | Reject record |
| DQ-SUP-003 | inspection_date >= receipt_date | Major | Flag for review |
| DQ-SUP-004 | Fail results must have rejection_reason populated | Major | Alert inspector |
| DQ-SUP-005 | qty_received > 0 | Critical | Reject record |

---

## Data Refresh Patterns

### Current (Phase 1): Manual/Batch

In the current CSV-based architecture, data refresh is a manual operation:

```bash
# Full data regeneration (development/demo):
python -m data.generators.generate_compliance_data

# DuckDB views are refreshed automatically on next query:
# read_csv_auto() reads the file fresh on each connection
```

For production use in Phase 1, the recommended approach is:
1. Extract data from source EQMS to CSV files using a scheduled export script
2. Place files in /data/csv/ directory
3. DuckDB views automatically pick up the new files on the next query

**Refresh frequency recommendations:**
- CAPA, Deviations, Audit Findings: Daily (these change frequently)
- Training Records: Daily
- Supplier Inspections: Daily
- Risk Register, Change Requests: Weekly
- Documents, Employees, Sites, Products: Weekly or on-change

### Phase 2: Incremental API-Based Refresh

```
Source System API
    │
    ▼
Connector Service (Python async)
    │ Pull records WHERE updated_at > last_watermark
    │
    ▼
Data Validation Layer (DQ rules)
    │
    ├── PASS → Write to staging Parquet/CSV
    │
    └── FAIL → Log to DQ issue tracker, alert data steward
    │
    ▼
Swap into DuckDB views (atomic file replace)
    │
    ▼
Alert Platform of data refresh completion
```

**Target refresh latency by domain:**
- CAPA / Deviations: 15-minute incremental pull
- Training / Audits: Hourly
- Suppliers / Risk / Changes: Hourly
- Regulatory Inspections: Daily
- Reference data (Sites, Products, Employees): Daily

### Phase 3: Event-Driven Real-Time

For agent triggers (Deviation Watcher, Training Cascade), API-based polling is replaced by webhook or message queue events from the source system:

```
EQMS creates new Deviation record
    │
    ▼
EQMS webhook → Compliance BI API POST /events
    │
    ▼
Event router triggers relevant agents immediately
```

---

## Data Lineage Diagram

```
Source Systems                     Compliance BI Data Layer
─────────────────                  ─────────────────────────

EQMS ────────────────────────────► capa_records.csv ──────────────────┐
  (CAPA, Deviations, Audits,        deviation_records.csv              │
   Change Control)                   audit_findings.csv                 │
                                     change_requests.csv                │
                                                                        │
Training Management System ──────► training_records.csv                │
  (LMS / TMS)                                                           │
                                                                        ▼
LIMS ────────────────────────────► batch_records.csv         ┌──────────────────┐
  (Batch Records, OOS/OOT)                                    │                  │
                                                              │  DuckDB Engine   │
SAP ERP ─────────────────────────► suppliers.csv             │  (16 views)       │
  (Supplier Master, PO Data)        supplier_inspections.csv  │                  │
                                                              └────────┬─────────┘
Risk Management System ──────────► risk_register.csv                  │
  (or spreadsheet in Phase 1)                                          │
                                                                        ▼
EDMS ────────────────────────────► documents.csv             ┌──────────────────┐
  (Document Control)                                          │  Query Engine    │
                                                              │  (route_intent   │
HR / IAM System ─────────────────► employees.csv             │  _to_query)      │
                                    departments.csv           └────────┬─────────┘
                                                                        │
Regulatory Affairs ──────────────► regulatory_inspections.csv          │
  (Manual / Submission Tracking)    regulatory_commitments.csv          ▼
                                                              ┌──────────────────┐
Site Master Data ─────────────────► sites.csv                │  API Layer       │
Product Master ───────────────────► products.csv             │  (/chat, agents) │
                                                              └──────────────────┘
```

---

## CSV Format Specifications

### Common CSV Conventions

All CSV files follow these conventions:
- **Encoding:** UTF-8 with BOM (for Excel compatibility)
- **Delimiter:** Comma (,)
- **Line terminator:** CRLF (Windows) or LF (Unix)
- **Quote character:** Double quote (")
- **Null representation:** Empty field (no value between delimiters)
- **Date format:** YYYY-MM-DD (ISO 8601)
- **Boolean:** true / false (lowercase)
- **Decimal:** Period as decimal separator (1234.56)
- **Header row:** Always present as first row

### capa_records.csv Schema

```
capa_id,site_id,department_id,source_type,source_reference_id,severity,
root_cause_category,root_cause_detail,description,initiated_by,
owner_employee_id,initiation_date,target_close_date,actual_close_date,
status,effectiveness_check_req,effectiveness_check_date,
effectiveness_check_result,reopen_count,regulatory_notif_required
```

Example row:
```
CAPA-2026-0112,SITE-EU-02,5,Deviation,DEV-2026-0847,Critical,Equipment,
Equipment EQP-2047 was 33 days overdue for quarterly qualification,
Tablet press operated without required qualification...,john.smith,
42,2026-04-03,2026-05-03,,Open,true,2026-07-03,,0,false
```

### deviation_records.csv Schema

```
deviation_id,site_id,department_id,batch_id,product_id,deviation_category,
deviation_type,severity,description,detected_by,detection_date,
manufacturing_area,equipment_id,shift,gmp_classification,
investigation_required,investigation_close_dt,root_cause_category,
root_cause_description,capa_id,batch_disposition_impact,status
```

### training_records.csv Schema

```
training_record_id,employee_id,doc_id,curriculum_id,training_type,
delivery_method,assigned_date,due_date,completion_date,assessment_score,
assessment_passed,attempt_number,trainer_id,status,waiver_reason
```

### risk_register.csv Schema

```
risk_id,risk_title,risk_description,risk_category,business_process,
product_id,site_id,risk_owner_id,initial_severity,initial_occurrence,
initial_detectability,initial_rpn,risk_controls,residual_severity,
residual_occurrence,residual_detectability,residual_rpn,
risk_acceptance_status,last_review_date,next_review_date,status,
icq9_tool_used,linked_capa_id
```

### API Response Shape (/chat endpoint)

```json
{
  "session_id": "string (UUID)",
  "turn_id": "integer",
  "user_query": "string",
  "intent": {
    "intent": "string (intent type)",
    "domain": "string",
    "metrics": ["string"],
    "dimensions": ["string"],
    "time_filter": {"type": "string", "value": "string"},
    "filters": [{"field": "string", "op": "string", "value": "any"}],
    "viz_type": "string"
  },
  "narrative": "string",
  "viz_type": "string",
  "viz_spec": "object (Vega-Lite spec or table spec)",
  "data": [{"field": "value", ...}],
  "suggested_followups": ["string", "string", "string"],
  "error": "string | null"
}
```

---

## Master Data Management Approach

### Master Data Domains

**Sites:** Single source of truth. Site codes (SITE-US-01, SITE-EU-02, etc.) are stable identifiers referenced across all compliance data. Changes to site master (new site, name change, deactivation) require a formal change request and are coordinated with IT and QA.

**Employees:** Sourced from HR/IAM system. Employee IDs are stable — never reused after departure. Departed employees retain their records (is_active = false) for historical data integrity. Contractor additions require HR confirmation before addition to employee master.

**Products:** Sourced from Regulatory Affairs / SAP ERP. product_code is the stable identifier. Regulatory status changes (Approved → Discontinued) are made only by Regulatory Affairs.

**Suppliers:** Sourced from Procurement / SAP Vendor Master. qualification_status changes are made only by Supplier Quality after formal requalification or audit. Suspended suppliers are flagged in the supplier master within 24 hours of suspension decision.

**Documents:** Sourced from EDMS (Veeva Vault or equivalent). doc_number is the stable identifier. Version changes generate a new document_versions row — the master documents row is updated in place with the new version.

### Cross-Domain Consistency Rules

- Every `site_id` in any compliance record must exist in `sites.site_id`.
- Every `employee_id` in any record must exist in `employees.employee_id`.
- Every `capa_id` referenced as a foreign key must exist in `capa_records.capa_id`.
- `deviation_records.capa_id` FK is nullable — not all deviations require a CAPA.

These constraints are enforced in the SQL schema. In the CSV layer, they are enforced by the data quality validation step at ingestion.

---

## Data Governance Policies

### Data Access Control

- **Read access:** All compliance platform users can query all data via the chatbot. Row-level filtering by site is enforced based on user role (planned for Phase 2 authentication).
- **Write access:** The platform is read-only from the query engine perspective. Agents that create records (Training Cascade, CAPA Auto-Drafter) write to the source EQMS via API — not directly to the CSV layer.
- **Admin access:** Platform administrators can refresh the CSV data layer, add new query definitions, and modify policy rules.

### Data Retention

All compliance data must be retained for a minimum of:
- Batch records, CAPA, Deviations: 1 year after product expiry or discontinuation (21 CFR 211.180)
- Training records: Duration of employment + 2 years
- Audit records: 5 years minimum
- Regulatory inspection records: Indefinite (regulatory correspondence is permanent)

The CSV layer should implement a 10-year retention policy for all compliance data files.

### Data Privacy

- Employee records contain PII (first_name, last_name, employee_number). These fields are subject to applicable privacy regulations (GDPR for EU employees).
- The chatbot API does not return full employee names in aggregate compliance queries. Individual-level data (overdue training list) is restricted to authorized Quality and Training roles.
- API responses are never cached in browser storage — all data is session-ephemeral.

### Change Data Capture

For Phase 2 system integration, all source system extracts must include `updated_at` timestamps for incremental refresh. Full-table refreshes are only performed for small reference tables (sites, departments, products, materials) and during initial load.

### Data Quality SLA

| Data Domain | Completeness Target | Accuracy Target | Timeliness Target |
|---|---|---|---|
| CAPA Records | >99% required fields | >99% | <15 min from EQMS update |
| Deviation Records | >99% required fields | >99% | <15 min from EQMS update |
| Training Records | >98% required fields | >98% | <60 min from TMS update |
| Supplier Inspections | >99% required fields | >99% | <60 min from inspection entry |
| Risk Register | >98% all fields | >99% | <60 min from update |
| Reference Tables | 100% | 100% | <24 hours from change |

---

*Data Engineering Lead: Compliance BI Platform Team | April 2026*
