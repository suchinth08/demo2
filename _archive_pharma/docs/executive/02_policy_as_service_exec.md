# Policy as a Service — Executive Feature Overview

**Feature: Policy as a Service (PaaS)**
**Classification: Internal — Leadership Distribution**
**Version: 1.0 | April 2026**

---

## Feature Title & Value Statement

**Policy as a Service** — *Turn regulatory requirements and internal SOPs into continuously running rules that evaluate your data automatically, flag violations before they become findings, and ensure consistent interpretation across every site.*

Policy as a Service transforms compliance policy from static documents that people read (inconsistently) into active digital programs that run against live data — every hour, every day, at every site simultaneously.

---

## The Policy Challenge in Pharma

### Three Structural Failures in How Policy Works Today

**1. Inconsistent Interpretation Across Sites**

A pharmaceutical company operating three manufacturing sites has the same CAPA procedure SOP, but each site's Quality team interprets timelines, severity classifications, and closure criteria slightly differently. Frankfurt classifies "equipment malfunction during batch" as a Process deviation. Philadelphia classifies the same event as an Equipment deviation. Dublin has a third interpretation.

The result: cross-site metrics are incomparable, trending is misleading, and regulatory inspectors find inconsistency as a systemic quality system finding.

**2. Version Drift and Policy Lag**

When a SOP is revised, the updated policy takes effect on paper the moment it is approved. In practice, it takes weeks for all affected personnel to receive training, and months before the behavioral changes embedded in the policy are reflected in how data is recorded and how events are handled. During that gap, the policy says one thing and operations do another.

FDA inspectors find this discrepancy routinely. It is one of the most common root causes of 21 CFR 211.68 data integrity observations.

**3. Manual Policy Checking Is Impossible at Scale**

A pharmaceutical quality system generates thousands of records per month across CAPA, deviations, audits, training, supplier inspections, change requests, and regulatory commitments. Manually checking each record against the applicable regulatory and SOP requirements is not feasible. The practical result: policy compliance is checked sporadically, at audit time, when it is too late to prevent findings.

---

## What Policy as a Service Means

In plain terms, Policy as a Service works like this:

Imagine you have a highly experienced pharmaceutical regulatory compliance expert who knows every relevant clause of FDA 21 CFR Parts 210/211, ICH Q9, ICH Q10, and all your internal SOPs by heart. This expert sits next to your data systems and reads every new compliance record as soon as it is created. For each record, they check: Does this comply with the applicable requirements? Is anything missing? Is anything overdue? Is anything inconsistently classified?

They do this for every record, 24 hours a day, at every site simultaneously. They never have a bad day, never forget a clause, and never interpret a rule differently on a Tuesday than they did on a Monday.

That is what Policy as a Service does — except it is a programmable rules engine, not a person, so it is infinitely scalable, always consistent, and fully auditable.

---

## Four Policy Layers

### Layer 1: Organizational Policies

The highest-level governance rules that apply enterprise-wide, regardless of site or function. Examples:

- "Every Critical CAPA must have a target close date within 30 calendar days of initiation."
- "No CAPA may be closed without a documented root cause."
- "CAPAs with regulatory notification required must have owner assignment within 24 hours."

These rules fire against every CAPA record the moment it enters the system. Violations generate alerts immediately — not at the next monthly review.

### Layer 2: Regulatory Policies (FDA 21 CFR, ICH)

Rules encoded directly from regulatory text, mapped to specific data fields. Examples:

- **21 CFR 211.192** — All batch production records must be reviewed before batch release. Rule: Flag any batch with `batch_status = Released` where `deviation_records` with `batch_disposition_impact NOT IN ('None')` exist and `capa_id IS NULL`.
- **21 CFR 211.68** — Records must be complete, legible, and attributable. Rule: Flag any CAPA where `description IS NULL` or `initiated_by IS NULL`.
- **ICH Q9 Section 4** — Risks with `residual_rpn > 100` must have documented risk controls. Rule: Flag any `risk_register` record where `residual_rpn > 100` AND `risk_controls IS NULL`.
- **ICH Q10 3.1** — Management review must include CAPA system review. Rule: If current date is more than 30 days past scheduled QMR date and no QMR document is present in the document system, generate a reminder.

