# Agent Workflows — Detailed Technical Reference

**Document Type: Technical Architecture**
**Version: 1.0 | April 2026**
**Audience: Engineers, QA SMEs, Platform Architects**

---

## Overview

This document provides step-by-step workflow specifications for all seven Compliance BI agents, the multi-agent orchestration pattern, the Tool Registry, and the memory architecture. Each agent specification includes trigger conditions, execution steps, decision points, error handling, audit trail entries, and an example execution trace.

---

## Agent 1: Deviation Watcher Agent

**Agent ID:** `AGENT-DEV-WATCHER`
**Trigger Type:** Scheduled (runs every 30 minutes) + Event-triggered (on new deviation record insert)
**Autonomy Level:** Level 1 — Monitor & Alert only. No records created without human approval.

### Workflow

```
1. TRIGGER
   └── Cron: every 30 minutes
   └── Event: new deviation_records row detected (via data polling)

2. FETCH RECENT DEVIATIONS
   └── Query: deviation_records WHERE detection_date >= NOW() - 72 hours
   └── Include severity, site_id, deviation_category, batch_id, capa_id, status

3. APPLY PATTERN RULES (run all in parallel)
   ├── Rule DEV-001: Critical deviation with no linked CAPA after 48 hours
   │   └── deviation_records WHERE severity='Critical' AND capa_id IS NULL
   │       AND detection_date < NOW() - 48h
   │
   ├── Rule DEV-002: Frequency spike at a single site (30% week-on-week increase)
   │   └── Compare this week's count vs last week per site
   │   └── Flag if ratio > 1.30 for any site
   │
   ├── Rule DEV-003: Same root_cause_category at same site, 3+ times in 30 days
   │   └── Count by (site_id, root_cause_category) WHERE detection_date >= NOW()-30d
   │   └── Flag if count >= 3
   │
   └── Rule DEV-004: Batch disposition impact with no quality disposition review
       └── deviation_records WHERE batch_disposition_impact != 'None'
           AND status NOT IN ('Closed', 'Under Disposition Review')
           AND detection_date < NOW() - 24h

4. EVALUATE FINDINGS
   └── For each rule that fired, collect:
       ├── Rule ID and description
       ├── Supporting deviation IDs (evidence)
       ├── Regulatory reference (21 CFR 211.192, etc.)
       └── Recommended immediate action

5. DECISION POINT: Any rules fired?
   ├── NO → Log "no patterns detected" to audit trail. Exit.
   └── YES → Continue to step 6

6. GENERATE ALERT PACKAGE
   └── LLM call: Synthesize findings into structured alert
       ├── Executive summary (2 sentences)
       ├── Rule-by-rule findings with evidence
       ├── Risk assessment (what could go wrong if not acted on)
       └── Recommended immediate actions (numbered list)

7. HUMAN NOTIFICATION
   └── Create alert record in notifications queue
   └── Notify: Site Quality Manager (if site-specific alert)
   └── Notify: QA Director (if 2+ rules fire simultaneously)
   └── Include link to pre-filtered chatbot query showing the deviations

8. DECISION POINT: Human reviews alert
   ├── Acknowledged + Action taken → Log resolution
   ├── Acknowledged + No action needed → Log with reason (false positive)
   └── No response in 4 hours (Critical alert) → Escalate to next tier

9. AUDIT TRAIL WRITE (every run)
   └── agent_id, run_timestamp, rules_evaluated, rules_fired,
       alert_generated (bool), notifications_sent, human_response
```

### Tools Used
- `execute_query("deviations.trend_monthly")` — baseline frequency data
- `execute_query("deviations.by_site")` — site-level aggregation
- Custom rule evaluation queries (ad hoc SQL via `get_conn()`)
- Groq API — alert narrative generation
- Notification service — in-app alert + email

### Decision Points Requiring Human Input
- **Step 8:** Human must acknowledge or dismiss every alert. Unacknowledged Critical alerts auto-escalate after 4 hours.

