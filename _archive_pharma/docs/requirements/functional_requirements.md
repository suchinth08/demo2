# Functional Requirements — Compliance BI Platform

**Document Type: Formal Requirements**
**Version: 1.0 | April 2026**
**Audience: Product, Engineering, QA**

---

## Requirement Format

Each requirement follows this structure:
- **ID:** Unique identifier (FR-XXX)
- **Title:** Short descriptive name
- **Description:** What the system must do
- **Priority:** Must (essential for launch) / Should (important but deferrable) / Could (desirable)
- **Feature:** AI BI Chatbot / Policy as a Service / Agentic Actions / Platform
- **Acceptance Criteria:** How to verify this requirement is met
- **Dependencies:** Other requirements this depends on

---

## Platform Requirements

### FR-001
**Title:** Natural Language Query Processing
**Description:** The system must accept natural language text queries about pharmaceutical compliance data and return structured results including data, visualization, and narrative.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- Given a valid English natural language query about any supported compliance domain, the /chat endpoint returns a 200 response with non-empty `data`, `narrative`, and `viz_spec` fields within 10 seconds.
- Queries about all 8 supported domains (CAPA, Deviations, Audit Findings, Training, Supplier Quality, Risk, Regulatory, Batches) return relevant results.
**Dependencies:** FR-002, FR-003

---

### FR-002
**Title:** Structured Intent Extraction
**Description:** The system must extract a structured JSON intent object from every natural language query, identifying: intent type, compliance domain, metrics, dimensions, time filters, record-level filters, sort preferences, and visualization type.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- Intent extraction succeeds (returns valid JSON with all required fields) for >92% of test queries in the validated query corpus.
- All 11 intent types (METRIC_SNAPSHOT, TREND_ANALYSIS, BREAKDOWN, RANKING, COMPARISON, ANOMALY_DETECTION, DRILL_DOWN, OVERDUE_ALERT, RISK_ASSESSMENT, COMPLIANCE_SCORE, REGULATORY_STATUS) are correctly identified.
- All 8 compliance domain synonyms (e.g., "non-conformance" → "deviations") are resolved correctly.
**Dependencies:** FR-014 (Groq API integration)

---

### FR-003
**Title:** Multi-Turn Conversation Context
**Description:** The system must maintain conversation context across multiple turns within a session, enabling follow-up questions that inherit domain, time filter, metrics, and record-level filters from prior turns.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- A follow-up question ("Now break it down by site") correctly inherits the domain, time filter, and metrics from the prior turn without restating them.
- Context inheritance is maintained for a minimum of 5 prior turns.
- A fresh question (clearly new domain or intent) is recognized as not a follow-up and treated as a new query.
**Dependencies:** FR-004, FR-002

---

### FR-004
**Title:** Session Management
**Description:** The system must create, store, and retrieve conversation sessions associated with a user ID. Sessions must persist for the duration of the server process and be retrievable by session ID.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- POST /chat with no session_id creates a new session and returns the session_id.
- POST /chat with an existing session_id retrieves and updates the existing session.
- GET /sessions returns all sessions for the specified user_id.
- GET /sessions/{id}/history returns all turns for that session.
**Dependencies:** None

---

### FR-005
**Title:** Query Library Execution
**Description:** The system must maintain a named query library covering all supported compliance domains and route intent objects to the appropriate query. Queries must execute against DuckDB and return results as a list of row dictionaries.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- All 22+ named queries in QUERY_LIBRARY execute without SQL errors against valid data.
- Query routing correctly maps (domain, intent_type) pairs to query keys for all supported combinations.
- Domain-level fallback ensures no intent results in a null query key.
- Query results are returned within 2 seconds for data volumes up to 100,000 rows.
**Dependencies:** FR-017 (DuckDB data layer)

---

### FR-006
**Title:** Dynamic Filter Injection
**Description:** The system must support injection of additional WHERE conditions into any named query based on filters extracted from the user's intent, without modifying the base query definition.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- String filter: `field = 'value'` correctly appended.
- List filter: `field IN ('v1', 'v2')` correctly appended.
- Range filter (`gte`): `field >= 'value'` correctly appended.
- Filters are appended to existing WHERE clause or inserted before GROUP BY/ORDER BY/LIMIT.
- Injection does not produce SQL syntax errors for any combination of base query + filter type.
**Dependencies:** FR-005

---

