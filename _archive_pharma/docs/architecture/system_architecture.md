# System Architecture — Compliance BI Platform

**Document Type: Technical Architecture**
**Version: 1.0 | April 2026**
**Audience: Engineers, Architects, IT Security**

---

## Architecture Overview

Compliance BI is a Python-based, single-process monolith for the current version, designed with clear internal service boundaries to enable future decomposition into microservices. The architecture follows an intent-query-response pipeline pattern for the chatbot, a rule-evaluation pipeline for Policy as a Service, and an event-driven agent loop for the agentic layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│   Browser — index.html (Vanilla JS + Vega-Lite + Lucide Icons)              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  HTTP (REST)
┌────────────────────────────────▼────────────────────────────────────────────┐
│                         FastAPI APPLICATION SERVER                           │
│   uvicorn (ASGI) — Port 8000                                                │
│                                                                              │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────────────┐ │
│  │  /chat           │  │  /sessions        │  │  /health                 │ │
│  │  POST endpoint   │  │  /sessions/{id}/  │  │  /example-queries        │ │
│  │  Main chatbot    │  │  history          │  │  Static file serving     │ │
│  │  pipeline        │  │  GET endpoints    │  │  (frontend)              │ │
│  └────────┬─────────┘  └───────────────────┘  └──────────────────────────┘ │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────────────────┐
│                          CORE SERVICES LAYER                                 │
│                                                                              │
│  ┌──────────────────────────┐    ┌──────────────────────────────────────┐  │
│  │   INTENT ENGINE          │    │    QUERY ENGINE                      │  │
│  │   intent_engine.py       │    │    query_engine.py                   │  │
│  │                          │    │                                      │  │
│  │  • extract_intent()      │    │  • route_intent_to_query()           │  │
│  │  • _looks_like_followup()│    │  • execute_query()                   │  │
│  │  • build_insight_        │    │  • QUERY_LIBRARY (SQL dict)          │  │
│  │    narrative()           │    │  • DuckDB connection pool            │  │
│  │  • Groq API calls        │    │                                      │  │
│  └──────────────┬───────────┘    └──────────────────────────────────────┘  │
│                 │                                                            │
│  ┌──────────────▼───────────┐    ┌──────────────────────────────────────┐  │
│  │   SESSION MANAGER        │    │    VISUALIZATION BUILDER             │  │
│  │   session_manager.py     │    │    viz_builder.py                    │  │
│  │                          │    │                                      │  │
│  │  • Session (dataclass)   │    │  • build_viz_spec() router           │  │
│  │  • ConversationTurn      │    │  • 13 chart builders                 │  │
│  │  • In-memory store       │    │  • Vega-Lite JSON generation         │  │
│  │  • Context threading     │    │                                      │  │
│  └──────────────────────────┘    └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
            │                                    │
┌───────────▼────────────────────┐  ┌────────────▼──────────────────────────┐
│        AI / LLM LAYER          │  │         DATA LAYER                     │
│                                │  │                                        │
│  Groq API (external)           │  │  DuckDB (in-process)                  │
│  Model: llama-3.3-70b-         │  │  16 tables registered as views        │
│  versatile                     │  │  over CSV files in /data/csv/         │
│                                │  │                                        │
│  Used for:                     │  │  CSV files (current):                 │
│  • Intent extraction           │  │  capa_records.csv                     │
│  • Follow-up resolution        │  │  deviation_records.csv                │
│  • Insight narrative gen.      │  │  audit_findings.csv                   │
│  Temperature: 0.1 (consistent) │  │  training_records.csv                 │
│  Max tokens: 1024 / 512        │  │  batch_records.csv ... (16 total)     │
│                                │  │                                        │
└────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. FastAPI Application Server (`chatbot/main.py`)

**Responsibilities:**
- HTTP request routing and response serialization
- CORS middleware (permissive in development; scoped in production)
- Static file serving for the frontend single-page application
- Request validation via Pydantic models (`ChatRequest`, `ChatResponse`)
- Orchestration of the 7-step chat pipeline
- Follow-up question generation (`_generate_followups`)
- Safe JSON serialization of date/datetime objects (`_safe_serialize`)
- Error handling and HTTP exception propagation

