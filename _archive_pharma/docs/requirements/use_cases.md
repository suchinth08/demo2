# Use Case Catalogue — Compliance BI Platform

**Document Type: Use Case Specification**
**Version: 1.0 | April 2026**
**Audience: Product, QA, Testing, Engineering**

---

## Format

Each use case follows this structure:
- **UC-ID:** Unique identifier
- **Title:** Short descriptive name
- **Actor:** Who initiates or is primarily involved
- **Preconditions:** What must be true before this use case executes
- **Main Flow:** Numbered steps of the primary success path
- **Alternative Flows:** What happens when things go differently
- **Postconditions:** What is true after successful completion
- **Business Value:** Why this matters
- **Related Requirements:** FR-IDs this use case validates

---

## Section 1: AI BI Chatbot Use Cases

### UC-001
**Title:** Query CAPA On-Time Closure Rate
**Actor:** Compliance Analyst / QA Director
**Preconditions:**
- User is authenticated and has a browser open to the Compliance BI UI
- capa_records.csv contains at least one closed CAPA record
- GROQ_API_KEY is configured

**Main Flow:**
1. User types: "What is our CAPA on-time closure rate?"
2. System calls /chat with the query and no session_id.
3. System creates a new session and calls extract_intent().
4. Groq model returns intent: `{intent: "METRIC_SNAPSHOT", domain: "capa", metrics: ["capa_on_time_closure_rate"], viz_type: "metric_card"}`.
5. System routes to query_key = "capa.summary_kpi".
6. DuckDB executes the KPI query and returns a single-row summary.
7. System generates a metric_card viz_spec with the on-time closure rate value.
8. Groq generates a narrative highlighting the rate, target comparison, and overdue count.
9. System returns response with session_id, metric card, narrative, and 3 follow-up suggestions.
10. UI renders the metric card and narrative. User sees the rate and the session is established.

**Alternative Flows:**
- A2: Groq API returns malformed JSON → system falls back to intent {domain: "capa", intent: "METRIC_SNAPSHOT"} and continues. Narrative is "Found N records for your query."
- A3: capa_records.csv missing → query returns empty list → narrative: "No data found. Try adjusting your filters."
- A4: User submits empty query → Pydantic validation rejects with HTTP 422.

**Postconditions:**
- New session created with session_id and turn_id = 1.
- User has seen the on-time closure rate and at least 3 follow-up options.
- Audit log entry written for this turn.

**Business Value:** Replaces a 30–45 minute manual data extraction with a 5-second answer. Enables daily monitoring without analyst effort.

**Related Requirements:** FR-001, FR-002, FR-004, FR-005, FR-008, FR-009

---

### UC-002
**Title:** CAPA Site Breakdown (Follow-Up)
**Actor:** Compliance Analyst
**Preconditions:**
- Session UC-001 has been completed (session_id exists with prior CAPA intent)

**Main Flow:**
1. User types: "Break it down by site" (follow-up in same session).
2. System calls /chat with query and existing session_id.
3. System retrieves existing session and prior intent.
4. `_looks_like_followup("Break it down by site")` → True.
5. `extract_intent()` called with FOLLOWUP_SYSTEM prompt + prior intent JSON.
6. Groq resolves follow-up: inherits domain=capa, metrics=capa_on_time_closure_rate, adds dimension=site_name.
7. System routes to "capa.by_site".
8. DuckDB returns one row per site with on-time closure rate and overdue count.
9. Viz builder generates horizontal_bar chart (sites ranked by overdue count).
10. Narrative highlights the underperforming site and compares it to best-performing site.
11. Response returned with same session_id, turn_id = 2.

**Alternative Flows:**
- A2: User says "by department" → dimension resolved to dept_name → routes to "capa.by_department".
- A3: User starts a completely new query (no follow-up signals) → treated as fresh intent, prior context not inherited.

**Postconditions:**
- Session now has 2 turns. Active context: domain=capa, dimension=site_name.
- User has site-level CAPA breakdown visible as interactive chart.

**Business Value:** Context threading enables natural exploration without re-asking context. Mirrors how a human analyst would naturally guide a conversation.

**Related Requirements:** FR-003, FR-006, FR-007

---