### FR-007
**Title:** Visualization Spec Generation
**Description:** The system must generate a complete, valid Vega-Lite v5 JSON specification for each query response, automatically selecting field encodings based on data types detected in the result set.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- All 13 visualization types produce valid Vega-Lite JSON that renders without errors in a browser.
- Time-series fields (containing "month", "quarter", "year", "date") are automatically encoded as temporal.
- Categorical fields are detected and used as x/y/color axes appropriately.
- Empty data returns a valid empty-state Vega-Lite spec (not an error).
**Dependencies:** FR-005

---

### FR-008
**Title:** AI-Generated Insight Narrative
**Description:** For every query returning data, the system must generate a 3–5 sentence natural language insight narrative that directly answers the user's question, highlights the key finding, flags compliance risks, and suggests a follow-up question.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- Narrative is generated for every response where `len(data) > 0`.
- Narrative references specific values from the query results (not generic text).
- Narrative ends with "Follow-up: [question]".
- If Groq API fails, a fallback narrative ("Found N records for your query") is returned without error.
**Dependencies:** FR-014

---

### FR-009
**Title:** Suggested Follow-Up Questions
**Description:** The system must generate 3 contextually relevant follow-up question suggestions for every response, based on the current domain, intent type, and data dimensions.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- Every ChatResponse includes a `suggested_followups` list with exactly 3 items.
- Follow-ups are domain-relevant (CAPA domain → CAPA-related suggestions).
- Follow-ups are intent-aware (trend queries → site breakdown suggestions; overdue alerts → detail drill-down suggestions).
- Default fallback follow-ups are returned if domain-specific mapping is absent.
**Dependencies:** FR-002

---

### FR-010
**Title:** Pharmaceutical Terminology Synonym Resolution
**Description:** The system must resolve pharmaceutical compliance domain synonyms to their canonical form, enabling queries using non-standard but industry-accepted terminology.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- "non-conformance", "NC", "discrepancy" → resolved to Deviation domain.
- "observation", "483", "citation" → resolved to AuditFinding domain.
- "procedure", "SOP", "controlled doc" → resolved to Document domain.
- "lot", "production batch" → resolved to Batch domain.
- "corrective action", "CA/PA" → resolved to CAPA domain.
- "RPN", "risk score", "criticality" → resolved to Risk domain.
**Dependencies:** FR-002

---

### FR-011
**Title:** Time Expression Parsing
**Description:** The system must correctly interpret natural language time expressions and convert them to structured date filter objects.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- "this year" → `{type: "relative", value: "year = current year"}`.
- "last year" → prior calendar year.
- "last 12 months" / "rolling 12 months" → trailing 12-month window from today.
- "YTD" → January 1 of current year to today.
- "last quarter" → prior fiscal quarter (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec).
- "last month" → prior calendar month.
**Dependencies:** FR-002

---

### FR-012
**Title:** Frontend UI — Chat Interface
**Description:** The system must serve a browser-based chat interface that displays conversation turns, renders Vega-Lite charts, displays data tables, shows suggested follow-ups as clickable buttons, and provides a text input field for new queries.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- Frontend loads from GET / without additional configuration.
- Chat messages (user and assistant) are displayed in chronological order.
- Vega-Lite specs in viz_spec field are rendered as interactive charts.
- Suggested follow-ups are displayed as clickable buttons that populate the input field.
- Input field accepts text and submits on Enter key or button click.
- Loading state is displayed while awaiting /chat response.
**Dependencies:** FR-001

---

### FR-013
**Title:** Example Query Catalog
**Description:** The system must provide a catalog of example queries organized by compliance domain, accessible via API and displayed in the UI for user onboarding.
**Priority:** Should
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- GET /example-queries returns a dictionary keyed by domain with at least 4 example queries per domain.
- All 8 supported domains are represented.
- Example queries are valid inputs to the /chat endpoint and return non-error responses.
**Dependencies:** FR-001

---

### FR-014
**Title:** Groq API Integration
**Description:** The system must integrate with the Groq API using the llama-3.3-70b-versatile model for intent extraction and narrative generation. API key must be loaded from environment variable. System must handle API failures gracefully.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- GROQ_API_KEY is read from environment variable (not hardcoded).
- Temperature is set to 0.1 for intent extraction (for consistency).
- API failures (network error, rate limit) are caught and result in graceful degradation (fallback narrative, not 500 error).
- Response is parsed to strip markdown code fences before JSON extraction.
**Dependencies:** None

---