**Key endpoints:**
- `POST /chat` — Main chatbot endpoint; accepts `query`, `session_id`, `user_id`
- `GET /sessions` — Lists all sessions for a user
- `GET /sessions/{session_id}/history` — Returns conversation turns for a session
- `GET /health` — Service liveness check
- `GET /example-queries` — Returns domain-organized example question catalog
- `GET /` — Serves the frontend `index.html`
- `GET /static/*` — Serves frontend assets

**Data models:**

```python
ChatRequest:
  query: str           # The user's natural language question
  session_id: str?     # Optional — creates new session if absent
  user_id: str         # User identifier for session scoping

ChatResponse:
  session_id: str      # Session this turn belongs to
  turn_id: int         # Sequential turn number
  user_query: str      # Echo of the input query
  intent: dict         # Structured intent JSON from LLM
  narrative: str       # AI-written insight text
  viz_type: str        # Chart type identifier
  viz_spec: dict       # Vega-Lite specification JSON
  data: list[dict]     # Raw query results (capped at 50 rows)
  suggested_followups: list[str]
  error: str?          # Query error if data retrieval failed
```

---

### 2. Intent Engine (`chatbot/services/intent_engine.py`)

**Responsibilities:**
- Determining whether a query is a fresh question or a follow-up (via `_looks_like_followup`)
- Constructing the appropriate system prompt (ontology context or follow-up resolution)
- Calling the Groq API with conversation history for context
- Parsing and validating the JSON intent structure from the LLM response
- Generating insight narratives from query results

**Intent schema (what the LLM must return):**

```json
{
  "intent": "METRIC_SNAPSHOT | TREND_ANALYSIS | BREAKDOWN | RANKING | ...",
  "domain": "capa | deviations | audit_findings | training | ...",
  "metrics": ["capa_on_time_closure_rate"],
  "dimensions": ["site_name"],
  "time_filter": {"type": "relative", "value": "rolling 12 months"},
  "filters": [{"field": "site_id", "op": "eq", "value": "SITE-EU-02"}],
  "sort": {"field": "overdue_capas", "dir": "desc"},
  "limit": null,
  "viz_type": "horizontal_bar",
  "nl_response_hint": "Emphasize the overdue outlier site"
}
```

**11 intent types:** `METRIC_SNAPSHOT`, `TREND_ANALYSIS`, `BREAKDOWN`, `RANKING`, `COMPARISON`, `ANOMALY_DETECTION`, `DRILL_DOWN`, `OVERDUE_ALERT`, `RISK_ASSESSMENT`, `COMPLIANCE_SCORE`, `REGULATORY_STATUS`

**Groq API parameters:**
- Model: `llama-3.3-70b-versatile`
- Temperature: 0.1 (minimizes non-deterministic output in structured extraction)
- Max tokens: 1024 for intent extraction, 512 for narrative generation
- Conversation history: Last 3 turns (6 messages: user + assistant pairs)

---

### 3. Query Engine (`chatbot/services/query_engine.py`)

**Responsibilities:**
- Maintaining a library of pre-built, named SQL queries (`QUERY_LIBRARY` dict)
- Routing structured intent to the appropriate query key (`route_intent_to_query`)
- Executing queries against DuckDB with optional dynamic WHERE filters
- Registering all 16 data tables as DuckDB views at startup

**Query routing logic:**
1. Static map lookup: `(domain, intent_type)` → `query_key` (covers ~80% of cases)
2. Dimension-aware breakdown dispatch: for `BREAKDOWN` intents where the choice depends on which dimension was requested
3. Domain-level fallback: if no specific match, use the primary summary query for the domain