### Success / Failure Handling
- **Success:** Alert generated, human notified, acknowledgment logged.
- **Groq API failure:** Alert generated in structured text format without LLM narrative. Logged as partial success.
- **Data query failure:** Agent logs error and exits. Alert: "Deviation monitoring run failed — data unavailable." Sent to platform admin.

### Audit Trail Entries
```json
{
  "event": "AGENT_RUN",
  "agent_id": "AGENT-DEV-WATCHER",
  "run_id": "RUN-2026-04-03-0930",
  "timestamp": "2026-04-03T09:30:00Z",
  "rules_evaluated": 4,
  "rules_fired": ["DEV-001", "DEV-003"],
  "deviations_in_scope": 23,
  "alert_generated": true,
  "notifications_sent": ["qm@site-eu-02.com", "qa-director@company.com"],
  "data_quality_issues": null
}
```

### Example Execution Trace
```
09:30:00 [AGENT-DEV-WATCHER] Run started. Fetching deviations from last 72 hours.
09:30:01 [AGENT-DEV-WATCHER] Retrieved 23 deviation records.
09:30:01 [AGENT-DEV-WATCHER] Evaluating Rule DEV-001: Critical deviations without CAPA...
09:30:01 [AGENT-DEV-WATCHER] DEV-001 FIRED: DEV-2026-0847 (Critical, Equipment) at SITE-EU-02
           detected 52h ago, no CAPA linked.
09:30:01 [AGENT-DEV-WATCHER] Evaluating Rule DEV-002: Frequency spike...
09:30:01 [AGENT-DEV-WATCHER] DEV-002: SITE-US-01 this week: 14, last week: 9 → ratio 1.56. FIRED.
09:30:02 [AGENT-DEV-WATCHER] DEV-003 evaluated: no clusters found.
09:30:02 [AGENT-DEV-WATCHER] DEV-004 evaluated: no batch disposition gaps.
09:30:02 [AGENT-DEV-WATCHER] 2 rules fired. Generating alert narrative via Groq...
09:30:03 [AGENT-DEV-WATCHER] Alert narrative generated (487 chars).
09:30:03 [AGENT-DEV-WATCHER] Creating notification for site-eu-02 QM + QA Director.
09:30:03 [AGENT-DEV-WATCHER] Audit entry written. Run complete.
```

---

## Agent 2: CAPA Auto-Drafter Agent

**Agent ID:** `AGENT-CAPA-DRAFT`
**Trigger Type:** Event-triggered — when a new deviation record transitions to status `Investigation Complete` with `capa_required = true`, or when manually triggered by a QA user.
**Autonomy Level:** Level 2 — Draft and recommend. Human approval required before any CAPA record is created.

### Workflow