### FR-015
**Title:** Health Check Endpoint
**Description:** The system must expose a GET /health endpoint that returns service status.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- GET /health returns `{"status": "ok", "service": "pharma-compliance-bi-chatbot"}` with HTTP 200.
- Endpoint responds even when downstream services (DuckDB, Groq) are unavailable.
**Dependencies:** None

---

### FR-016
**Title:** CORS Support
**Description:** The backend must include CORS middleware to permit cross-origin requests from the frontend.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- CORS headers are present on all API responses.
- Preflight OPTIONS requests return HTTP 200 with correct CORS headers.
**Dependencies:** None

---

### FR-017
**Title:** DuckDB Data Layer
**Description:** The system must register all 16+ compliance data tables as DuckDB views over CSV files at startup and maintain a shared connection for query execution.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- All CSV files present in /data/csv/ are registered as DuckDB views at startup.
- Missing CSV files are handled gracefully (table not registered, not an error).
- Connection is reused across requests (not reconnected per request).
- Query results are returned as `list[dict]` for JSON serialization.
**Dependencies:** None

---

### FR-018
**Title:** Safe JSON Serialization
**Description:** The system must serialize all query results to JSON-safe types, converting date and datetime objects to ISO 8601 strings.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- All date and datetime fields in query results are serialized as ISO 8601 strings.
- None values are preserved as JSON null.
- Response data is capped at 50 rows to prevent oversized API responses.
**Dependencies:** FR-005

---

### FR-019
**Title:** Policy Registry — Rule Storage
**Description:** The Policy as a Service engine must maintain a structured registry of all compliance rules, each with: policy ID, title, regulatory reference, rule definition, data domain, violation severity, action on violation, sites in scope, and effective date.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Policy Registry is queryable and returns all active rules.
- Each rule has a unique policy ID in format POL-{DOMAIN}-{NNN}.
- Rules can be filtered by domain, severity, and site scope.
- Inactive (retired) rules are retained for audit purposes.
**Dependencies:** None

---

### FR-020
**Title:** Policy Rule Evaluation Engine
**Description:** The Policy as a Service engine must evaluate compliance data records against all applicable policy rules and generate a structured finding for each rule that fires.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Engine evaluates all active rules for a given data record within 500ms.
- Each finding includes: policy_id, rule_description, evidence (field values that triggered the rule), severity, and recommended_action.
- Rules that do not fire produce no output (silent pass).
**Dependencies:** FR-019

---

### FR-021
**Title:** CAPA Timeliness Policy Rules
**Description:** The system must implement and enforce the following CAPA timeliness rules:
(a) Critical CAPAs must have target_close_date ≤ 30 days from initiation_date.
(b) Major CAPAs must have target_close_date ≤ 60 days from initiation_date.
(c) Any CAPA where actual_close_date IS NULL AND target_close_date < CURRENT_DATE must have status = 'Overdue'.
(d) No CAPA may be closed without root_cause_category and root_cause_detail populated.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Rules (a)–(d) fire correctly for all test cases in the CAPA policy test suite.
- Rule (c) fires for all records matching the condition on every evaluation run.
- Rule (d) fires at CAPA close attempt if root cause fields are null.
**Dependencies:** FR-020

---

### FR-022
**Title:** Regulatory Reference Mapping
**Description:** The policy engine must map each rule to its applicable regulatory reference (21 CFR section, ICH guideline section) and include this reference in all violation findings.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Every policy rule has a non-null regulatory_ref field.
- Regulatory references follow standard citation format (e.g., "21 CFR 211.192", "ICH Q10 3.2.3").
- Violation findings include the regulatory reference in a format suitable for inclusion in audit documentation.
**Dependencies:** FR-019

---

### FR-023
**Title:** Data Governance — Required Field Rules
**Description:** The policy engine must enforce required-field completeness rules for all GMP-classified data records, generating Minor violations for missing required fields.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- deviation_records: deviation_category, severity, root_cause_category, gmp_classification are required.
- capa_records: severity, root_cause_category, owner_employee_id, target_close_date are required.
- training_records: employee_id, doc_id, due_date, status are required.
- Missing required fields generate a POL-DG-XXX violation with severity = Minor.
**Dependencies:** FR-020

---

### FR-024
**Title:** ICH Q9 Risk Register Completeness Rules
**Description:** The policy engine must enforce ICH Q9 requirements on the risk register.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Risks with residual_rpn > 100 and null risk_controls generate a Critical violation citing ICH Q9 §4.
- Risks with risk_acceptance_status = 'Unacceptable' and no linked_capa_id generate a Major violation.
- Risks with next_review_date < CURRENT_DATE generate a Minor violation.
**Dependencies:** FR-020

