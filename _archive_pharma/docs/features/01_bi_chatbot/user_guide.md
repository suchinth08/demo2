# AI BI Chatbot — User Guide

**Document Type: End-User Guide**
**Version: 1.0 | April 2026**
**Audience: Compliance Officers, QA Analysts, Quality Directors, Regulatory Affairs**

---

## Getting Started

### What Is the AI BI Chatbot?

The AI BI Chatbot lets you ask questions about your organization's compliance data in plain English — the same way you would ask a knowledgeable colleague. You do not need to know SQL, navigate dashboards, or export spreadsheets. Ask the question, get the answer with a chart and a written insight.

### Accessing the Platform

1. Open your browser and navigate to `http://localhost:8000` (or your organization's deployment URL).
2. The chat interface loads immediately — no login is required in the current version.
3. The sidebar shows your conversation history. The main panel shows the chat.

### Your First Query

Type any compliance question in the input bar at the bottom and press **Enter** or click the send button. Try:

> "What is our overall CAPA on-time closure rate?"

Within a few seconds you will see a metric card with the rate, an AI-written insight paragraph, and three suggested follow-up questions you can click to continue the conversation.

---

## Interface Walkthrough

### Sidebar (Left Panel)

The sidebar shows your conversation history — each conversation is a separate session with its own context thread. Click any past session to review it. Start a new conversation by clicking **New Chat** at the top of the sidebar.

Each session entry shows:
- The first question you asked in that session
- The number of turns (questions and answers)
- The domain of the last query (CAPA, Training, etc.)

### Chat Area (Main Panel)

The chat area displays your conversation chronologically:

- **Your messages** appear on the right in the user bubble style.
- **AI responses** appear on the left and contain:
  - An **intent tag** showing the detected query type (e.g., [TREND ANALYSIS | CAPA])
  - A **visualization** — chart, table, or metric card
  - A **narrative** — 3–5 sentences of AI-written insight
  - **Follow-up suggestion pills** — 3 clickable buttons for the next question

### Input Bar (Bottom)

Type your question and press Enter, or click the circular send button. The input bar is always available. Click any follow-up suggestion pill to auto-populate the input bar with that question.

### Visualizations

Charts and tables appear inline in the AI response. You can:
- **Hover** over chart elements to see exact values in a tooltip
- **Sort** data tables by clicking column headers
- **Export** results using the export button that appears on hover

### Intent Tag

Every AI response shows a small tag indicating how the system interpreted your question:
- `[METRIC_SNAPSHOT | CAPA]` — You asked for a single KPI about CAPA
- `[TREND_ANALYSIS | DEVIATIONS]` — You asked for a time-series trend about deviations
- `[OVERDUE_ALERT | TRAINING]` — You asked for overdue items in training

This tag helps you understand if the system understood your question correctly. If the intent tag looks wrong, rephrase your question or add more context.

---

## How to Ask Questions

### General Tips

**Be direct.** The system works best with specific questions:
- Good: "Show me overdue CAPAs by site"
- Less good: "Can you tell me something about CAPA status?"

**Use natural pharma language.** All these work:
- "CAPAs", "corrective actions", "CA/PA"
- "deviations", "non-conformances", "discrepancies"
- "483 observations", "audit citations", "findings"
- "training compliance rate", "GMP training status"
- "RPN", "risk score", "criticality"

**Specify time if you want to filter.** Time expressions that work:
- "this year", "last year", "last quarter", "last month"
- "last 12 months", "rolling 12 months", "YTD"
- "in Q1 2026", "between January and March"

**Ask for what you want to see.** The system picks the right chart automatically, but you can guide it:
- "Show me a trend" → line chart
- "Rank by..." → horizontal bar chart
- "Break it down by..." → bar chart
- "Show me the list" → data table
- "Show the risk matrix" → ICH Q9 risk matrix

### Follow-Up Questions

After any response, you can ask follow-up questions without restating context. The system remembers what you just asked:

**Example thread:**
1. "Show CAPA on-time closure rate by site" → you see a site breakdown
2. "Now just show Frankfurt" → filters to Frankfurt only (inherits CAPA context)
3. "What's driving the overdue backlog?" → switches to root cause breakdown (still Frankfurt, still CAPA)
4. "Show the training compliance there too" → switches domain to Training, keeps Frankfurt filter

**Follow-up triggers the system recognizes:**
- "Now show...", "Also...", "What about...", "Break it down by...", "Only for...", "Same but...", "Filter to..."
- Single-word clarifications like "by site", "by department", "last year"
- "Show me the details" or "Show me the list" → drills to a data table

### Tips for Best Results

- If a chart type is not what you expected, say "Show me this as a table" or "Show me this as a bar chart instead."
- If the system misunderstands a follow-up, start with "New question:" to signal a fresh query.
- Use site names as they appear in the system (e.g., "Frankfurt", "Philadelphia") not codes (SITE-EU-02).
- Combining two questions in one sentence works: "Show me CAPA trend and break it down by root cause."

---

## Understanding Responses

### The Intent Tag

The intent tag shows how the AI classified your question. The format is `[INTENT TYPE | DOMAIN]`.

| Intent Type | What It Means | Typical Viz |
|---|---|---|
| METRIC_SNAPSHOT | Single KPI value | Metric card |
| TREND_ANALYSIS | Metric over time | Line chart |
| BREAKDOWN | Metric by category or dimension | Bar chart |
| RANKING | Top or bottom N | Horizontal bar |
| COMPARISON | Two things side by side | Grouped bar |
| OVERDUE_ALERT | Items past due date | RAG table |
| RISK_ASSESSMENT | Risk scores and matrix | Risk matrix |
| COMPLIANCE_SCORE | Overall health score | Radar chart |
| REGULATORY_STATUS | Inspection history, commitments | Timeline / Table |
| DRILL_DOWN | Detailed records list | Data table |

### The Narrative

The AI-written narrative directly follows your question with 3–5 sentences:
1. **Direct answer** — the number or finding you asked for
2. **Key insight** — the most important pattern or anomaly in the data
3. **Compliance flag** — any regulatory risk embedded in the data
4. **Follow-up prompt** — "Follow-up: [suggested next question]"

The narrative is generated from the actual query results, not from general knowledge. If data is missing or incomplete, the narrative will say so.

### Charts and Tables

- **Line charts** show trends over time. Hover over any point to see the exact value.
- **Bar/Horizontal bar charts** show rankings or breakdowns. Bars are sorted by default.
- **Metric cards** show single key numbers with a label.
- **Data tables** are sortable by any column. Click column headers to sort.
- **RAG tables** (Red/Amber/Green) color-code rows based on compliance thresholds. Red = action required, Amber = watch, Green = compliant.
- **Risk matrix** shows ICH Q9 Severity × Occurrence bubbles. Larger bubbles = more risks in that zone.

### Suggested Follow-Ups

Three follow-up suggestion pills appear below every response. These are contextually generated based on the current domain and intent. Click any pill to instantly run that question. You can also type your own follow-up.

---

## Multi-Turn Conversations

### How Context Works

Each session maintains a running context window. When you ask a follow-up question, the system carries forward:
- The compliance **domain** (CAPA, Deviations, Training, etc.)
- The **time filter** (last 12 months, Q1 2026, etc.)
- The active **metrics** (on-time closure rate, rejection rate, etc.)
- Any **record-level filters** (site = Frankfurt, supplier = Sigma, etc.)

You only need to specify what is changing. Everything else is inherited.

### Starting a New Topic

To switch topics completely, just ask a clearly new question. The system will recognize the domain change:
- "Show me deviation trends" after asking about CAPAs → clear domain switch → fresh intent
- "Now show training compliance" after CAPA analysis → clear domain switch

If the system incorrectly inherits context from a prior question, prefix your query with "New question:" to force a fresh interpretation.

### Session Limits

Each session stores the last 5 turns for context resolution. Sessions do not persist across server restarts in the current version. For production use, sessions are stored for 24 hours.

---

## Chart Types and When Each Appears

| Chart Type | When It Appears | Example Queries |
|---|---|---|
| **Metric Card** | Single KPI queries | "What is our CAPA closure rate?" |
| **Line Chart** | Time-series and trend queries | "Show deviation trend last 12 months" |
| **Bar Chart** | Category breakdown queries | "Show CAPAs by root cause" |
| **Horizontal Bar** | Ranking queries | "Rank suppliers by rejection rate" |
| **Grouped Bar** | Comparison queries | "Compare CAPA rates for Q1 vs Q2" |
| **Donut/Pie** | Composition/share queries | "What share of deviations are critical?" |
| **Heatmap** | Two-dimensional matrix queries | "Show deviation category vs site heatmap" |
| **Risk Matrix** | Risk score queries | "Show the risk matrix" |
| **Radar Chart** | Multi-dimension health scores | "Show inspection readiness score" |
| **Data Table** | Detail queries and drill-down | "Show me the overdue CAPA list" |
| **RAG Table** | Overdue item queries | "Show overdue training by employee" |
| **Timeline** | Regulatory inspection history | "Show FDA inspection history" |

---

## Exporting Results

Every query response includes an **Export** button that appears when you hover over the result area. Export options:

- **Export as CSV** — downloads the raw query results as a comma-separated file
- **Copy as Table** — copies the data formatted as a Markdown or HTML table for pasting into documents

For charts, right-click the chart area to save as an image (PNG/SVG) using your browser's standard right-click menu.

---

## 50+ Example Questions by Domain

### CAPA (Corrective & Preventive Actions)

1. What is our CAPA on-time closure rate?
2. Show me the CAPA on-time closure rate by site.
3. Which site has the most overdue CAPAs?
4. Show overdue CAPAs across all sites.
5. Which department has the most open CAPAs?
6. Show CAPA trend for the last 12 months.
7. What are the top root causes for CAPAs this year?
8. How many Critical CAPAs are currently open?
9. What is our CAPA recurrence rate?
10. Show CAPAs that were reopened.
11. What is the average CAPA cycle time by severity?
12. Show CAPAs initiated by audit findings.
13. Which CAPAs have failed effectiveness checks?
14. Show me CAPAs with no owner assigned.
15. What is our YTD CAPA closure rate vs last year?

### Deviations

16. Show me the deviation trend for the last 12 months.
17. What are the top 5 root cause categories for deviations?
18. Which site has the highest critical deviation rate?
19. Show deviations that impacted batch disposition.
20. Compare deviation rate between manufacturing sites.
21. Which shift has the most deviations?
22. Show me deviations in the Equipment category.
23. What percentage of deviations triggered a CAPA?
24. Show deviation trend by product.
25. How many planned vs unplanned deviations do we have?

### Audit Findings

26. Show audit findings by process area.
27. Which sites have the most repeat findings?
28. What FDA regulatory references are cited most often?
29. Show all critical audit findings in the last 2 years.
30. Which process area has the highest repeat finding rate?
31. Show audit findings from the last FDA inspection.
32. How many audit findings are still open without a response?
33. What is our response acceptance rate for audit findings?

### Training Compliance

34. What is the GMP training compliance rate by department?
35. Show me all overdue training records.
36. Which site has the lowest training compliance?
37. Show training records expiring in the next 30 days.
38. Which employees have the most overdue training items?
39. What is the first-pass assessment rate?
40. Show training compliance trend over the last 6 months.
41. Which department has the most overdue training in QC?

### Supplier Quality

42. Rank suppliers by incoming rejection rate.
43. Show rejection rate trend for Sigma API Solutions.
44. Which suppliers have qualification status issues?
45. Which API suppliers are approaching requalification due date?
46. Show supplier scorecard for all high-risk suppliers.
47. How many lots were rejected this year by supplier?

### Risk Management

48. Show top 20 risks by residual RPN.
49. Show risk distribution by category.
50. Which risks are classified as unacceptable?
51. Show the ICH Q9 risk matrix.
52. Which high-RPN risks have no linked CAPA?
53. Show risks for our injectable products.

### Regulatory Inspections

54. Show FDA inspection history by site.
55. How many 483 observations have we received per inspection?
56. Show open regulatory commitments that are overdue.
57. Are we inspection ready for FDA?
58. Show regulatory inspection outcomes (NAI/VAI/OAI) by site.

### Batch Quality

59. What is the batch rejection rate by site?
60. Show batch rejection trend by quarter.
61. Which products have the highest rejection rate?
62. How many batches are currently on hold?

---

## Troubleshooting FAQ

**Q: My question returned "No data found" — what happened?**

This usually means one of three things: (a) the data files for that domain are not populated, (b) your filters are too specific (e.g., filtering to a site that doesn't exist in the data), or (c) the date range you specified has no records. Try removing filters or asking a broader question. Check the intent tag to see what filters were applied.

---

**Q: The intent tag shows the wrong domain — how do I fix it?**

Rephrase with more explicit domain language. For example, if asking about non-conformances is being classified as CAPA, say "Show me deviation non-conformances" or "Show the deviation records." You can also start fresh by clicking New Chat.

---

**Q: The chart is the wrong type — can I change it?**

Yes. Say "Show me this as a table" or "Show me this as a bar chart." The system will re-render the same data with the visualization type you specify.

---

**Q: My follow-up question isn't inheriting the context from my last question.**

This happens if the new question doesn't contain follow-up signals. Try prefixing with "Now show me...", "Break that down by...", or "Same question, but filter to...". If the system treats it as a fresh query, you may need to restate the domain or filter.

---

**Q: The narrative says something that doesn't match the chart numbers — is there an error?**

The narrative is generated from a preview of the data (first 10 rows for long result sets). If the chart shows more data than the narrative references, this is expected behavior — the narrative summarizes the most prominent findings, not every data point. For the full detail, export the data.

---

**Q: I asked about a specific employee and got no results.**

The chatbot does not support queries about individual employees by name in the current version due to privacy controls. You can query by department, site, or role. The overdue training list does show employee names for authorized users with QA or Training roles.

---

**Q: How long does a typical response take?**

Most queries return in 2–5 seconds. Queries involving LLM calls (intent extraction + narrative generation) add approximately 1–3 seconds of AI processing time. If your connection to the Groq API is slow, responses may take up to 10 seconds. A loading indicator is shown while the response is processing.

---

**Q: Can I ask about data from a specific date range not listed in the time expressions?**

Yes. You can specify explicit dates: "Show me deviations from January 2025 to March 2025" or "Show CAPA trend for 2024." These are interpreted by the LLM and converted to appropriate date filters. Unusual date formats may occasionally be misinterpreted — use ISO format (2025-01-01) for most reliable results.

---

**Q: The chat says it can't find the GROQ_API_KEY. What should I do?**

This is a configuration issue. The platform administrator needs to set the GROQ_API_KEY environment variable in the .env file. See the Developer Setup Guide for instructions. This issue only affects organizations running their own self-hosted deployment.

---

**Q: I asked "show me everything" or "give me a summary of all compliance" — why did I only get one domain?**

The system is optimized for domain-specific queries. Multi-domain summaries are handled by the Inspection Readiness Score (try: "Show me our overall compliance health" or "Are we inspection ready?") which provides a radar chart across all domains. For a full cross-domain summary, use the QMR Generator Agent.

---

*User Guide: Compliance BI Platform Team | April 2026*
*Have feedback on this guide? Contact the platform team.*