```
1. TRIGGER
   └── Event: deviation_records.status changes to 'Investigation Complete'
             AND investigation_required = true AND capa_id IS NULL
   └── OR: QA user manually triggers via API: POST /agents/capa-drafter/trigger
       with deviation_id

2. FETCH DEVIATION CONTEXT
   └── Retrieve full deviation record: deviation_id, site_id, dept_id,
       severity, description, root_cause_category, root_cause_description,
       batch_id, product_id, equipment_id
   └── Fetch linked batch record (if batch_id present)
   └── Fetch linked product record

3. SEARCH HISTORICAL CAPAs (precedent lookup)
   └── Query capa_records WHERE root_cause_category = THIS.root_cause_category
       AND site_id = THIS.site_id AND status = 'Closed'
       ORDER BY actual_close_date DESC LIMIT 5
   └── For each precedent: note what corrective actions were taken and
       effectiveness_check_result

4. RETRIEVE APPLICABLE SOP TEMPLATE
   └── Query documents WHERE doc_type = 'SOP' AND business_function = 'CAPA'
       AND status = 'Effective' AND site_id = THIS.site_id
   └── If no site-specific SOP, use enterprise CAPA SOP

5. APPLY POLICY RULES
   └── Policy Engine check: what are the required elements for a CAPA
       of this severity?
       ├── Critical: target_close_date <= 30 days, regulatory_notif assessment required
       ├── Major: target_close_date <= 60 days, effectiveness check required
       └── Minor: target_close_date <= 90 days

6. DRAFT CAPA STRUCTURE (LLM call)
   └── System prompt: Pharma CAPA writing expert, 21 CFR 820.100, ICH Q10 3.2.3
   └── Input: deviation record + root cause + precedent actions + SOP template
   └── Output:
       ├── capa_title (concise, action-oriented)
       ├── source_type = "Deviation"
       ├── source_reference_id = deviation_id
       ├── severity (inherited)
       ├── root_cause_category (inherited)
       ├── root_cause_detail (expanded from investigation summary)
       ├── description (full CAPA problem statement)
       ├── recommended target_close_date (per policy)
       ├── effectiveness_check_req (per severity policy)
       ├── proposed_action_items (list of 3-5 items, each with type, description,
           suggested_owner_role, suggested_due_date)
       └── regulatory_notif_required (policy-derived)

7. QUALITY CHECK
   └── Policy engine validates draft:
       ├── All required fields present?
       ├── Target close date within policy limits?
       ├── At least 1 corrective AND 1 preventive action item?
       ├── Effectiveness check set if severity >= Major?
       └── Description does not include vague language (e.g., "retrain as needed")?

8. DECISION POINT: Quality check passes?
   ├── YES → Present draft to CAPA Owner for review
   └── NO → Revise draft (LLM re-generation with quality feedback), max 2 retries

9. PRESENT TO HUMAN
   └── Display draft in approval UI:
       ├── Side-by-side: AI draft vs blank template
       ├── Precedent actions panel (what worked before)
       ├── Policy compliance indicators (all green)
       └── Accept / Edit / Reject buttons

10. HUMAN DECISION
    ├── Accept → Create capa_record in system (human's identity as initiated_by)
    ├── Edit → Human modifies draft → Accept → Create
    └── Reject → Log rejection reason, no record created

11. AUDIT TRAIL WRITE
    └── All steps logged including: draft quality score, human decision,
        edit summary (if any), final record ID created
```

### Tools Used
- `execute_query("capa.overdue_list")` — precedent lookup base
- Custom precedent query (filtered by root cause + site)
- Policy Engine: CAPA rule set evaluation
- Groq API: CAPA draft generation
- Document search: applicable SOP retrieval

### Decision Points Requiring Human Input
- **Step 9/10:** Human must explicitly Accept, Edit, or Reject the draft. No CAPA is created without this step.

### Audit Trail Entries
```json
{
  "event": "CAPA_DRAFT_GENERATED",
  "agent_id": "AGENT-CAPA-DRAFT",
  "triggered_by": "DEV-2026-0847",
  "draft_id": "DRAFT-CAPA-20260403-001",
  "precedents_found": 3,
  "policy_check": "PASS",
  "quality_score": 0.91,
  "presented_to": "john.smith@site-eu-02.com",
  "human_decision": "ACCEPT_WITH_EDITS",
  "edit_summary": "Adjusted target close date from 45 to 30 days per site policy",
  "capa_created": "CAPA-2026-0112",
  "timestamp": "2026-04-03T10:45:00Z"
}
```

---

## Agent 3: QMR Report Generator Agent

**Agent ID:** `AGENT-QMR-GEN`
**Trigger Type:** Scheduled (monthly, 5 business days before QMR date) + On-demand (QA Director trigger)
**Autonomy Level:** Level 2 — Generates complete draft package. Human review and approval required before distribution.

### Workflow