### UC-003
**Title:** Deviation Trend Analysis
**Actor:** QA Manager
**Preconditions:** deviation_records.csv populated with at least 12 months of data.

**Main Flow:**
1. User asks: "Show me deviation trend for last 12 months."
2. Intent extracted: `{intent: "TREND_ANALYSIS", domain: "deviations", time_filter: {type: "relative", value: "rolling 12 months"}, viz_type: "line_chart"}`.
3. System routes to "deviations.trend_monthly".
4. DuckDB returns monthly counts with critical/major breakdown.
5. Line chart spec generated with three series (total, critical, major) over time.
6. Narrative identifies trend direction, Q4 spike, and critical rate vs. target.
7. Follow-up: "Which site is driving the Q4 spike?"

**Postconditions:** User has 12-month trend chart. Session context carries rolling 12-month time filter for next follow-up.

**Business Value:** Replaces the deviation trend slide in monthly management review. Trend direction visible in seconds.

**Related Requirements:** FR-001, FR-002, FR-005, FR-007, FR-011

---

### UC-004
**Title:** Root Cause Pareto Analysis
**Actor:** Quality Engineer
**Preconditions:** deviation_records.csv populated with root_cause_category.

**Main Flow:**
1. User asks: "Show me the top root causes for deviations."
2. Intent: `{intent: "BREAKDOWN", domain: "deviations", dimensions: ["root_cause_category"], viz_type: "horizontal_bar"}`.
3. Routes to "deviations.pareto_root_cause".
4. Returns root cause categories with count, % of total, cumulative %.
5. Viz: horizontal_bar showing Pareto distribution with cumulative % line.
6. Narrative applies 80/20 analysis: "Equipment (34%) and Process (28%) account for 62% of deviations."

**Postconditions:** Pareto chart rendered. Root cause breakdown visible for action planning.

**Business Value:** Enables data-driven root cause focus for CAPA resources. Pareto principle applied automatically.

**Related Requirements:** FR-005, FR-007, FR-008

---

### UC-005
**Title:** Training Compliance Query
**Actor:** Training Manager / Site QA
**Preconditions:** training_records.csv and employees.csv populated.

**Main Flow:**
1. User asks: "What is our GMP training compliance rate by department?"
2. Intent: `{intent: "BREAKDOWN", domain: "training", dimensions: ["dept_name"], viz_type: "bar_chart"}`.
3. Routes to "training.by_department".
4. Returns compliance rate per department with overdue count.
5. Bar chart rendered with RAG coloring (green >98%, amber 95–98%, red <95%).
6. Narrative highlights lowest-performing department and overdue count.

**Postconditions:** Department-level training compliance visible. User can act on lowest performers.

**Business Value:** Training compliance is a leading indicator of CAPA risk. Immediate visibility enables proactive management before an inspection.

**Related Requirements:** FR-001, FR-005, FR-007

---

### UC-006
**Title:** Overdue Training List
**Actor:** Department Manager
**Preconditions:** training_records with status = 'Overdue' exist.

**Main Flow:**
1. User asks: "Show me all overdue training records for the QC department."
2. Intent: `{intent: "OVERDUE_ALERT", domain: "training", filters: [{field: "dept_name", op: "eq", value: "QC"}], viz_type: "table_with_rag"}`.
3. Routes to "training.overdue_list" with dept_name filter injected.
4. Returns employee list with days overdue.
5. RAG-colored table rendered. Red = >30 days overdue, Amber = 14–30, Green = 1–14.
6. Narrative: "14 overdue training records in QC, 3 employees each have 4+ overdue — highest risk individuals."

**Postconditions:** Actionable list of overdue employees available for follow-up.

**Business Value:** Enables targeted training follow-up rather than blanket reminders. Highest-risk individuals identified.

**Related Requirements:** FR-006, FR-007

---

### UC-007
**Title:** Supplier Quality Scorecard
**Actor:** Supplier Quality Engineer
**Preconditions:** supplier_inspections.csv and suppliers.csv populated.

