# Developer Setup Guide — Compliance BI Platform

**Document Type: Developer Reference**
**Version: 1.0 | April 2026**
**Audience: Engineers, Contributors**

---

## Prerequisites

Before setting up the platform, ensure the following are installed on your machine:

| Requirement | Minimum Version | Check Command |
|---|---|---|
| Python | 3.11+ | `python --version` |
| pip | 23.0+ | `pip --version` |
| Git | 2.40+ | `git --version` |
| A terminal | — | bash, zsh, PowerShell, or cmd |

You will also need:
- A **Groq API key** — free account at [console.groq.com](https://console.groq.com). The free tier is sufficient for development.
- A modern browser (Chrome, Firefox, Edge) for the UI.

---

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone <repository-url> pharma-compliance-bi
cd pharma-compliance-bi
```

### Step 2: Create a Virtual Environment

It is strongly recommended to use a virtual environment to isolate dependencies.

```bash
# Create the virtual environment
python -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Activate it (Windows Command Prompt)
.venv\Scripts\activate.bat

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

Verify activation: your terminal prompt should now show `(.venv)`.

### Step 3: Install Dependencies

```bash
pip install -r config/requirements.txt
```

This installs:
- `fastapi==0.115.0` — API framework
- `uvicorn[standard]==0.30.6` — ASGI server
- `pydantic==2.9.2` — Request/response validation
- `groq==0.11.0` — Groq API client
- `duckdb==1.1.3` — In-process analytical database
- `pandas==2.2.3` — DataFrame operations (query result handling)
- `pyyaml==6.0.2` — YAML parsing (ontology)
- `python-dotenv==1.0.1` — Environment variable loading
- `httpx==0.27.2` — Async HTTP client (for tests)

### Step 4: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env
```

Open `.env` in your editor and fill in the required values:

```env
# REQUIRED: Your Groq API key
GROQ_API_KEY=gsk_your_key_here

# OPTIONAL: Override the default Groq model
GROQ_MODEL=llama-3.3-70b-versatile

# OPTIONAL: Override the data directory path
DATA_DIR=/absolute/path/to/data/csv
```

**Never commit the .env file to version control.** It is already in `.gitignore`.

### Step 5: Generate Sample Data

The platform ships with a data generator that creates realistic synthetic compliance data for all tables.

```bash
python -m data.generators.generate_compliance_data
```

This creates CSV files in `/data/csv/` directory. Expected output:

```
Generating sites... done (5 sites)
Generating departments... done (20 departments)
Generating employees... done (250 employees)
Generating products... done (12 products)
Generating suppliers... done (30 suppliers)
Generating documents... done (80 documents)
Generating capa_records... done (520 records)
Generating deviation_records... done (1040 records)
Generating audit_findings... done (215 records)
Generating training_records... done (2100 records)
Generating batch_records... done (380 records)
Generating supplier_inspections... done (640 records)
Generating risk_register... done (110 records)
Generating change_requests... done (180 records)
Generating regulatory_inspections... done (24 records)
Generating regulatory_commitments... done (48 records)
Data generation complete. Files written to ./data/csv/
```

Known patterns embedded in generated data:
- **SITE-EU-02** (Frankfurt) has lower training compliance and higher CAPA overdue rate
- **Sigma API Solutions** has a worsening rejection rate trend over 10 months
- **Q4 deviation spike** — October–December has ~43% more deviations than Q1

### Step 6: Start the Server

```bash
uvicorn chatbot.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The `--reload` flag enables hot-reload on code changes (development only).

### Step 7: Verify the Setup

Open a new terminal and run:

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"pharma-compliance-bi-chatbot"}
```

Then open `http://localhost:8000` in your browser. The chat UI should appear. Try:
> "What is our CAPA on-time closure rate?"

You should see a metric card response within a few seconds.

---

## Environment Configuration

### Complete .env Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key. Obtain from console.groq.com |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use. Do not change for standard use. |
| `DATA_DIR` | No | `./data/csv` | Absolute or relative path to directory containing CSV files |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG / INFO / WARNING / ERROR |
| `PORT` | No | `8000` | Port for uvicorn to listen on |
| `HOST` | No | `127.0.0.1` | Host address. Use `0.0.0.0` for network access. |

### Running on a Non-Default Port

```bash
uvicorn chatbot.main:app --reload --port 8080
# Or use environment variable:
PORT=8080 uvicorn chatbot.main:app --reload
```