```
1. TRIGGER
   └── Scheduled: 5 business days before configured QMR date
   └── On-demand: QA Director clicks "Generate QMR Draft"

2. DETERMINE REPORTING PERIOD
   └── Default: prior calendar month (or quarter for quarterly QMR)
   └── Allow override via trigger parameters

3. EXECUTE DATA COLLECTION (parallel queries)
   ├── capa.summary_kpi (current period + prior period for trend)
   ├── deviations.by_site + deviations.trend_monthly
   ├── audit_findings.by_site + repeat finding rate
   ├── training.by_site (compliance rates by site/dept)
   ├── supplier_quality.scorecard (top 10 suppliers by risk)
   ├── risk.top_risks (top 20 by residual RPN)
   ├── regulatory.open_commitments (all overdue)
   ├── batches.by_site (rejection rates)
   └── Prior period comparative data for all domains

4. GENERATE SECTION NARRATIVES (LLM call per section)
   ├── Executive Summary (key metrics vs targets, top 3 concerns, management actions needed)
   ├── CAPA System Performance (on-time closure trend, overdue analysis, by-site breakdown)
   ├── Deviation Management (trend, severity breakdown, root cause Pareto, batch impact)
   ├── Audit Management (findings by site and process area, repeat finding analysis)
   ├── Training Compliance (compliance rates, overdue analysis, risk population)
   ├── Supplier Quality (scorecard, risk-rated suppliers, rejections analysis)
   ├── Risk Management (register health, unacceptable risks, ICH Q9 compliance)
   ├── Regulatory Commitments (open items, overdue items, upcoming deadlines)
   └── Management Actions (carryover actions from prior QMR + new recommended actions)

5. GENERATE VISUALIZATIONS
   └── For each section: build Vega-Lite specs for the primary 2-3 charts
       ├── CAPA: trend line + on-time closure rate by site (bar)
       ├── Deviations: trend line with severity breakdown
       ├── Training: compliance rate by site (horizontal bar, RAG colored)
       └── Suppliers: rejection rate ranking (horizontal bar)

6. ASSEMBLE QMR DOCUMENT STRUCTURE
   └── Title page with reporting period, sites in scope, preparer (agent)
   └── Table of contents
   └── Section pages (narrative + charts + data tables)
   └── Appendix: methodology, data sources, definitions

7. POLICY ENGINE VALIDATION
   └── Check: Does QMR include all ICH Q10 §2.5 required elements?
       ├── Product quality review status ✓
       ├── CAPA effectiveness review ✓
       ├── Prior management actions follow-up ✓
       └── Resource adequacy assessment ✓

8. PRESENT TO QA DIRECTOR
   └── Draft available in the platform as downloadable document
   └── Chatbot notification: "Your Q1 2026 QMR draft is ready for review"
   └── Human reviews, edits as needed, approves for distribution

9. AUDIT TRAIL WRITE
   └── Generation timestamp, data queries executed, sections generated,
       human reviewer, approval timestamp, distribution list
```

---

## Agent 4: Inspection Readiness Agent

**Agent ID:** `AGENT-INSP-READY`
**Trigger Type:** Scheduled (weekly score update) + On-demand + Event-triggered (when inspection announced)
**Autonomy Level:** Level 1 (continuous scoring) / Level 2 (pre-inspection briefing package)

### Workflow

```
1. WEEKLY SCORE CALCULATION
   └── Execute 8 domain health queries (parallel)
   └── Calculate weighted Inspection Readiness Score:
       ├── CAPA Health (25%): on_time_closure_rate, overdue_rate, critical_open
       ├── Training Compliance (20%): compliance_rate across all GMP roles
       ├── Deviation Management (15%): critical_rate, investigation_timeliness
       ├── Audit Findings (15%): repeat_finding_rate, response_acceptance_rate
       ├── Regulatory Commitments (15%): overdue_commitment_count
       ├── Document Currency (5%): expired_document_rate
       ├── Risk Register (5%): unacceptable_risk_count
       └── Overall score: weighted sum, 0-100 scale

2. SCORE INTERPRETATION
   ├── 90-100: Green — Inspection Ready
   ├── 75-89: Amber — Minor remediation needed
   ├── 60-74: Yellow — Significant gaps, action required
   └── <60: Red — Not inspection ready — immediate escalation

3. GENERATE ACTION LIST
   └── For each domain scoring below target:
       ├── Identify specific items driving the gap
       ├── Estimate score impact of resolving each item
       └── Prioritize by score impact × urgency

4. PRE-INSPECTION BRIEFING (when inspection < 14 days away)
   └── Fetch last 3 inspection reports for this site and authority
   └── Identify patterns in prior observations
   └── Generate likely question areas based on current compliance landscape
   └── Draft pre-inspection action plan with 30/14/7/1-day milestones
   └── Assemble back-room document index (list of documents inspectors typically request)

5. DELIVER SCORE AND BRIEFING
   └── Available via chatbot: "Are we inspection ready?"
   └── Weekly summary email to site Quality Directors
   └── Pre-inspection package: delivered to QA Director and Site Head

6. AUDIT TRAIL
   └── Score calculation timestamp, component scores, overall score,
       action list generated, briefing package generated
```