**Dynamic filter injection:**
The engine can inject additional WHERE conditions into any query based on intent filters:
- String values → `field = 'value'`
- List values → `field IN ('v1', 'v2')`
- Range values → `field >= 'value'`
- Injection appended to existing WHERE clause or inserted before GROUP BY/ORDER BY

**Query library coverage (as of v1.0):**

| Domain | Query Keys |
|---|---|
| CAPA | `capa.summary_kpi`, `capa.by_site`, `capa.by_department`, `capa.by_root_cause`, `capa.trend_monthly`, `capa.overdue_list` |
| Deviations | `deviations.by_site`, `deviations.pareto_root_cause`, `deviations.trend_monthly`, `deviations.by_category` |
| Audit Findings | `audit_findings.by_site`, `audit_findings.by_process_area`, `audit_findings.by_regulatory_ref` |
| Training | `training.by_site`, `training.by_department`, `training.overdue_list` |
| Supplier Quality | `supplier_quality.scorecard`, `supplier_quality.rejection_trend` |
| Risk | `risk.top_risks`, `risk.by_category`, `risk.matrix` |
| Batches | `batches.by_site`, `batches.trend_quarterly` |
| Regulatory | `regulatory.inspection_history`, `regulatory.open_commitments` |

---

### 4. Session Manager (`chatbot/services/session_manager.py`)

**Responsibilities:**
- Creating and retrieving sessions keyed by UUID
- Storing `ConversationTurn` objects with full context
- Maintaining active context (domain, metrics, dimensions, filters, time filter) across turns
- Providing conversation history as LLM-digestible format (last 5 turns)

**Session data model:**
```python
Session:
  session_id: str       # UUID
  user_id: str          # Who owns this session
  created_at: datetime
  turns: list[ConversationTurn]
  active_domain: str?          # Last queried domain
  active_metrics: list[str]    # Last used metrics
  active_dimensions: list[str] # Last used dimensions
  active_filters: list[dict]   # Inherited filters
  active_time_filter: dict?    # Inherited time filter

ConversationTurn:
  turn_id: int
  user_query: str
  intent: dict
  query_key: str
  result_rows: list[dict]
  narrative: str
  viz_type: str
  viz_spec: dict
  timestamp: datetime
  parent_turn_id: int?  # For follow-up threading
```

**Current storage:** In-memory Python dict — suitable for development and single-instance deployment. Session data is lost on server restart.

**Production replacement:** Redis (with JSON serialization) or a persistent store, enabling multi-instance deployment and session persistence across restarts.

---

### 5. Visualization Builder (`chatbot/services/viz_builder.py`)

**Responsibilities:**
- Routing to the appropriate chart builder based on `viz_type`
- Generating complete Vega-Lite v5 JSON specifications
- Auto-detecting field types (temporal, categorical, quantitative) from data
- Providing fallback specifications when data is empty

**Supported visualization types:**

| viz_type | Chart | Optimal Use Case |
|---|---|---|
| `metric_card` | KPI card(s) | Single metric snapshots |
| `line_chart` | Multi-series line | Time series, trends |
| `bar_chart` | Vertical bar | Categorical breakdown |
| `horizontal_bar` | Horizontal bar | Rankings (top-N) |
| `grouped_bar` | Grouped bars | Comparisons |
| `pie` | Donut chart | Composition / share |
| `heatmap` | 2D rect heatmap | Matrix views |
| `scatter` | Scatter plot | Correlation analysis |
| `risk_matrix` | Bubble scatter | ICH Q9 S×O risk matrix |
| `radar_chart` | Radar / spider | Multi-dimension scores |
| `data_table` | Sortable table | Drill-down detail |
| `table_with_rag` | RAG-colored table | Overdue alerts |
| `timeline` | Event timeline | Regulatory history |

---

## Request Flow — Step-by-Step (Chat Query)