---

### FR-025
**Title:** Policy Violation Alert Generation
**Description:** The policy engine must generate notifications for policy violations at or above a configurable severity threshold. Critical violations must notify within 15 minutes.
**Priority:** Must
**Feature:** Policy as a Service
**Acceptance Criteria:**
- Critical violations generate an in-app alert within 15 minutes of the evaluation run.
- Notifications include: violation summary, evidence, regulatory reference, recommended action, and link to affected record.
- Alert recipients are determined by violation domain and site (site QM for site-specific violations, global QA Director for Critical violations).
**Dependencies:** FR-020

---

### FR-026
**Title:** Deviation Watcher Agent — Pattern Detection
**Description:** The Deviation Watcher Agent must continuously monitor deviation records and detect the following patterns: (a) Critical deviations with no CAPA after 48 hours, (b) 30%+ week-on-week frequency spike at a site, (c) 3+ deviations with same root_cause_category at same site in 30 days, (d) batch disposition impact with no quality disposition review after 24 hours.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Agent runs on 30-minute schedule and after every new deviation insert.
- All four pattern rules are evaluated on every run.
- Alerts are generated within 2 minutes of a pattern being detected.
- Alert includes: rule fired, evidence (specific deviation IDs), regulatory reference, recommended action.
**Dependencies:** FR-005, FR-014

---

### FR-027
**Title:** CAPA Auto-Drafter Agent — Draft Generation
**Description:** The CAPA Auto-Drafter Agent must generate a complete, structured CAPA draft when triggered by a deviation with completed investigation, including: problem statement, root cause detail, proposed corrective actions (minimum 1), proposed preventive actions (minimum 1), target close date (policy-compliant), effectiveness check requirement, and owner assignment suggestion.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Draft is generated within 60 seconds of trigger.
- Draft passes Policy Engine validation (all required CAPA fields present, dates within policy limits).
- At least 1 corrective and 1 preventive action item are generated.
- CAPA is NOT created in the system without explicit human approval (Accept action).
**Dependencies:** FR-021, FR-014, FR-005

---

### FR-028
**Title:** Human Approval Gate
**Description:** All agent actions that create, modify, or delete GMP data records must be blocked until a human approval event is recorded. The approval event must log the approver's identity, timestamp, and any modifications made to the agent's proposal.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- TOOL-RECORD-001 (create_training_assignment) verifies active approval token before execution.
- Approval events are written to the immutable audit trail with: approver_id, approval_timestamp, action_approved, modification_summary.
- If approval token is absent or expired, the record creation fails with a clear error.
**Dependencies:** FR-042

---

### FR-029
**Title:** Training Cascade Agent — Assignment Generation
**Description:** The Training Cascade Agent must identify all affected employees when a document revision is approved and generate training assignment records with appropriate due dates based on the change magnitude.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Agent triggers within 1 hour of a document status change to 'Effective' with new version.
- Affected employees correctly identified from training_curricula and job_roles tables.
- Due dates follow policy: Critical/Emergency changes = 7 days, Major = 14 days, Minor = 30 days.
- Assignment list is presented to department manager for approval before records are created.
**Dependencies:** FR-028, FR-005

---

### FR-030
**Title:** Inspection Readiness Agent — Score Calculation
**Description:** The Inspection Readiness Agent must calculate a composite Inspection Readiness Score (0–100) weekly, incorporating CAPA health, training compliance, deviation management, audit findings, regulatory commitments, document currency, and risk register status with defined weights.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Score is calculated and stored every 7 days (configurable).
- Score is queryable via chatbot: "Are we inspection ready for FDA?" returns the current score.
- Score breakdown by domain is included in the response.
- Action list of items that would improve the score is generated with each calculation.
**Dependencies:** FR-005

---

### FR-031
**Title:** QMR Report Generator Agent — ICH Q10 Compliance
**Description:** The QMR Generator Agent must produce a draft QMR that includes all elements required by ICH Q10 Section 2.5: product quality review, CAPA effectiveness review, process performance monitoring, change control review, resource assessment, and regulatory submission status.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Generated QMR includes all ICH Q10 §2.5 required sections.
- All numerical data in the QMR matches the output of the underlying named queries.
- QMR is presented as a structured draft requiring human review before distribution.
- Generation completes within 5 minutes for a single-site, single-quarter report.
**Dependencies:** FR-014, FR-005

