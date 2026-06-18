# Example Multi-Turn Conversations — Pharma Compliance BI Chatbot

These examples demonstrate the intent resolution, follow-up threading,
and domain-specific compliance insights the chatbot produces.

---

## Conversation 1: CAPA Deep-Dive

**Turn 1 — Snapshot**
> User: "What is our CAPA on-time closure rate?"

Intent: `METRIC_SNAPSHOT | capa | capa_on_time_closure_rate`
Response: "Your overall CAPA on-time closure rate is **84.2%**, below the 90% benchmark.
There are currently **23 overdue CAPAs** across all sites, with **3 Critical** CAPAs past due.
Follow-up: Which site is driving the overdue backlog?"
Viz: Metric card with trend indicator (🔴 below target)

---

**Turn 2 — Follow-up: Site breakdown (delta: add dimension)**
> User: "Break it down by site"

Intent: `BREAKDOWN | capa | site_name` ← inherits time context
Response: "Frankfurt QC Lab (SITE-EU-02) has the lowest on-time closure rate at **71.3%**
with **12 overdue CAPAs**, significantly underperforming vs. Philadelphia at **93.1%**.
Frankfurt's average CAPA cycle time is 78 days vs. the 60-day Major CAPA target.
Follow-up: What are the root causes driving Frankfurt's CAPAs?"
Viz: Horizontal bar chart (sites ranked by overdue count, RAG-colored)

---

**Turn 3 — Follow-up: Root cause for specific site**
> User: "What's driving Frankfurt's CAPAs?"

Intent: `BREAKDOWN | capa | root_cause_category` + filter `site_id=SITE-EU-02`
Response: "Training (38%) and Procedure (29%) gaps account for 67% of Frankfurt's CAPAs.
This suggests systemic issues with SOP adherence — likely compounded by high contractor
turnover (32% of the site workforce). 5 of their 12 overdue CAPAs are in the QC Lab department.
Follow-up: What is Frankfurt's training compliance rate?"
Viz: Pareto chart (root cause categories with cumulative %)

---

**Turn 4 — Domain switch: Training**
> User: "What is Frankfurt's training compliance rate?"

Intent: `METRIC_SNAPSHOT | training | training_compliance_rate` + filter `site=SITE-EU-02`
Response: "Frankfurt's GMP training compliance rate is **88.4%**, well below the 98% target (🔴).
There are **47 overdue training records**, concentrated in the Microbiology QC and Analytical QC departments.
3 employees have 5+ overdue trainings — these are your highest-risk individuals.
Follow-up: Show me the overdue training list for Frankfurt"
Viz: Gauge chart with RAG zones (needle in red zone)

---

## Conversation 2: Deviation Analysis

**Turn 1 — Trend query**
> User: "Show me the deviation trend for the last 12 months"

Intent: `TREND_ANALYSIS | deviations | total_deviations`
Response: "Deviations are trending upward — Q4 2024 saw **43% more deviations** than Q1 2024.
The October-December period shows a consistent seasonal spike, likely driven by year-end
production pressure. Critical deviation rate held steady at 1.8%, within the 2% target.
Follow-up: Which site is driving the Q4 spike?"
Viz: Line chart with UCL/LCL control lines, Q4 annotated

---

**Turn 2 — Site drill-down**
> User: "Which site?"

Intent: `BREAKDOWN | deviations | site_name` ← inherits last 12 months filter
Response: "Philadelphia Manufacturing (SITE-US-01) accounts for **61% of Q4 deviations**,
primarily in the Equipment category (34% of events). Dublin saw a batch disposition impact
rate of **4.2%** vs. the 1% benchmark — 3 batches placed on hold in November alone.
Follow-up: Show root cause breakdown for Philadelphia's equipment deviations"
Viz: Stacked bar (sites × severity)

---

**Turn 3 — Root cause Pareto**
> User: "Show root cause breakdown"