**Main Flow:**
1. User asks: "Rank API suppliers by rejection rate."
2. Intent: `{intent: "RANKING", domain: "supplier_quality", metrics: ["supplier_rejection_rate"], filters: [{field: "supplier_type", op: "eq", value: "API"}], viz_type: "horizontal_bar"}`.
3. Routes to "supplier_quality.scorecard" with supplier_type=API filter.
4. Returns suppliers ranked by rejection_rate_pct.
5. Horizontal bar chart with reds color scheme.
6. Narrative highlights worst performer with trend note and open CAPA reference.

**Postconditions:** Supplier ranking visible. Highest-risk suppliers identified for action.

**Business Value:** Supply chain risk becomes visible on demand. Prevents surprise quality failures from unmonitored supplier degradation.

**Related Requirements:** FR-005, FR-006, FR-007, FR-008

---

### UC-008
**Title:** Audit Findings by Process Area
**Actor:** Internal Audit Manager
**Preconditions:** audit_findings.csv and audits.csv populated.

**Main Flow:**
1. User asks: "Show audit findings by process area."
2. Intent: `{intent: "BREAKDOWN", domain: "audit_findings", dimensions: ["process_area"], viz_type: "bar_chart"}`.
3. Routes to "audit_findings.by_process_area".
4. Returns top 10 process areas by finding count with critical and repeat counts.
5. Grouped bar chart rendered.
6. Narrative: "Document Control and Cleaning Validation have the most findings. Cleaning Validation has a 22% repeat finding rate — systemic gap in CAPA effectiveness."

**Postconditions:** Process area risk ranking visible. Audit focus areas identified for next audit cycle.

**Business Value:** Enables risk-based audit planning. Repeat findings surface as a leading indicator of systemic quality failures.

**Related Requirements:** FR-005, FR-007, FR-008

---

### UC-009
**Title:** Risk Matrix Query
**Actor:** Quality Risk Manager
**Preconditions:** risk_register.csv populated with severity and occurrence scores.

**Main Flow:**
1. User asks: "Show me the risk matrix."
2. Intent: `{intent: "RISK_ASSESSMENT", domain: "risk", viz_type: "risk_matrix"}`.
3. Routes to "risk.matrix".
4. Returns severity × occurrence grid with risk counts and average RPN.
5. ICH Q9 risk matrix visualization rendered with zone coloring.
6. Narrative: "12 risks in the high (red) zone. 3 are rated Unacceptable with no linked CAPA."

**Postconditions:** Risk landscape visible as ICH Q9 matrix. High-zone risks with no CAPA identified.

**Business Value:** ICH Q9 compliance visualization directly from live data. No manual risk matrix maintenance.

**Related Requirements:** FR-005, FR-007, FR-041

---

### UC-010
**Title:** Regulatory Inspection Readiness Check
**Actor:** QA Director / Site Head
**Preconditions:** All compliance data tables populated. Inspection Readiness Agent has computed current score.

**Main Flow:**
1. User asks: "Are we inspection ready for FDA?"
2. Intent: `{intent: "COMPLIANCE_SCORE", domain: "regulatory", viz_type: "radar_chart"}`.
3. System retrieves current Inspection Readiness Score from agent.
4. Radar chart rendered with 7 domain scores.
5. Narrative: "Composite readiness score is 76/100 (Amber). Key gaps: 18 overdue CAPAs, Frankfurt training at 88.4%, 4 overdue regulatory commitments."
6. Follow-up: "Show me the open regulatory commitments that are overdue."

**Postconditions:** Current inspection readiness score visible. Action items for improvement surfaced.

**Business Value:** Continuous inspection readiness visibility replaces the 3-week pre-inspection scramble.

**Related Requirements:** FR-030, FR-043

---

### UC-011
**Title:** Open Regulatory Commitments
**Actor:** Regulatory Affairs Manager
**Preconditions:** regulatory_commitments.csv with open/overdue records exists.

**Main Flow:**
1. User asks: "Show me overdue regulatory commitments."
2. Intent: `{intent: "OVERDUE_ALERT", domain: "regulatory", viz_type: "table_with_rag"}`.
3. Routes to "regulatory.open_commitments" with status filter.
4. Returns commitments with days overdue.
5. Table with RAG coloring. Red = >30 days overdue.
6. Narrative: "4 overdue regulatory commitments from March 2024 FDA inspection. RCOM-0012 (21 CFR 211.68) is 124 days overdue — immediate escalation required."