```
Client: POST /chat
  body: { "query": "Show overdue CAPAs by site", "session_id": "abc-123", "user_id": "user@company.com" }
  │
  ▼ STEP 1: Session Resolution
  get_or_create_session("abc-123", "user@company.com")
  → Returns existing Session object with prior turn history
  │
  ▼ STEP 2: Intent Extraction (Groq API call #1)
  extract_intent(
    user_query = "Show overdue CAPAs by site",
    conversation_history = [last 3 turns],
    prior_intent = {previous intent JSON}
  )
  → _looks_like_followup("Show overdue CAPAs by site") → False (fresh query)
  → Groq API called with ONTOLOGY_CONTEXT system prompt + conversation history
  → Returns intent JSON:
    { "intent": "OVERDUE_ALERT", "domain": "capa", "dimensions": ["site_name"],
      "viz_type": "table_with_rag", ... }
  │
  ▼ STEP 3: Query Routing
  route_intent_to_query(intent)
  → Static map: ("capa", "OVERDUE_ALERT") → "capa.overdue_list"
  → extra_filters: {} (no additional filters in this query)
  → Returns ("capa.overdue_list", None)
  │
  ▼ STEP 4: Query Execution (DuckDB)
  execute_query("capa.overdue_list", None)
  → Retrieves SQL from QUERY_LIBRARY["capa.overdue_list"]
  → DuckDB executes against capa_records view (reads capa_records.csv)
  → Joins with sites, departments
  → Returns list of dicts: [{capa_id, severity, site_name, dept_name, age_days, ...}, ...]
  │
  ▼ STEP 5: Visualization Spec Generation
  build_viz_spec("table_with_rag", data, intent)
  → Builds sortable data table spec with RAG coloring enabled
  → rag_field = "age_days" (or compliance rate field if present)
  → Returns Vega-Lite-compatible dict
  │
  ▼ STEP 6: Narrative Generation (Groq API call #2)
  build_insight_narrative(intent, {"data": data[:10]}, user_query)
  → Groq API called with pharma compliance analyst system prompt
  → Returns 3-5 sentence insight narrative highlighting overdue pattern,
    worst-performing site, regulatory risk flag, and follow-up question
  │
  ▼ STEP 7: Follow-Up Generation
  _generate_followups(intent, data)
  → Maps ("capa", "OVERDUE_ALERT") to suggested follow-ups
  → Returns 3 contextual suggestions
  │
  ▼ STEP 8: Session Storage
  session.add_turn(ConversationTurn(...))
  → Updates active_domain, active_metrics, active_dimensions
  → Appends turn to session history
  │
  ▼ STEP 9: Response Serialization
  _safe_serialize(data[:50])  # Cap at 50 rows for response size
  → Converts date objects to ISO strings
  │
  ▼ Response: 200 OK
  { session_id, turn_id, user_query, intent, narrative, viz_type, viz_spec,
    data, suggested_followups }
```

---

## Data Flow Diagram

```
External Data Sources (future)         Current Data Layer
EQMS (Veeva Vault) ──►                 ┌──────────────────────────────┐
LIMS ─────────────────► (Phase 2)      │  /data/csv/                  │
SAP ERP ──────────────► connectors     │  ├── capa_records.csv        │
EDMS ─────────────────►                │  ├── deviation_records.csv   │
                                        │  ├── audit_findings.csv      │
                                        │  ├── audits.csv              │
Data Generator ──────────────────────► │  ├── training_records.csv    │
generate_compliance_data.py             │  ├── batch_records.csv       │
(synthetic for development)             │  ├── supplier_inspections.csv│
                                        │  ├── suppliers.csv           │
                                        │  ├── risk_register.csv       │
                                        │  ├── change_requests.csv     │
                                        │  ├── regulatory_*.csv        │
                                        │  ├── documents.csv           │
                                        │  ├── employees.csv           │
                                        │  ├── departments.csv         │
                                        │  ├── sites.csv               │
                                        │  └── products.csv            │
                                        └──────────────┬───────────────┘
                                                       │ read_csv_auto()
                                        ┌──────────────▼───────────────┐
                                        │    DuckDB In-Process Engine  │
                                        │    16 views registered       │
                                        │    SQL query execution        │
                                        │    Result: list[dict]         │
                                        └──────────────────────────────┘
```