---

## Agent 5: Supplier Risk Monitor Agent

**Agent ID:** `AGENT-SUPPLIER-RISK`
**Trigger Type:** Scheduled (weekly) + Event-triggered (on new supplier inspection failure)
**Autonomy Level:** Level 1 — Monitor, score, and alert. No supplier status changes without human approval.

### Workflow

```
1. WEEKLY SUPPLIER QUALITY RUN
   └── Fetch all suppliers with is_gmp_critical = true or risk_rating = 'High'

2. FOR EACH SUPPLIER: CALCULATE ROLLING METRICS
   ├── 90-day rejection rate (current vs prior 90-day period)
   ├── CoA compliance rate trend
   ├── Days since last audit
   ├── Days until requalification due
   └── Open CAPA count + average CAPA age

3. TREND ANALYSIS
   └── For each supplier: is rejection rate trending up?
   └── Calculate 12-week moving average rejection rate
   └── Flag if: current_rate > 1.5 × prior_12w_average
   └── Flag if: requalification_due_dt < NOW() + 60 days

4. RISK TIER ASSIGNMENT (per supplier)
   ├── Tier 1 (Immediate Action): rejection_rate > 5% OR qualification_status = 'Suspended'
   ├── Tier 2 (Watch): rejection_rate 2-5% OR worsening trend detected
   └── Tier 3 (Monitor): rejection_rate <2% AND stable trend

5. GENERATE WEEKLY SUPPLIER RISK DIGEST
   └── Tier 1 suppliers: full detail + recommended actions (suspend, urgent audit, CAPA review)
   └── Tier 2 suppliers: trend data + watch recommendations
   └── New failures since last run: individual event summaries

6. HUMAN NOTIFICATION
   └── Digest sent to Supplier Quality team lead
   └── Tier 1 items: immediate notification to Procurement + QA Director

7. DECISION POINT: Tier 1 supplier
   └── Human reviews and decides: Suspend? Emergency audit? Accept risk?
   └── Agent presents options with policy implications for each choice
```

---

## Agent 6: Training Cascade Agent

**Agent ID:** `AGENT-TRAIN-CASCADE`
**Trigger Type:** Event-triggered — document revision approved (detected via documents table status change to 'Effective' with new version number)
**Autonomy Level:** Level 3 — Generates training assignments + executes after manager approval.

### Workflow