### Running for Network Access (Other Devices on LAN)

```bash
uvicorn chatbot.main:app --reload --host 0.0.0.0 --port 8000
```

Then access from other devices at `http://<your-ip-address>:8000`.

---

## Running Tests

### Unit Tests

```bash
# Install test dependencies (if not already in requirements.txt)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_intent_engine.py -v

# Run tests with coverage
pip install pytest-cov
pytest --cov=chatbot --cov-report=html
```

### Integration Test: Chat Endpoint

```bash
# Quick functional test using curl
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me CAPA on-time closure rate", "user_id": "test_user"}'
```

Expected response structure:
```json
{
  "session_id": "uuid-here",
  "turn_id": 1,
  "user_query": "Show me CAPA on-time closure rate",
  "intent": {"intent": "METRIC_SNAPSHOT", "domain": "capa", ...},
  "narrative": "Your CAPA on-time closure rate is...",
  "viz_type": "metric_card",
  "viz_spec": {...},
  "data": [{...}],
  "suggested_followups": ["...", "...", "..."],
  "error": null
}
```

### Testing Without Groq API

To test query engine and visualization without making Groq API calls, set a mock environment variable:

```bash
# In your test setup
GROQ_API_KEY=test_mock_key pytest tests/ -v
```

The system will fall back to a default intent for intent extraction failures, allowing the rest of the pipeline to be tested.

---

## Project Structure Explained

```
pharma-compliance-bi/
│
├── chatbot/                    # Backend Python package
│   ├── __init__.py
│   ├── main.py                 # FastAPI application + endpoint definitions
│   │                           # Add new endpoints here
│   └── services/
│       ├── intent_engine.py    # LLM intent extraction + narrative generation
│       │                       # Edit ONTOLOGY_CONTEXT to add new domains/metrics
│       ├── query_engine.py     # SQL query library + routing + DuckDB execution
│       │                       # Add new queries and routing rules here
│       ├── session_manager.py  # Session creation + conversation context storage
│       └── viz_builder.py      # Vega-Lite spec builders for all 13 chart types
│
├── frontend/
│   ├── index.html              # Single-page application entry point
│   └── src/                    # JavaScript modules and CSS
│
├── data/
│   ├── csv/                    # Generated CSV data files (gitignored)
│   └── generators/
│       └── generate_compliance_data.py    # Synthetic data generator
│
├── schema/
│   └── compliance_schema.sql   # Full DDL schema (reference only — DuckDB uses CSV)
│
├── ontology/                   # Domain ontology YAML files
│   └── compliance_ontology.yaml
│
├── malloy/                     # Malloy semantic layer definitions (future)
│
├── config/
│   ├── requirements.txt        # Python dependencies
│   └── example_conversations.md
│
├── docs/                       # Documentation (this tree)
│
├── tests/                      # Test suite
│   ├── test_intent_engine.py
│   ├── test_query_engine.py
│   └── test_viz_builder.py
│
├── .env                        # Your local secrets (gitignored)
├── .env.example                # Template for .env
└── .gitignore
```

---

## Adding New Query Types

Follow these steps to add a new named query to the Query Library.

### Step 1: Write the SQL Query

Add your SQL to the `QUERY_LIBRARY` dictionary in `chatbot/services/query_engine.py`:

```python
QUERY_LIBRARY: dict[str, str] = {
    # ... existing queries ...

    # Add your new query:
    "changes.by_category": """
        SELECT
          change_category,
          COUNT(*) AS total_changes,
          SUM(CASE WHEN change_type = 'Emergency' THEN 1 ELSE 0 END) AS emergency_changes,
          ROUND(100.0 * SUM(CASE WHEN change_type = 'Emergency' THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 1) AS emergency_rate_pct,
          ROUND(AVG(DATEDIFF('day', initiation_date,
              COALESCE(close_date, CURRENT_DATE))), 1) AS avg_cycle_days
        FROM change_requests
        GROUP BY change_category
        ORDER BY total_changes DESC
    """,
}
```

**Naming convention:** `domain.description` — e.g., `changes.by_category`, `capa.by_site`, `deviations.pareto_root_cause`.