---

### FR-032
**Title:** Root Cause Investigator — Multi-Hop Evidence Gathering
**Description:** The RCA Investigator Agent must traverse at least 6 evidence hops for a given deviation: batch records, equipment qualification, personnel training, area process history, supplier/material quality, and risk register cross-reference.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- All 6 hops are attempted for every investigation.
- Hops that yield no findings return "No relevant findings" (not errors).
- Synthesis narrative correctly ranks candidate root causes by number of supporting signals.
- Investigation package is presented to the human investigator — agent does not determine final root cause.
**Dependencies:** FR-005, FR-014

---

### FR-033
**Title:** Supplier Risk Monitor — Trend Analysis
**Description:** The Supplier Risk Monitor Agent must calculate rolling 12-week rejection rate trends for all GMP-critical suppliers and flag suppliers showing a worsening trend (current rate > 1.5× prior 12-week average).
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Weekly analysis covers all suppliers with is_gmp_critical = true or risk_rating = 'High'.
- Trend calculation uses 12-week rolling average.
- Flagging threshold is configurable (default 1.5×).
- Weekly digest delivered to Supplier Quality team lead.
**Dependencies:** FR-005

---

### FR-034
**Title:** Agent Audit Trail
**Description:** Every agent run must produce an immutable audit trail entry recording: agent ID, run ID, timestamp, trigger event, data sources accessed, rules or tools invoked, findings generated, human notifications sent, and human approval/rejection decisions.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Audit entries are written for every agent run, including runs with no findings.
- Entries are never modified or deleted after writing.
- Audit trail is queryable by: agent_id, run_date_range, triggered_by, human_decision.
- Format is JSON with all required fields present.
**Dependencies:** None

---

### FR-035
**Title:** Agent Autonomy Level Enforcement
**Description:** The system must enforce autonomy level limits for each agent. Level 1 agents may only read data and send notifications. Level 2 agents may additionally generate drafts. Level 3 agents may create GMP records after human approval. No agent may operate above its configured level.
**Priority:** Must
**Feature:** Agentic Actions
**Acceptance Criteria:**
- Level 1 agents: tool calls to TOOL-RECORD-001 raise an authorization error.
- Level 2 agents: draft generation is permitted; record creation requires approval token.
- Level 3 agents: record creation executes after approval token is validated.
- Autonomy level is configured per agent and cannot be overridden at runtime without admin permission.
**Dependencies:** FR-028

---

### FR-036
**Title:** Data Generator — Synthetic Compliance Data
**Description:** The system must include a data generator that creates realistic synthetic compliance data for all 16+ tables, with embedded patterns (CAPA overdue clusters, deviation seasonal spikes, supplier rejection trends) suitable for demonstrating platform capabilities.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- Running `python -m data.generators.generate_compliance_data` produces CSV files for all tables.
- Generated data contains at least: 500 CAPA records, 1000 deviation records, 200 audit findings, 2000 training records, 50 supplier inspection lots, 100 risk register entries.
- Known patterns are embedded: SITE-EU-02 compliance underperformance, Sigma API rejection trend, Q4 deviation spike.
**Dependencies:** None

---

### FR-037
**Title:** Error Handling and Graceful Degradation
**Description:** The system must handle all anticipated failure modes gracefully, returning informative error messages and partial responses rather than unhandled 500 errors.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- Intent extraction failure (invalid JSON from Groq) → returns default narrative, not 500.
- Query execution failure (SQL error) → returns error message in `error` field, empty data, not 500.
- Missing data files (CSV not found) → table not registered, queries against missing table return empty list.
- Groq API rate limit → exponential backoff with max 3 retries before graceful failure.
**Dependencies:** None

---

### FR-038
**Title:** Response Capping and Pagination
**Description:** The /chat endpoint must cap data payloads at 50 rows per response to prevent oversized API responses, while the full dataset is retained in session state.
**Priority:** Must
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- ChatResponse.data contains a maximum of 50 rows regardless of query result size.
- The narrative and viz_spec are generated from the full result set (up to the first 10 rows for narrative, full set for viz).
- Response size stays under 1MB for all standard queries.
**Dependencies:** FR-001

---