**Postconditions:** Overdue regulatory commitments visible with priority ordering.

**Business Value:** Legal obligations to FDA (483 response commitments) are surfaced before they escalate. FDA follow-up inspections are triggered by overdue commitments.

**Related Requirements:** FR-005, FR-007, FR-008

---

### UC-012
**Title:** Batch Rejection Rate by Site
**Actor:** Manufacturing Quality Manager
**Preconditions:** batch_records.csv populated.

**Main Flow:**
1. User asks: "Which site has the highest batch rejection rate?"
2. Intent: `{intent: "RANKING", domain: "batches", metrics: ["rejection_rate_pct"], dimensions: ["site_name"], viz_type: "horizontal_bar"}`.
3. Routes to "batches.by_site".
4. Returns sites ranked by rejection_rate_pct.
5. Horizontal bar with reds color gradient.
6. Narrative highlights the highest-rejection site and absolute count.

**Postconditions:** Batch quality ranking by site visible. Highest-rejection site identified for root cause analysis.

**Business Value:** Batch rejection rate directly impacts revenue and regulatory risk. Early detection enables process improvement before quality failures escalate.

**Related Requirements:** FR-005, FR-007

---

## Section 2: Policy as a Service Use Cases

### UC-013
**Title:** CAPA Timeliness Policy Violation Detection
**Actor:** Policy Engine (automated)
**Preconditions:** Policy Engine is running. POL-CAPA-001 (Critical CAPA ≤30 days) is active in registry.

**Main Flow:**
1. Policy Engine evaluation run triggered (scheduled, every hour).
2. Engine fetches all capa_records WHERE severity = 'Critical' AND actual_close_date IS NULL.
3. For each record, checks: CURRENT_DATE - initiation_date > 30 days.
4. Records meeting the condition generate a violation finding: `{policy_id: "POL-CAPA-001", severity: "Critical", evidence: {capa_id, initiation_date, age_days}, regulatory_ref: "21 CFR 820.100"}`.
5. Violation findings stored in violations log.
6. For each new Critical violation (not seen in prior run), notification sent to CAPA owner and QA Director.
7. Audit trail entry written.

**Alternative Flows:**
- A2: All Critical CAPAs are within 30 days → engine logs "0 violations for POL-CAPA-001." No notifications.
- A3: Policy Engine data query fails → engine logs error, skips rule, continues with remaining rules.

**Postconditions:** Violation log updated. Owners notified of overdue Critical CAPAs.

**Business Value:** CAPAs are the primary mechanism for responding to FDA 483 observations. Timeliness enforcement prevents escalation from Inspector observations to Warning Letters.

**Related Requirements:** FR-020, FR-021, FR-025

---

### UC-014
**Title:** Data Completeness Policy Check on Deviation Record
**Actor:** Policy Engine (event-triggered)
**Preconditions:** New deviation record inserted with missing root_cause_category.

**Main Flow:**
1. New deviation record created: `{deviation_id: "DEV-2026-0901", severity: "Major", root_cause_category: null, status: "Open"}`.
2. Policy Engine event trigger fires for new deviation_records row.
3. Engine evaluates POL-DG-003: deviation_records.root_cause_category must be populated before status = 'Closed'.
4. Engine evaluates POL-DG-001: severity and gmp_classification must be populated at creation.
5. POL-DG-001 fires: root_cause_category is null → generates Minor violation.
6. In-app notification to the record creator: "Data completeness issue on DEV-2026-0901: root_cause_category is required."
7. System does not block the record creation — advisory violation only at creation; enforcement at status transition.

**Postconditions:** Deviation record exists. Completeness violation logged. Creator notified.

**Business Value:** Data quality at source prevents the "garbage in, garbage out" problem that makes compliance metrics unreliable.

**Related Requirements:** FR-023, FR-025

---

### UC-015
**Title:** ICH Q9 Unacceptable Risk Without CAPA
**Actor:** Policy Engine (scheduled)
**Preconditions:** risk_register contains a record with risk_acceptance_status = 'Unacceptable' and linked_capa_id IS NULL.