**SQL requirements:**
- Reference only the table names registered in `_register_tables()`.
- Use DuckDB-compatible SQL (most standard SQL works; use `DATEDIFF('day', ...)` not `DATE_DIFF`).
- Use DuckDB's `DATE_TRUNC('month', date_field)` for monthly grouping.
- Use `NULLIF(denominator, 0)` in all division operations to prevent division-by-zero.

### Step 2: Add a Route Mapping

In `route_intent_to_query()`, add the mapping from `(domain, intent_type)` to your query key:

```python
static_map: dict[tuple, str] = {
    # ... existing mappings ...

    # Add your new mapping:
    ("changes", "BREAKDOWN"):         "changes.by_category",
    ("changes", "TREND_ANALYSIS"):    "changes.trend_monthly",
    ("changes", "METRIC_SNAPSHOT"):   "changes.summary_kpi",
}
```

For breakdown queries that need dimension-aware routing, add a picker function:

```python
def _pick_change_breakdown(dimensions: list[str]) -> str:
    if "change_type" in dimensions: return "changes.by_type"
    if "site_name" in dimensions: return "changes.by_site"
    return "changes.by_category"  # default
```

And register it in the breakdown dispatch:
```python
breakdown_dispatch = {
    # ... existing pickers ...
    "changes": _pick_change_breakdown,
}
```

### Step 3: Add a Domain Fallback

In the domain-level fallbacks dict, add:
```python
fallbacks = {
    # ... existing ...
    "changes": "changes.by_category",
}
```

### Step 4: Add Domain to the Ontology

In `intent_engine.py`, update the `ONTOLOGY_CONTEXT` system prompt to include the new domain and its metrics:

```python
ONTOLOGY_CONTEXT = """
...
AVAILABLE METRICS (use exact keys):
  ...
  Change:     total_changes, avg_cycle_days, emergency_rate_pct, regulatory_impact_rate_pct

AVAILABLE DIMENSIONS (use exact keys):
  ...
  change_category, change_type
...
"""
```

### Step 5: Add Follow-Up Suggestions

In `main.py`, add follow-up suggestions for the new domain in `_generate_followups()`:

```python
followup_map = {
    # ... existing ...
    "changes": {
        "BREAKDOWN": [
            "Show the trend over time",
            "Which changes have regulatory impact?",
            "Show average cycle time by type"
        ],
    },
}
```

### Step 6: Test

```bash
# Test your new query directly
python -c "
from chatbot.services.query_engine import execute_query
results = execute_query('changes.by_category')
print(results[:3])
"

# Test via the API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Show change requests by category", "user_id": "test"}'
```

---

## Adding New Agents

Follow this template to add a new agent.

### Step 1: Create the Agent File

Create `chatbot/agents/my_new_agent.py`:

```python
"""
My New Agent — Description of what this agent monitors/does.
Trigger: Scheduled / Event-triggered
Autonomy Level: 1 / 2 / 3
"""
import json
from datetime import datetime, timezone
from chatbot.services.query_engine import execute_query, get_conn
from chatbot.services.intent_engine import _call_groq

AGENT_ID = "AGENT-MY-NEW"

# Define the rules this agent evaluates
RULES = [
    {
        "rule_id": "MY-RULE-001",
        "description": "Description of what this rule checks",
        "regulatory_ref": "21 CFR 211.XXX",
    }
]


def run_agent(trigger_data: dict = None) -> dict:
    """
    Main agent execution function.
    Returns: dict with findings, notifications_sent, audit_entry
    """
    run_id = f"RUN-{AGENT_ID}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    findings = []

    # Step 1: Fetch relevant data
    data = execute_query("your.query_key")

    # Step 2: Apply rules
    for row in data:
        if _rule_fires(row):
            findings.append({
                "rule_id": "MY-RULE-001",
                "evidence": row,
                "regulatory_ref": RULES[0]["regulatory_ref"],
                "recommended_action": "Description of what to do"
            })

    # Step 3: Generate narrative if findings exist
    narrative = ""
    if findings:
        narrative = _generate_alert_narrative(findings)

    # Step 4: Send notifications (findings only)
    notifications_sent = []
    if findings:
        notifications_sent = _send_notifications(findings, narrative)

    # Step 5: Write audit trail (ALWAYS — even if no findings)
    audit_entry = {
        "event": "AGENT_RUN",
        "agent_id": AGENT_ID,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rules_evaluated": len(RULES),
        "findings_count": len(findings),
        "notifications_sent": notifications_sent,
    }
    _write_audit_trail(audit_entry)

    return {
        "run_id": run_id,
        "findings": findings,
        "narrative": narrative,
        "notifications_sent": notifications_sent,
        "audit_entry": audit_entry,
    }


def _rule_fires(row: dict) -> bool:
    """Implement your rule logic here."""
    return False  # Replace with actual logic


def _generate_alert_narrative(findings: list[dict]) -> str:
    """Use Groq to generate a structured alert narrative."""
    system = "You are a Pharma Compliance BI agent. Generate a concise, actionable alert."
    prompt = f"Findings:\n{json.dumps(findings[:5], indent=2)}\n\nGenerate a 3-sentence alert."
    return _call_groq(system, [{"role": "user", "content": prompt}], max_tokens=512)


def _send_notifications(findings: list[dict], narrative: str) -> list[str]:
    """
    Send notifications to relevant stakeholders.
    Replace with real notification service in production.
    """
    print(f"[{AGENT_ID}] NOTIFICATION: {narrative[:200]}")
    return ["console_log"]


def _write_audit_trail(entry: dict) -> None:
    """
    Write to audit log. Replace with persistent store in production.
    """
    print(f"[AUDIT] {json.dumps(entry)}")
```