---

## Session & State Management

### Current Architecture (In-Memory)

Sessions are stored in a Python dictionary keyed by UUID session ID. State is maintained as a `Session` dataclass with a list of `ConversationTurn` objects.

**Context threading across turns:**
When a new turn is added, the session updates its "active context" — the domain, metrics, dimensions, filters, and time filter from the latest intent. On the next follow-up question, `extract_intent` receives the prior intent JSON so the Groq model can resolve references like "now break it down by site" correctly.

**Limitations of current approach:**
- Sessions lost on server restart
- No cross-instance session sharing (single-process only)
- Memory grows unboundedly for long-running processes (no TTL)

**Production upgrade path:**
Replace `_sessions: dict[str, Session]` with a Redis client. Session dataclass serializes to/from JSON. TTL set to 24 hours per session. This change requires no modifications to any calling code — only `session_manager.py` changes.

---

## Security Architecture

### Authentication (Current)
No authentication is enforced in the current development version. The `user_id` parameter in `ChatRequest` is accepted as-is without verification.

**Production requirement:** All endpoints must be protected by OAuth 2.0 / OpenID Connect. The `/chat` endpoint must require a valid JWT bearer token. User identity in the token must match the `user_id` parameter.

### Authorization
**Current:** None — all authenticated users see all data.

**Production requirement:** Row-level security based on user's site assignments. A site-level QA analyst should only see data for their assigned site(s). A global QA Director should see all sites. Authorization should be enforced at the query engine layer by injecting site-scoping filters based on the authenticated user's permissions, not at the API layer.

### Data Access Control
- All data queries execute against DuckDB views over CSV files in the `/data/csv/` directory
- The DuckDB connection is read-only (no INSERT, UPDATE, or DELETE operations are possible from the query engine)
- SQL injection mitigation: the query engine uses a named-query library approach — user input (the query string) never directly touches SQL. User input flows only to the Groq API for intent extraction; the resulting intent JSON is mapped to a pre-written query key, not interpolated into SQL.
- Dynamic filter injection uses parameterized-style value substitution with type checking

### Audit Trail
All `/chat` calls are logged with: timestamp, user_id, session_id, turn_id, raw query string, extracted intent (domain, intent type), query key executed, row count returned, narrative generated. This log is the foundation of the 21 CFR Part 11 audit trail.

### API Key Management
- Groq API key stored in `.env` file, loaded via `python-dotenv`
- Never included in source code or logged
- Production: use a secrets manager (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)

---

## Integration Architecture

### Current Integration Model
The platform reads from flat CSV files via DuckDB. This is the simplest possible data integration — no real-time synchronization, no change data capture.

### Phase 2: Direct System Integration

```
EQMS ──► REST API ──► Data Connector Service ──► DuckDB (live query) or
LIMS ──► REST API ──►     (Python async)     ──► Parquet/Arrow cache
```

Connector service design:
- Pull-based: periodic refresh (configurable per source — every 15 minutes for CAPA/Deviations, hourly for Training/Risk)
- Incremental: only changed records fetched using `updated_at` watermarks
- Schema mapping: source-system field names mapped to Compliance BI schema
- Data quality validation: completeness rules applied at ingestion
- Failure handling: last-good-data policy — serve stale data rather than errors

### Phase 3: Event-Driven Integration

For agent triggers, a message queue (Kafka or AWS SQS) will receive events from EQMS and trigger agent workflows immediately rather than waiting for the next polling cycle.

---

## Scalability Design

### Current Bottlenecks
1. **DuckDB connection:** Single shared connection. DuckDB is single-writer by design. For read queries, this is fine for moderate concurrency.
2. **Groq API:** External API call adds 200–800ms latency. With 10+ concurrent users, API rate limits may bind.
3. **In-memory sessions:** All sessions held in process memory. Bounded by single-process RAM.

### Scaling Approach