**Main Flow:**
1. Policy Engine weekly risk register scan runs.
2. Engine evaluates ICH Q9 rule: risks rated Unacceptable must have a linked CAPA.
3. Rule fires for RSK-0089: residual_rpn = 144, risk_acceptance_status = 'Unacceptable', linked_capa_id = null.
4. Violation generated: `{policy_id: "POL-RISK-002", severity: "Major", regulatory_ref: "ICH Q9 §5"}`.
5. Notification to risk owner and QA Director: "Unacceptable risk RSK-0089 has no linked CAPA — ICH Q9 non-conformance."
6. Chatbot query "Show active ICH Q9 policy violations" returns this violation.

**Postconditions:** Risk owner is notified. Violation visible in compliance dashboard.

**Business Value:** ICH Q9 requires that unacceptable risks have risk reduction actions. Missing CAPA linkage is a direct ICH Q9 non-conformance that inspectors commonly cite.

**Related Requirements:** FR-024, FR-025

---

### UC-016
**Title:** Batch Release with Open Critical Deviation
**Actor:** Policy Engine (event-triggered)
**Preconditions:** batch_records contains a record where status transitions to 'Released' while an open critical deviation is linked to the same batch.

**Main Flow:**
1. batch_records.batch_status changes from 'In Process' to 'Released' for BATCH-2026-1847.
2. Policy Engine event trigger fires.
3. Engine checks POL-REL-001: any batch with an open Critical deviation and no linked closed CAPA must not be released.
4. Engine finds DEV-2026-0847 (Critical, open, linked to BATCH-2026-1847) with no closed CAPA.
5. Violation generated: `{policy_id: "POL-REL-001", severity: "Critical", regulatory_ref: "21 CFR 211.192"}`.
6. Notification to QA Director and Batch Release Specialist: "CRITICAL: BATCH-2026-1847 released with open critical deviation DEV-2026-0847 and no closed CAPA. Immediate review required."

**Postconditions:** Batch is technically released in the system (the engine is advisory in Phase 1). Critical violation logged. QA Director notified immediately.

**Business Value:** 21 CFR 211.192 requires batch record review before release. A released batch with an unaddressed critical deviation is a direct regulatory violation and potential patient safety risk.

**Related Requirements:** FR-020, FR-025

---

### UC-017
**Title:** Training Compliance Below Threshold Alert
**Actor:** Policy Engine (scheduled)
**Preconditions:** Training compliance calculation shows a site below the configured threshold (95%).

**Main Flow:**
1. Daily policy engine scan calculates training compliance rate per site.
2. SITE-EU-02 training compliance rate = 88.4%.
3. Policy rule POL-TRAIN-001 fires: compliance below 95% threshold for GMP site.
4. Violation generated with severity = Major.
5. Site Quality Manager for SITE-EU-02 notified.
6. Training Cascade Agent is optionally triggered to identify which documents need follow-up.

**Postconditions:** Site QM notified. Training gap visible in compliance dashboard.

**Business Value:** Training compliance is a leading indicator of compliance failures. Early warning enables management intervention before the situation reaches inspection.

**Related Requirements:** FR-019, FR-020, FR-025

---

### UC-018
**Title:** Change Control Regulatory Impact Assessment
**Actor:** Policy Engine (event-triggered)
**Preconditions:** A change_request record has regulatory_impact = true and regulatory_filing_required IS NULL.

**Main Flow:**
1. New change_request submitted: change_type = 'Major', regulatory_impact = true, regulatory_filing_required = null.
2. Policy Engine fires POL-CHG-001: changes with regulatory_impact = true must have regulatory_filing_required determined within 5 business days.
3. Notification to Regulatory Affairs team: "Change CC-2026-0234 has regulatory impact flag — filing requirement must be assessed within 5 business days per 21 CFR 314.70."
4. If 5 days elapse with no update, escalate to Head of Regulatory Affairs.

**Postconditions:** Regulatory Affairs team is aware of pending assessment obligation.

**Business Value:** Unassessed regulatory impact on changes is a common source of CMC submission failures. Early notification prevents surprise CBE-30 or PAS filing obligations.

**Related Requirements:** FR-019, FR-020, FR-025

---

### UC-019
**Title:** Policy Registry Query via Chatbot
**Actor:** Compliance Officer
**Preconditions:** Policy Registry is populated. User has chatbot access.