### Step 2: Register a Schedule or Trigger

Add the agent to `chatbot/main.py`:

```python
from chatbot.agents.my_new_agent import run_agent as run_my_agent

@app.post("/agents/my-new/trigger")
async def trigger_my_agent():
    """Manually trigger the agent."""
    result = run_my_agent()
    return result
```

For scheduled execution, add to your scheduler (APScheduler or cron):
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(run_my_agent, "interval", minutes=30)
scheduler.start()
```

---

## API Reference

### POST /chat

Execute a compliance query in natural language.

**Request:**
```json
{
  "query": "string (required) — Natural language query, max 2000 chars",
  "session_id": "string (optional) — UUID of existing session",
  "user_id": "string (optional, default: 'default_user')"
}
```

**Response (200):**
```json
{
  "session_id": "uuid",
  "turn_id": 1,
  "user_query": "string",
  "intent": {
    "intent": "METRIC_SNAPSHOT|TREND_ANALYSIS|...",
    "domain": "capa|deviations|training|...",
    "metrics": ["metric_key"],
    "dimensions": ["dimension_key"],
    "time_filter": {"type": "relative|absolute", "value": "description"},
    "filters": [{"field": "name", "op": "eq|gt|in", "value": "val"}],
    "viz_type": "bar_chart|line_chart|..."
  },
  "narrative": "AI-written insight text",
  "viz_type": "string",
  "viz_spec": {},
  "data": [{}],
  "suggested_followups": ["q1", "q2", "q3"],
  "error": null
}
```

**Error responses:**
- `422 Unprocessable Entity` — Invalid request body (missing required fields)
- `500 Internal Server Error` — Unhandled exception (see traceback in detail field)

---

### GET /sessions

List all sessions for a user.

**Query parameters:** `user_id` (string, default: "default_user")

**Response (200):**
```json
[
  {
    "session_id": "uuid",
    "created_at": "2026-04-03T09:30:00Z",
    "turn_count": 5,
    "last_query": "Show CAPA trend",
    "last_domain": "capa"
  }
]
```

---

### GET /sessions/{session_id}/history

Get all turns for a session.

**Path parameters:** `session_id` (string, required)
**Query parameters:** `user_id` (string, default: "default_user")

**Response (200):**
```json
[
  {
    "turn_id": 1,
    "user_query": "What is our CAPA on-time closure rate?",
    "intent_type": "METRIC_SNAPSHOT",
    "domain": "capa",
    "narrative": "Your overall CAPA on-time closure rate is...",
    "viz_type": "metric_card",
    "row_count": 1,
    "timestamp": "2026-04-03T09:30:01Z"
  }
]
```

---

### GET /health

Service liveness check.

**Response (200):**
```json
{"status": "ok", "service": "pharma-compliance-bi-chatbot"}
```

---

### GET /example-queries

Returns a catalog of example queries organized by domain.

**Response (200):**
```json
{
  "capa": ["query1", "query2", ...],
  "deviations": ["query1", ...],
  "audit": [...],
  "training": [...],
  "supplier": [...],
  "risk": [...],
  "regulatory": [...]
}
```

---

## Common Errors and Fixes

### Error: `GROQ_API_KEY` not found

```
KeyError: 'GROQ_API_KEY'
```

**Fix:** Ensure `.env` exists in the project root and contains `GROQ_API_KEY=your_key`. Restart the server after editing `.env`.

---

### Error: DuckDB — table not found

```
CatalogException: Table with name capa_records does not exist!
```

**Fix:** The CSV file for this table is missing from `/data/csv/`. Run the data generator:
```bash
python -m data.generators.generate_compliance_data
```

---

### Error: `ModuleNotFoundError: No module named 'chatbot'`

```
ModuleNotFoundError: No module named 'chatbot'
```

**Fix:** Run uvicorn from the project root directory, not from inside the `chatbot/` subdirectory:
```bash
# Correct (from project root):
cd pharma-compliance-bi
uvicorn chatbot.main:app --reload