| Bottleneck | Horizontal Scale Solution |
|---|---|
| DuckDB | Separate read-replica DuckDB instances per API process; or migrate to MotherDuck/BigQuery/Snowflake for production |
| Groq API | Request caching for identical queries (LRU cache on intent+query_key); add retry with exponential backoff |
| Session store | Redis cluster with JSON serialization |
| API server | Multiple uvicorn workers behind nginx; stateless design (sessions in Redis, not process memory) |

**Target throughput:** 200 concurrent users, <3 second end-to-end response time for 95th percentile queries.

---

## Technology Decision Log

| Decision | Technology Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| LLM provider | Groq (llama-3.3-70b-versatile) | OpenAI GPT-4o, Azure OpenAI, local Ollama | Groq provides the fastest inference for open-weight models; llama-3.3-70b delivers GPT-4-class performance at significantly lower cost; no data retention by default |
| Backend framework | FastAPI | Flask, Django, Express.js | FastAPI provides automatic OpenAPI docs, native async, Pydantic validation, and is the industry standard for Python AI APIs |
| Analytical database | DuckDB | SQLite, PostgreSQL, BigQuery | DuckDB is purpose-built for in-process analytical SQL; zero infrastructure; reads CSVs/Parquet natively; easily swappable to BigQuery/Snowflake via connector |
| Visualization | Vega-Lite | Chart.js, D3, Recharts, Plotly | Vega-Lite is a declarative spec — the backend generates the entire chart specification as JSON, decoupling chart generation from rendering. Zero chart library code on the frontend for standard types |
| Frontend | Vanilla JS | React, Vue, Angular | Minimizes build toolchain complexity; enables direct serving from FastAPI static files; suitable for the current single-page application scope |
| Python version | Python 3.11 | 3.9, 3.10, 3.12 | 3.11 provides significant performance improvements over 3.10; union type syntax (`dict | None`) is idiomatic; wide library support |
| Session storage | In-memory dict | Redis, PostgreSQL, DynamoDB | Simplest correct implementation for single-process development; Redis replacement is a 1-file change |

---

## Deployment Architecture

### Development (Current)
```
Developer machine
└── uvicorn chatbot.main:app --reload --port 8000
    └── All services in single process
    └── CSV files read from /data/csv/
    └── .env file with GROQ_API_KEY
```

### Production (Target — Phase 3)
```
Load Balancer (nginx)
    │
    ├── API Server Pod 1 (uvicorn, 4 workers)
    ├── API Server Pod 2 (uvicorn, 4 workers)
    └── API Server Pod N (auto-scale)
         │
         ├── Redis (session store, shared across pods)
         ├── DuckDB / MotherDuck / BigQuery (analytical queries)
         └── Groq API (external, load-balanced with fallback)

Data Pipeline (separate process):
    EQMS ──► Connector Service ──► Data Lake (S3/ADLS) ──► BigQuery/Snowflake
```

---

## Monitoring & Observability

### Application Metrics to Track

| Metric | Collection Method | Alert Threshold |
|---|---|---|
| `/chat` endpoint latency (p50, p95, p99) | Middleware timing | p95 > 5 seconds |
| Groq API call latency | Timing in `_call_groq()` | p95 > 3 seconds |
| Groq API error rate | Exception count | >2% of calls |
| Intent extraction failure rate | `"error" in intent` count | >5% of queries |
| Query execution time | DuckDB timing | p95 > 1 second |
| Active sessions count | `len(_sessions)` | Monitor for growth |
| Requests per minute | ASGI middleware | Alert on unusual spike or drop |

### Logging
All requests are logged to `server.log` with: timestamp, method, path, status code, response time, user_id, session_id, domain, intent type, query key, row count. Log format is structured JSON for downstream analysis.

### Health Check
`GET /health` returns `{"status": "ok", "service": "pharma-compliance-bi-chatbot"}`. Used by load balancers and container orchestrators for liveness probing.

---

*Architecture Lead: Compliance BI Platform Team | April 2026*
*Next review: July 2026 (prior to Phase 2 deployment)*