### FR-039
**Title:** Static File Serving — Frontend
**Description:** The FastAPI server must serve the frontend single-page application from the /frontend directory, with index.html at the root (/) and static assets at /static/*.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- GET / returns the index.html file.
- GET /static/{filename} returns the corresponding file from the frontend directory.
- 404 is returned for missing static files.
**Dependencies:** None

---

### FR-040
**Title:** Pydantic Request Validation
**Description:** All API endpoint inputs must be validated using Pydantic models. Invalid requests must return HTTP 422 with field-level validation errors.
**Priority:** Must
**Feature:** Platform
**Acceptance Criteria:**
- POST /chat with missing `query` field returns HTTP 422.
- POST /chat with `query` exceeding 2000 characters returns HTTP 422 with appropriate message.
- Valid requests with optional fields omitted use defined defaults (session_id=None, user_id="default_user").
**Dependencies:** None

---

### FR-041
**Title:** Risk Matrix Visualization
**Description:** The risk matrix visualization must render an ICH Q9-compliant Severity × Occurrence matrix with bubble sizes representing risk count and color intensity representing average RPN, with zone coloring (red for high, amber for medium, green for acceptable).
**Priority:** Should
**Feature:** AI BI Chatbot
**Acceptance Criteria:**
- risk_matrix viz_type produces a valid Vega-Lite layered spec with background zone rectangles and bubble overlay.
- Background zone: severity × occurrence ≥ 16 → red; ≥ 8 → amber; < 8 → green.
- Bubble size encodes risk_count field.
- Bubble color encodes avg_rpn field with reds color scheme.
**Dependencies:** FR-007

---

### FR-042
**Title:** Immutable Audit Log
**Description:** All system actions (queries executed, agent runs, human approvals, policy violations) must be written to an append-only audit log with cryptographic integrity markers, suitable for 21 CFR Part 11 compliance.
**Priority:** Should
**Feature:** Platform
**Acceptance Criteria:**
- Every /chat request generates an audit log entry.
- Every agent run generates one or more audit log entries.
- Log entries cannot be modified or deleted via any API endpoint.
- Log entries include: timestamp (UTC), user_id, action_type, action_details, result_summary.
**Dependencies:** None

---

### FR-043
**Title:** Inspection Readiness Score — Chatbot Integration
**Description:** Users must be able to query the Inspection Readiness Score via the chatbot using natural language questions about inspection readiness.
**Priority:** Should
**Feature:** Agentic Actions / AI BI Chatbot
**Acceptance Criteria:**
- Query "Are we inspection ready?" or "Show inspection readiness score" returns a radar chart with 7 domain scores plus the composite score.
- The intent type COMPLIANCE_SCORE maps to the Inspection Readiness Agent's latest computed score.
- Score components are clearly labeled with RAG status.
**Dependencies:** FR-030, FR-001

---

### FR-044
**Title:** Policy Violation Dashboard
**Description:** The system should provide a queryable view of all active policy violations, filterable by domain, severity, site, and age, accessible via chatbot query and as a dedicated dashboard view.
**Priority:** Should
**Feature:** Policy as a Service
**Acceptance Criteria:**
- "Show all active Critical policy violations" returns a list of current Critical violations with evidence and recommended actions.
- Violations are grouped by domain and site in the response.
- Age of violation (days since first triggered) is included.
**Dependencies:** FR-020, FR-025

---

### FR-045
**Title:** Configurable Alert Thresholds
**Description:** Policy Engine violation thresholds and Agent pattern detection thresholds must be configurable without code changes, stored in a configuration file or registry.
**Priority:** Could
**Feature:** Policy as a Service / Agentic Actions
**Acceptance Criteria:**
- CAPA timeliness thresholds (30/60/90 days by severity) are externalized to configuration.
- Agent pattern detection thresholds (deviation frequency spike multiplier, CAPA-without-CAPA window) are externalized.
- Configuration changes take effect on the next evaluation run without server restart.
**Dependencies:** FR-019, FR-026

---

### FR-046
**Title:** Multi-Site Data Scoping
**Description:** The system should support site-scoped queries where a user with site-level permissions sees only data for their assigned sites.
**Priority:** Could
**Feature:** Platform
**Acceptance Criteria:**
- Site-scoped user: queries against capa_records, deviation_records, etc. automatically filter to their assigned site_ids.
- Site-scoped user cannot retrieve data for sites outside their scope even by adding explicit filters.
- Global QA Director role: no site restriction applied.
**Dependencies:** FR-005

---

*Requirements Lead: Compliance BI Platform Team | April 2026*
*Next review: July 2026*