```
1. TRIGGER
   └── documents table: status changes to 'Effective' AND current_version != prior_version
   └── Extract: doc_id, doc_type, business_function, gxp_classification, site_id

2. DETERMINE TRAINING URGENCY (from change request)
   └── Look up linked change_requests record for this document version
   └── change_type mapping:
       ├── Critical / Emergency → due_date = NOW() + 7 days
       ├── Major → due_date = NOW() + 14 days
       └── Minor → due_date = NOW() + 30 days
   └── If no linked change request → default to Major (14 days)

3. IDENTIFY AFFECTED ROLES
   └── Query training_curricula WHERE doc_id = THIS.doc_id AND is_active = true
   └── Get list of role_ids that require training on this document

4. IDENTIFY AFFECTED EMPLOYEES
   └── Query employees WHERE role_id IN (affected_roles)
       AND is_active = true
       AND (site_id = doc.site_id OR doc.site_id IS NULL)  // global docs: all sites

5. GENERATE TRAINING ASSIGNMENT RECORDS (draft — not yet inserted)
   └── For each affected employee:
       ├── employee_id, doc_id, training_type = 'Change-Driven'
       ├── delivery_method = infer from doc_type (SOP → Read-and-Understand,
           Protocol → Classroom, Form → Read-and-Understand)
       ├── assigned_date = TODAY
       ├── due_date = calculated above
       └── status = 'Assigned'

6. POLICY CHECK
   └── Verify: employee is active, not on leave, role matches curriculum
   └── Flag any employees with pre-existing overdue training on this document

7. PRESENT ASSIGNMENT LIST TO MANAGER
   └── Group by department
   └── Show: employee count, due date, training type, delivery method
   └── Manager can: approve all, exclude individuals (with reason), adjust due dates

8. DECISION POINT: Manager approves
   ├── YES → Execute: insert training_records rows
   ├── PARTIAL → Insert approved subset, log exclusions
   └── NO → Log rejection with reason, no records created

9. POST-ASSIGNMENT MONITORING
   └── At due_date - 7 days: send reminder to employees not yet completed
   └── At due_date: flag overdue employees to department manager
   └── At due_date + 14 days: escalate to site Quality Director

10. AUDIT TRAIL
    └── Document ID, version, trigger timestamp, roles identified, employees in scope,
        assignments generated, manager approval event, assignment execution timestamp,
        completion tracking events
```

---

## Agent 7: Multi-Hop Root Cause Investigator

**Agent ID:** `AGENT-RCA-INVESTIGATOR`
**Trigger Type:** Manual trigger by QA investigator. Required: `deviation_id` or `capa_id`.
**Autonomy Level:** Level 2 — Generates investigation package. Human investigators direct and conclude.

### Workflow

```
1. TRIGGER
   └── QA investigator clicks "Launch AI Investigation" on deviation/CAPA record
   └── Input: deviation_id (primary) or capa_id

2. FETCH PRIMARY RECORD
   └── Full deviation record: description, severity, category, batch_id,
       product_id, equipment_id, shift, manufacturing_area, detection_date

3. HOP 1: BATCH RECORD INVESTIGATION
   └── If batch_id present:
       ├── Fetch full batch record
       ├── Fetch all deviations linked to this batch
       ├── Fetch all batch quality events in same manufacturing line ±30 days
       └── Finding: "3 deviations on this line in 30 days — possible systemic equipment issue"

4. HOP 2: EQUIPMENT INVESTIGATION
   └── If equipment_id present:
       ├── Fetch equipment record: qualification_status, last_qual_date, next_qual_date
       ├── Fetch all deviations citing this equipment_id in past 12 months
       ├── Flag if next_qual_date < detection_date (was equipment overdue for qualification?)
       └── Finding: "Equipment EQP-2047 was 23 days overdue for qualification at time of event"

3. HOP 3: PERSONNEL / TRAINING INVESTIGATION
   └── If detected_by employee identified:
       ├── Fetch employee's training records for the applicable SOP (doc linked to this process area)
       ├── Check: was training completed? Was it within 12 months?
       ├── Check: are there other employees in same department with same SOP overdue?
       └── Finding: "Operator's last training on SOP-MFG-042 was 14 months ago (beyond 12-month refresh)"

4. HOP 4: ENVIRONMENTAL / PROCESS INVESTIGATION
   └── Query deviation_records WHERE manufacturing_area = THIS.manufacturing_area
       AND detection_date >= THIS.detection_date - 90 days
       GROUP BY deviation_category, root_cause_category
   └── Identify if there is a pattern in the area prior to this event
   └── Finding: "7 equipment-category deviations in this area in 90 days vs. 2 in prior period"

5. HOP 5: SUPPLIER / MATERIAL INVESTIGATION
   └── If product_id and batch_id known:
       ├── Identify materials in this batch (batch records → materials)
       ├── Fetch supplier inspection records for those materials
       ├── Check for recent failures or complaints for same material lots
       └── Finding: "API lot used in this batch had CoA non-compliance flag from same supplier"

6. HOP 6: RISK REGISTER CROSS-REFERENCE
   └── Query risk_register WHERE site_id = THIS.site_id
       AND (business_process LIKE '%equipment%' OR risk_category = 'Process')
       AND status = 'Active'
   └── Find any pre-existing risk items that predicted this type of failure
   └── Finding: "Risk RSK-0089 (Tablet Press calibration gap) was flagged 6 months ago with
               residual_rpn=144 — this event may be the materialization of that risk"

7. SYNTHESIZE INVESTIGATION SUMMARY (LLM call)
   └── Input: all hop findings + original deviation
   └── Output:
       ├── Investigation summary (what was found at each evidence hop)
       ├── Probable root cause(s) ranked by supporting evidence strength
       ├── Contributing factors identified
       ├── Related risks in risk register
       ├── Recommended investigation next steps (what the human investigator should verify)
       └── Recommended CAPA scope (at minimum)

8. PRESENT TO INVESTIGATOR
   └── Structured investigation package in chat interface
   └── Each finding linked to source data (clickable)
   └── Investigator reviews, accepts/rejects each finding, adds their conclusions
   └── Final root cause is determined by the human investigator (not the agent)

9. AUDIT TRAIL
   └── Hops executed, data sources accessed, findings generated, LLM call details,
       investigator review event, human-determined root cause
```