**Main Flow:**
1. User asks: "What CAPA-related policies are currently active?"
2. Intent: `{intent: "REGULATORY_STATUS", domain: "capa", viz_type: "data_table"}`.
3. System queries Policy Registry for all active rules with domain = 'capa'.
4. Returns table of policy rules with ID, title, regulatory ref, severity.
5. User clicks on a specific policy to see its full definition and recent violation history.

**Postconditions:** User has a complete view of currently enforced CAPA policies.

**Business Value:** Auditability of the compliance program. Inspectors can be shown which policies are active and when they last fired — demonstrating a functioning quality system.

**Related Requirements:** FR-019, FR-001

---

## Section 3: Agentic Compliance Use Cases

### UC-020
**Title:** Deviation Pattern Alert — No CAPA
**Actor:** Deviation Watcher Agent (automated)
**Preconditions:** AGENT-DEV-WATCHER is running. A Critical deviation older than 48 hours has no linked CAPA.

**Main Flow:**
1. Agent runs at 09:30 scheduled interval.
2. Agent queries: Critical deviations WHERE capa_id IS NULL AND detection_date < NOW() - 48h.
3. DEV-2026-0847 matches (53 hours old, no CAPA, Critical severity).
4. Agent generates alert narrative via Groq.
5. In-app notification and email sent to Site QM (SITE-EU-02) and QA Director.
6. Alert includes: deviation ID, site, severity, description, regulatory reference (21 CFR 820.100), recommended action (initiate CAPA within 24 hours).
7. CAPA Auto-Drafter Agent is triggered (linked event).
8. Audit trail entry written for this agent run.

**Alternative Flows:**
- A2: All Critical deviations have linked CAPAs → Rule DEV-001 does not fire. Log "0 violations." No notification.
- A3: Agent run fails (data query error) → Platform admin notified. No false-positive alert sent.

**Postconditions:** Site QM and QA Director are aware of the unmitigated Critical deviation within minutes. CAPA drafting has been initiated.

**Business Value:** Closes the 18–23 day lag between a compliance signal and management awareness. For a Critical deviation, this gap is a direct regulatory risk.

**Related Requirements:** FR-026, FR-034, FR-035

---

### UC-021
**Title:** Automated CAPA Draft Approval
**Actor:** CAPA Auto-Drafter Agent + QA Professional (approver)
**Preconditions:** DEV-2026-0847 investigation is complete. Root cause: Equipment qualification overdue. AGENT-CAPA-DRAFT is triggered.

**Main Flow:**
1. Agent fetches full deviation record including root cause description.
2. Agent searches for prior CAPAs with root_cause_category = 'Equipment' at SITE-EU-02.
3. Agent finds 3 precedents. Notes that CAPA-2025-0067 had effective corrective action (calibration schedule review) and passed effectiveness check.
4. Agent fetches CAPA SOP template for SITE-EU-02.
5. Agent calls Policy Engine: Critical CAPA requires target_close_date within 30 days.
6. Groq generates draft CAPA with: problem statement, root cause (equipment qualification overdue 33 days), corrective actions (immediate re-qualification, investigation of PM schedule failure), preventive actions (automated qualification overdue alert, quarterly PM audit), target close date 28 days out, effectiveness check required.
7. Policy check: all required fields present, date within 30-day limit → PASS.
8. Draft presented to CAPA Owner (John Smith) in approval UI.
9. John Smith reviews, adjusts one corrective action description, clicks "Accept."
10. capa_records row created with John's identity as initiated_by.
11. Audit entry: draft generated, edits made (summarized), approved by EMP-0342, CAPA-2026-0112 created.

**Alternative Flows:**
- A2: John Smith clicks "Reject" with reason → No CAPA created. Rejection logged. John proceeds with manual CAPA creation.
- A3: Policy check fails (target date too far out) → Agent revises draft automatically, resubmits for policy check.

**Postconditions:** CAPA-2026-0112 created in system. Linked to DEV-2026-0847. Audit trail complete.

**Business Value:** CAPA preparation time reduced from 2–4 hours to 15–20 minutes of review. CAPA quality improved by precedent lookup and policy enforcement.

**Related Requirements:** FR-027, FR-028, FR-034