Intent: `BREAKDOWN | deviations | root_cause_category` ← filter Philadelphia
Response: "Equipment failures (34%) and Process gaps (28%) drive 62% of Philadelphia deviations —
classic 80/20 pattern. The Equipment category has a 23% CAPA trigger rate vs. 41% for Process,
suggesting under-reporting of corrective actions for equipment events. This should be reviewed
against your GMP data integrity policy.
Follow-up: Are any of these equipment deviations linked to overdue calibrations?"
Viz: Pareto chart (bar + cumulative % line, 80% threshold marked)

---

## Conversation 3: Supplier Quality

**Turn 1 — Scorecard**
> User: "Rank our API suppliers by rejection rate"

Intent: `RANKING | supplier_quality | supplier_rejection_rate`
Response: "Sigma API Solutions has the highest rejection rate at **3.8%**, 4× the 1% benchmark
for critical API suppliers. This has been worsening over the past 8 months — rejection rate
was 1.2% in January 2024 and reached 6.1% in October 2024. An open CAPA (CAPA-0087) exists
but has been in 'In Progress' status for 73 days past its due date.
Follow-up: Show the monthly rejection trend for Sigma API?"
Viz: Horizontal bar (suppliers ranked, Sigma highlighted in red)

---

**Turn 2 — Trend for specific supplier**
> User: "Show me the trend"

Intent: `TREND_ANALYSIS | supplier_quality | rejection_rate_pct` + filter Sigma API
Response: "The worsening trend is clear — Sigma's rejection rate has increased steadily
from 1.2% to 6.1% over 10 months, correlating with their facility expansion completed in March.
3 of their 7 rejections cite 'Out of Spec - Purity' suggesting a process change issue.
This supplier is at risk of suspension per your Approved Vendor List policy.
Follow-up: What is Sigma's current qualification status and audit score?"
Viz: Line chart with trend line, benchmark at 1%

---

## Conversation 4: Regulatory Readiness

**Turn 1 — Inspection readiness**
> User: "Are we inspection ready for FDA?"

Intent: `COMPLIANCE_SCORE | regulatory | inspection_readiness`
Response: "Your composite FDA Inspection Readiness Score is **76/100** (🟡 Amber).
Key gaps: 18 overdue CAPAs (including 2 Critical), training compliance at 88.4% at Frankfurt,
and 4 open regulatory commitments past their response date. Your last FDA inspection at
Philadelphia (March 2024) resulted in 3 Form 483 observations — all with accepted responses.
Follow-up: Show me the open regulatory commitments that are overdue"
Viz: Radar chart (5 KPI axes: CAPA, Training, Deviations, Audits, Commitments)

---

**Turn 2 — Open commitments**
> User: "Show me the overdue commitments"

Intent: `OVERDUE_ALERT | regulatory | regulatory_commitments`
Response: "There are **4 overdue regulatory commitments**, all from the March 2024 FDA inspection.
The most critical is RCOM-0012 referencing 21 CFR 211.68 (computer system validation) —
124 days overdue with no linked CAPA. FDA response dates are legally binding; immediate
escalation is recommended for these 4 items.
Follow-up: Create CAPAs for each of these overdue commitments"
Viz: Table with RAG rows (all red), days overdue column

---

## Key Business Insights Embedded in Sample Data

| Pattern | Description | How to Surface |
|---|---|---|
| **SITE-EU-02 compliance challenge** | Higher CAPA count, overdue rate, lower training compliance | "Compare sites on compliance KPIs" |
| **Sigma API worsening rejection** | Rejection rate trending from 1.2% → 6.1% over 10 months | "Show rejection trend for Sigma" |
| **Q4 seasonal deviation spike** | 43% more deviations in Oct-Dec across all manufacturing sites | "Show deviation trend by month" |
| **Training-CAPA correlation** | Sites with low training compliance have higher CAPA recurrence | "Correlate training rate with CAPA recurrence" |
| **Repeat audit findings** | 8% of findings are marked as repeat — systemic gap in CAPA effectiveness | "Show repeat finding rate by site" |
| **Change-driven training lag** | Documents revised via change control have avg 12-day delay to training assignment | "Show training completion after SOP revision" |