### Example Execution Trace

```
10:00:00 [AGENT-RCA-INVESTIGATOR] Triggered for DEV-2026-0847 (Critical, Equipment, SITE-EU-02)
10:00:01 [HOP-1-BATCH] Fetched batch BATCH-2026-1847. Found 2 other deviations on same line in 30d.
10:00:01 [HOP-2-EQUIPMENT] Equipment EQP-2047: next_qual_date was 2026-02-10.
          Event detected 2026-03-15. Equipment was 33 days overdue for qualification.
          Found 4 prior deviations citing EQP-2047 in 12 months. STRONG SIGNAL.
10:00:02 [HOP-3-TRAINING] Detected_by employee EMP-0342.
          SOP-MFG-042 training last completed: 2024-11-15 (16 months ago, beyond 12-month refresh).
          3 other operators in same team also have expired training on same SOP. MODERATE SIGNAL.
10:00:02 [HOP-4-PROCESS] Manufacturing area AREA-B2: 9 equipment deviations in 90 days vs 3 prior.
          Statistically elevated frequency. MODERATE SIGNAL.
10:00:03 [HOP-5-MATERIALS] API lot LOT-2847: CoA compliant. No material concerns identified.
10:00:03 [HOP-6-RISK] Found RSK-0089: "Tablet Press preventive maintenance gap" — residual_rpn=144,
          Unacceptable. Last reviewed 8 months ago. CONFIRMING SIGNAL.
10:00:04 [LLM] Generating synthesis narrative...
10:00:05 [LLM] Synthesis complete.
          Primary root cause candidate: Equipment qualification overdue (strong evidence: 4 signals)
          Contributing factor: Training currency gap (moderate evidence: 2 signals)
          Pre-existing risk: RSK-0089 (confirming — risk materialized)
10:00:05 [AGENT-RCA-INVESTIGATOR] Investigation package assembled. Presenting to EMP-0891.
10:00:05 [AUDIT] Investigation complete. 6 hops, 7 data sources, 5 findings. Human review pending.
```

---

## Multi-Agent Orchestration Pattern

### Agent Coordination

Agents in Compliance BI operate primarily as independent workers, but certain scenarios require coordination. The coordination model is event-based:

```
DEVIATION EVENT (new critical deviation)
         │
         ├──► DEVIATION WATCHER AGENT
         │    └── Fires alert: "Critical deviation, no CAPA in 48h"
         │
         ├──► CAPA AUTO-DRAFTER AGENT (triggered by alert from watcher)
         │    └── Begins CAPA draft for the specific deviation
         │
         └──► ROOT CAUSE INVESTIGATOR AGENT (triggered manually by QA investigator)
              └── Begins investigation, may inform CAPA drafter's root cause input
```