---

### UC-022
**Title:** Training Cascade After SOP Revision
**Actor:** Training Cascade Agent (event-triggered) + Department Manager (approver)
**Preconditions:** SOP-MFG-042 has been approved in Rev 5. Prior version was Rev 4.

**Main Flow:**
1. documents table: SOP-MFG-042 status → 'Effective', version → 'Rev 5'.
2. Agent triggers within 1 hour.
3. Agent reads linked change_request: change_type = 'Major' → due date = 14 days.
4. Agent queries training_curricula: SOP-MFG-042 in curriculum for role_id = [12, 14, 15] (Manufacturing Operator, QC Analyst, Production Supervisor).
5. Agent queries employees: 47 employees with matching roles, active, at SITE-US-01.
6. Agent generates 47 training assignment records (draft): employee_id, doc_id=SOP-MFG-042, training_type='Change-Driven', delivery_method='Read-and-Understand', due_date=TODAY+14, status='Assigned'.
7. Assignment list presented to Manufacturing and QC department managers for approval.
8. Manufacturing Manager approves 31 records (Manufacturing Operators + Supervisors).
9. QC Manager approves 16 records (QC Analysts) with due_date extended to 21 days (manager override).
10. All 47 training_records rows inserted with managers' approval events logged.
11. Audit trail: doc revision detected, roles identified, employees in scope, approval events, records created.

**Alternative Flows:**
- A2: Employee is on leave → agent flags the employee for deferred assignment, manager confirms.
- A3: No training curriculum entry for this document → agent logs "No curriculum for SOP-MFG-042. Manual assignment may be required." Notifies Training Manager.

**Postconditions:** 47 training assignments created on the day of SOP approval. Prior 14-day lag eliminated.

**Business Value:** Eliminates the compliance gap between procedure change and confirmed employee awareness. Directly reduces the risk of deviations caused by outdated procedure knowledge.

**Related Requirements:** FR-029, FR-028, FR-034

---

### UC-023
**Title:** Pre-Inspection Readiness Briefing
**Actor:** Inspection Readiness Agent + QA Director
**Preconditions:** FDA inspection announced for SITE-EU-02 in 12 days. Agent has current readiness data.

**Main Flow:**
1. Inspection event logged in system (or QA Director triggers manually).
2. Inspection Readiness Agent triggered for SITE-EU-02, authority = FDA, days until inspection = 12.
3. Agent fetches current component scores: CAPA Health 71%, Training 88.4%, Deviations (critical rate 2.1%), Audit Findings (repeat rate 8%), Regulatory Commitments (2 overdue), Documents (3 expired), Risk (1 unacceptable).
4. Composite readiness score: 72/100 (Yellow — significant gaps).
5. Agent generates pre-inspection action plan:
   - Days 1–3: Close 2 overdue regulatory commitments (RCOM-0012, RCOM-0015)
   - Days 1–5: Address 3 expired SOPs (renew or retire)
   - Days 1–7: Resolve unacceptable risk RSK-0089 (link CAPA)
   - Days 1–12: Reduce CAPA overdue count from 12 to <5
6. Agent fetches prior FDA inspection reports for SITE-EU-02 (2 prior inspections).
7. Identifies likely focus areas based on prior observations: Computer System Validation, Cleaning Validation, Laboratory Controls.
8. Generates back-room document index (list of documents FDA typically requests for this inspection type).
9. Briefing package delivered to QA Director and Site Head.

**Postconditions:** Site team has a prioritized 12-day action plan. Likely inspector focus areas identified. Document readiness list prepared.

**Business Value:** Structured, data-driven pre-inspection preparation replaces the chaotic 3-week scramble. Expected outcome: 20–40% reduction in Form 483 observations.

**Related Requirements:** FR-030, FR-043

---

### UC-024
**Title:** Supplier Risk Escalation
**Actor:** Supplier Risk Monitor Agent + Supplier Quality Lead
**Preconditions:** Sigma API Solutions has increasing rejection rate over 10 months.