### Layer 3: Data Governance Policies

Rules that ensure data quality, completeness, and consistency — the foundation on which all analytics depend. Examples:

- Required field completeness rules: Every `deviation_records` row must have `root_cause_category` populated before status can advance beyond "Under Investigation."
- Cross-table consistency rules: If a deviation has `severity = Critical`, a linked CAPA must exist or a documented justification for no-CAPA must be present.
- Coding consistency rules: `deviation_category` must be from the approved enumeration list; free-text entries trigger a data quality alert.
- Timeliness rules: Training records with `status = Assigned` and `due_date < CURRENT_DATE` must have their status updated to `Overdue` automatically.

### Layer 4: Business Rules

Site-specific, product-specific, or process-specific rules that reflect operational decisions beyond regulatory minimums. Examples:

- "For injectable products, any deviation touching the sterile manufacturing environment automatically requires a 5-day investigation completion target, regardless of severity."
- "Supplier inspection failures for API suppliers with `risk_rating = High` must trigger a CAPA within 48 hours."
- "Any training record for a GMP-classified employee that is overdue by more than 14 days must escalate to the site Quality Director."

Business rules are configurable without code changes — they are stored in a rule registry and activated/deactivated by Quality system owners.

---

## Key Use Cases

| Use Case | Policy Layer | Business Outcome |
|---|---|---|
| CAPA timeliness enforcement | Organizational | Prevent overdue CAPAs before they become FDA findings |
| Critical deviation auto-escalation | Regulatory (21 CFR 211.192) | Ensure critical events receive management attention within hours, not days |
| Risk assessment completeness | Regulatory (ICH Q9) | Every risk assessment that reaches the register has all required ICH Q9 elements |
| Batch release data integrity check | Regulatory (21 CFR 211.68) | No batch released with open critical deviations and no CAPA |
| Training compliance threshold alerting | Organizational | Site Quality Directors alerted when training compliance drops below 95% |
| Supplier qualification enforcement | Business rule | Suspended suppliers cannot receive new material orders without Quality Director override |
| Change control regulatory impact | Regulatory (21 CFR 314.70) | Changes with potential regulatory impact flagged for Regulatory Affairs review within 24 hours |

---

## Policy Registry Concept

The Policy Registry is the central catalog of all active rules in the system. Think of it as the "source of truth" for what the platform currently enforces.

**What the Policy Registry Contains:**

| Field | Description |
|---|---|
| Policy ID | Unique identifier (e.g., POL-CAPA-001) |
| Policy Title | Plain-language name |
| Regulatory Reference | 21 CFR 211.192, ICH Q9 §4.2, SOP-QA-042 Rev 3 |
| Rule Definition | Precise condition in structured format |
| Data Domain | CAPA, Deviations, Training, etc. |
| Violation Severity | Critical, Major, Minor |
| Action on Violation | Alert, Block, Escalate, Log only |
| Sites in Scope | All, or specific site codes |
| Effective Date | When the rule became active |
| Review Owner | Who owns this rule's maintenance |

**Why the Registry Matters:**

During an FDA inspection, an inspector asks: "How do you ensure your CAPA timelines comply with your procedures?" With Policy as a Service, the answer is demonstrable: open the Policy Registry, show POL-CAPA-001, POL-CAPA-002, and POL-CAPA-003, and show the execution log demonstrating these rules ran 2,847 times in the last six months and generated 94 alerts — every one of which was investigated and resolved. This is a fundamentally stronger answer than "our compliance team reviews CAPAs at monthly management reviews."

---

## Regulatory Coverage

### FDA 21 CFR Coverage