```
DOCUMENT REVISION EVENT (SOP approved in new version)
         │
         └──► TRAINING CASCADE AGENT
              └── Identifies affected employees, generates assignments
              └── Triggers DEVIATION WATCHER to note: "SOP recently changed —
                  watch for compliance lag deviations in this area"
```

### Orchestrator Pattern (for future multi-step workflows)

For Phase 3, a lightweight orchestrator will manage multi-agent workflows:

```python
class ComplianceOrchestrator:
    def handle_critical_deviation(self, deviation_id: str):
        # Step 1: Gather evidence
        rca_findings = RCAInvestigatorAgent.run(deviation_id)
        
        # Step 2: Draft CAPA using RCA findings
        capa_draft = CAPADrafterAgent.run(deviation_id, rca_findings=rca_findings)
        
        # Step 3: Check inspection readiness impact
        readiness_delta = InspectionReadinessAgent.score_delta(deviation_id)
        
        # Step 4: Present unified package to QA
        return UnifiedReviewPackage(rca=rca_findings, capa=capa_draft,
                                    readiness_impact=readiness_delta)
```

---

## Tool Registry

The Tool Registry is a catalog of all capabilities available to agents. Each agent declares which tools it uses; the orchestrator resolves tool availability.

| Tool ID | Tool Name | Description | Used By |
|---|---|---|---|
| `TOOL-QUERY-001` | execute_named_query | Execute a named SQL query from QUERY_LIBRARY | All agents |
| `TOOL-QUERY-002` | execute_raw_sql | Execute ad-hoc SQL (agent-internal only, not user-facing) | RCA Investigator, Deviation Watcher |
| `TOOL-LLM-001` | groq_complete | Call Groq API for text generation | CAPA Drafter, QMR Generator, RCA Investigator |
| `TOOL-POLICY-001` | evaluate_policy_rules | Run Policy Engine rules against a record | CAPA Drafter, Training Cascade |
| `TOOL-NOTIFY-001` | send_notification | Create in-app notification + email | Deviation Watcher, Supplier Monitor, Training Cascade |
| `TOOL-RECORD-001` | create_training_assignment | Insert training_records row (after approval) | Training Cascade |
| `TOOL-SCORE-001` | calculate_readiness_score | Compute Inspection Readiness Score | Inspection Readiness |
| `TOOL-DOC-001` | fetch_document_metadata | Retrieve document record and curriculum links | Training Cascade, CAPA Drafter |
| `TOOL-AUDIT-001` | write_audit_trail | Append entry to immutable audit log | All agents (mandatory) |

**Tool access control:** Agents can only invoke tools in their declared tool list. TOOL-RECORD-001 (which writes to GMP systems) requires an active human approval token — it verifies a valid approval event exists before executing.

---

## Memory Architecture

### Turn-Level Memory (Chatbot)

Maintained by `session_manager.py`. Stores the last 5 conversation turns as LLM-digestible history. Used for follow-up intent resolution. Not persistent across server restarts.

### Agent Working Memory (Per-Run)

Each agent execution creates an ephemeral working memory object holding:
- Input parameters (deviation_id, etc.)
- Results of each tool call (hop findings, query results)
- Intermediate reasoning steps
- Draft outputs awaiting human approval

Working memory exists only for the duration of an agent run and the subsequent human review window. Not persisted after the run completes.

### Agent Long-Term Memory (Planned — Phase 3)

For Phase 3, agents will maintain long-term pattern memory:
- Deviation Watcher: rolling baseline statistics per site (for anomaly detection that adapts to seasonal patterns)
- CAPA Drafter: record of which prior CAPA templates were accepted with minimal edits vs heavily revised (to improve future drafts)
- Inspection Readiness: historical readiness score trends, correlation with actual inspection outcomes

Long-term memory will be stored in a vector database (pgvector or Chroma) for semantic search capability alongside structured statistics.

### Audit Trail (Permanent)

Distinct from working memory — the audit trail is a write-once, append-only log of all agent events. Never modified or deleted. Required for 21 CFR Part 11 compliance. Stored in a separate audit log store with cryptographic integrity protection.

---

*Architecture Lead: Compliance BI Platform Team | April 2026*