**Main Flow:**
1. Weekly supplier risk run executes.
2. Agent calculates Sigma's rolling metrics: current 90-day rejection rate = 3.8%, prior 90-day = 1.4% → ratio 2.71 → exceeds 1.5× threshold.
3. Sigma classified as Tier 1 (Immediate Action).
4. Agent retrieves: open CAPA for Sigma (CAPA-0087, 73 days overdue), qualification_status = 'Approved' (expiry approaching in 45 days).
5. Digest entry for Sigma: all metrics, trend chart data, CAPA status, qualification timeline.
6. Agent notifies Supplier Quality lead: "TIER 1 ALERT: Sigma API Solutions rejection rate has increased 2.7× over 90 days. Open CAPA is 73 days overdue. Qualification expires in 45 days. Recommended actions: (1) Escalate CAPA-0087, (2) Schedule emergency supplier audit, (3) Review AVL policy for suspension threshold."
7. Supplier Quality lead reviews and decides: initiate emergency supplier audit.
8. Decision logged in audit trail.

**Postconditions:** Supplier Quality lead has actionable intelligence. Escalation path is documented. Supply chain disruption risk management is active.

**Business Value:** Detects supplier quality degradation while still reversible. Prevents the supply chain disruption scenario of a sudden suspension without a qualified alternative.

**Related Requirements:** FR-033, FR-034

---

### UC-025
**Title:** Multi-Hop Root Cause Investigation
**Actor:** Root Cause Investigator Agent + QA Investigator
**Preconditions:** DEV-2026-0847 (Critical, Equipment, SITE-EU-02). QA investigator triggers agent.

**Main Flow:**
1. QA investigator clicks "Launch AI Investigation" on DEV-2026-0847.
2. Agent executes 6 hops in parallel (as detailed in Agent Workflow specification).
3. HOP-2 finds EQP-2047 was 33 days overdue for qualification at time of event. 4 prior deviations citing same equipment.
4. HOP-3 finds operator's SOP training is 16 months old (beyond 12-month refresh). 3 teammates also expired.
5. HOP-6 finds RSK-0089 (equipment PM gap, RPN=144, Unacceptable) in risk register — pre-existing risk.
6. Synthesis: Primary root cause candidate = Equipment qualification overdue (strong evidence: 3 signals). Contributing = Training currency gap. Pre-existing risk materialized.
7. Investigation package rendered in chat interface with each finding linked to source data.
8. QA investigator reviews each hop finding. Marks HOP-2 as "Confirmed root cause." Marks HOP-3 as "Contributing factor." Marks HOP-6 as "Risk materialization confirmed."
9. Investigator writes final root cause determination (agent's synthesis is the starting point).

**Postconditions:** Evidence-gathering phase complete in 4–5 minutes. Investigator has structured package ready for CAPA initiation. All evidence hops are documented and linked.

**Business Value:** Multi-day evidence gathering compressed to minutes. Investigation quality improved — no data sources missed. Standard investigation package for regulatory review.

**Related Requirements:** FR-032, FR-034

---

### UC-026
**Title:** QMR Report Generation
**Actor:** QMR Generator Agent + QA Director
**Preconditions:** End of Q1 2026. Agent is scheduled for 5 business days before QMR date.

**Main Flow:**
1. Scheduler triggers AGENT-QMR-GEN for Q1 2026 reporting period.
2. Agent executes 9 parallel data collection queries across all compliance domains.
3. Agent generates narrative sections for all 9 QMR topics using current quarter data vs. Q4 2025 comparative.
4. Visualizations generated for key charts (CAPA trend, training compliance by site, deviation trend).
5. Policy Engine validates QMR completeness against ICH Q10 §2.5 checklist — all elements present.
6. Draft QMR document assembled and delivered to QA Director's workspace.
7. QA Director reviews draft over 2–3 hours. Adds commentary on two sections. Updates management actions table.
8. QA Director approves draft for distribution to leadership team.
9. Distribution event logged in audit trail.

**Postconditions:** QMR draft completed in <5 minutes of agent execution. Human review and approval complete in 3 hours vs. prior 30–40 hour preparation effort.

**Business Value:** QMR preparation time reduced by 65–85%. QMR is data-accurate (from live queries) rather than relying on manually compiled data that may be 2–4 weeks stale.

**Related Requirements:** FR-031, FR-028, FR-034

---

*Use Case Lead: Compliance BI Platform Team | April 2026*