| CFR Section | Topic | Rules Implemented |
|---|---|---|
| 21 CFR 210.1 | Status of current GMP regulations | Baseline quality system rules |
| 21 CFR 211.68 | Automatic, mechanical, electronic equipment | Data integrity checks on electronic records |
| 21 CFR 211.100 | Written procedures | SOP completeness and review cycle rules |
| 21 CFR 211.110 | Sampling and testing of in-process materials | In-process testing documentation rules |
| 21 CFR 211.180 | General requirements for records/reports | Record completeness and retention rules |
| 21 CFR 211.192 | Production record review | Batch release gating rules |
| 21 CFR 211.198 | Complaint files | Complaint investigation timeliness rules |
| 21 CFR 314.70 | Supplements and other changes | Change control regulatory impact classification |
| 21 CFR 820.100 | Corrective and preventive action | CAPA system completeness and timeliness rules |

### ICH Guideline Coverage

| Guideline | Topic | Rules Implemented |
|---|---|---|
| ICH Q9 §3 | Risk management process | Risk assessment completeness, RPN threshold rules |
| ICH Q9 §4 | Risk assessment tools | FMEA completeness, HACCP applicability rules |
| ICH Q9 §5 | Risk communication | Unacceptable risk escalation rules |
| ICH Q10 §1 | Quality management system | QMS element completeness rules |
| ICH Q10 §2.5 | Management review and monitoring | QMR timeliness and content rules |
| ICH Q10 §3.2 | CAPA system | CAPA system effectiveness rules |

---

## Business Value

| Benefit | Quantification |
|---|---|
| Regulatory finding prevention | Estimated 2–4 fewer 483 observations per inspection cycle |
| CAPA overdue rate reduction | Rules enforce timelines proactively — projected 40% reduction in overdue rate |
| Inspection preparation time | Policy compliance demonstrable on demand — saves 3–5 days of inspection prep per cycle |
| Consistency across sites | Elimination of classification inconsistencies that currently confound cross-site comparison |
| Data quality improvement | Required-field rules reduce incomplete records from estimated 12% to <2% within 90 days |
| Training lag reduction | Automated timeliness rules cut average training assignment lag from 14 to 3 days |
| Regulatory fine avoidance | Probability-weighted value of avoided Warning Letter: $200,000–$2,000,000 annually |

---

## Technical Architecture (Simplified)

```
Data Events (CAPA created, Deviation updated, Training overdue)
         │
         ▼
┌─────────────────────────────────────────┐
│           POLICY ENGINE                 │
│  ┌───────────────┐  ┌────────────────┐  │
│  │ Policy        │  │ Rule Evaluator │  │
│  │ Registry      │  │ (Python DSL)   │  │
│  │ (YAML/DB)     │  │                │  │
│  └───────────────┘  └────────────────┘  │
│          │                  │           │
│          └──────────────────┘           │
│                   │                     │
│          ┌────────▼────────┐            │
│          │ Violation       │            │
│          │ Detector        │            │
│          └────────┬────────┘            │
└───────────────────┼─────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼────┐          ┌─────▼──────┐
    │  Alert  │          │  Audit Log │
    │  Engine │          │  (Part 11) │
    └────┬────┘          └────────────┘
         │
    ┌────▼────────────────┐
    │ Notification Router  │
    │ UI Alert / Email /   │
    │ Agent Trigger        │
    └─────────────────────┘
```

---

## Success Metrics

| KPI | Baseline | 6-Month Target |
|---|---|---|
| Policy rules active in registry | 0 | 85+ rules |
| Policy evaluation runs per day | 0 | >500 evaluations |
| Alert-to-resolution time | N/A (manual) | <24 hours for Critical |
| Data record completeness rate | 88% | >98% |
| Cross-site classification consistency | Unmeasured | >95% consistency score |
| Policy registry coverage (% of CFR sections) | 0% | 70% of applicable sections |

---

## Roadmap

| Phase | Timeline | Deliverables |
|---|---|---|
| Phase 1: Foundation rules | Months 1–3 | 20 core CAPA and Deviation rules, Policy Registry v1 |
| Phase 2: Regulatory rules | Months 4–6 | Full 21 CFR 211 and ICH Q9/Q10 coverage (85+ rules) |
| Phase 3: Business rules engine | Months 7–9 | Self-service rule authoring UI for Quality teams |
| Phase 4: Predictive policy | Months 10–12 | Rules that predict future violations before they occur |

---

*Feature Lead: Compliance BI Platform Team | April 2026*