# Wrong (from inside chatbot/):
cd chatbot
uvicorn main:app --reload  # won't work
```

---

### Error: Port 8000 already in use

```
ERROR:    [Errno 48] Address already in use
```

**Fix:** Use a different port:
```bash
uvicorn chatbot.main:app --reload --port 8001
```
Or kill the existing process using port 8000:
```bash
# macOS/Linux:
lsof -ti:8000 | xargs kill -9

# Windows:
netstat -ano | findstr :8000
# Then: taskkill /PID <pid> /F
```

---

### Error: Groq API rate limit

```
groq.RateLimitError: Rate limit reached for model llama-3.3-70b-versatile
```

**Fix:** The free Groq tier has rate limits. Either:
- Wait a few seconds and retry
- Upgrade your Groq plan
- Reduce the `max_tokens` parameter in `_call_groq()` calls

---

### Error: Intent returns `{"error": "Could not parse intent", "raw": ...}`

**Symptom:** The chatbot responds "I couldn't understand that query."

**Fix options:**
1. Check that the Groq API key is valid and has credits
2. Check the `raw` field in the error response to see what the LLM returned
3. Check `GROQ_MODEL` environment variable — invalid model names cause this
4. Add LOG_LEVEL=DEBUG to `.env` and check server logs for the raw Groq response

---

### Error: `pandas is not installed` or `duckdb is not installed`

**Fix:**
```bash
pip install -r config/requirements.txt
```

Ensure your virtual environment is activated before running pip.

---

## Contribution Guidelines

### Code Style

- Python: Follow PEP 8. Use `black` for formatting (`pip install black && black chatbot/`).
- Type hints: All function signatures should have type annotations.
- Docstrings: Module-level and function-level docstrings are required for all service files.
- Naming: Use `snake_case` for functions and variables. Query keys use `domain.description` format.

### Branching Strategy

- `main` — stable, deployable code only
- `develop` — integration branch for active features
- `feature/description` — individual feature branches

Create a pull request from `feature/*` into `develop`. Merges to `main` require review.

### Commit Message Format

```
<type>: <short description>

<optional longer description>

<optional related issues>
```

Types: `feat` (new feature), `fix` (bug fix), `refactor`, `docs`, `test`, `chore`.

Examples:
```
feat: add change_requests domain to query engine

Adds 3 new query keys (changes.by_category, changes.trend_monthly,
changes.summary_kpi) and routing rules for the changes domain.
```

### Adding a New Query Type — Checklist

Before submitting a PR for a new query type, verify:

- [ ] SQL query added to `QUERY_LIBRARY` with correct naming convention
- [ ] Route mapping added to `static_map` in `route_intent_to_query()`
- [ ] Domain fallback added to `fallbacks` dict
- [ ] Domain metrics and dimensions added to `ONTOLOGY_CONTEXT` in intent_engine.py
- [ ] Follow-up suggestions added in `_generate_followups()` in main.py
- [ ] Unit test added in `tests/test_query_engine.py`
- [ ] SQL tested manually against generated data
- [ ] API integration test run and response verified

### Environment for Testing

For automated testing (CI/CD), set:
```env
GROQ_API_KEY=test_mock_key  # triggers graceful fallback in intent engine
```

Tests that call the Groq API should be marked `@pytest.mark.integration` and excluded from the fast test suite.

---

*Developer Guide: Compliance BI Platform Team | April 2026*
*For questions: open a GitHub issue or contact the platform team*
