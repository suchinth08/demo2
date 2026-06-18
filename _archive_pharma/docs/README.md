# Compliance BI — Documentation Hub

> **Compliance BI** — AI-powered compliance intelligence for the modern pharmaceutical enterprise.
> From natural language queries to autonomous agents, we close the gap between your data and the decisions that keep patients safe.

---

## What Is Compliance BI?

Compliance BI is an AI-native platform that transforms how pharmaceutical quality and compliance teams interact with their data. Instead of navigating spreadsheets and BI dashboards, users ask questions in plain English. Instead of manually checking policy, a rules engine does it continuously. Instead of compliance teams discovering issues after audits, autonomous agents surface them in real time.

The platform is built on three tightly integrated capability layers:

| Layer | Feature | What It Does |
|---|---|---|
| 1 | **AI BI Chatbot** | Natural language queries over CAPA, Deviations, Audits, Training, Supplier Quality, Risk, and Regulatory data — returning charts, tables, and AI-written narratives |
| 2 | **Policy as a Service** | A programmable rules engine that continuously evaluates live compliance data against FDA 21 CFR, ICH Q9/Q10, and internal SOPs — surfacing violations, gaps, and risk scores in real time |
| 3 | **Agentic Compliance Actions** | Seven autonomous AI agents that monitor the compliance landscape, draft CAPAs, cascade training, generate QMRs, assess inspection readiness, and investigate root causes — with human approval gates at every critical step |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A Groq API key (free tier works for development)
- Git

### Five-minute setup

```bash
# 1. Clone and install
git clone <repo-url> pharma-compliance-bi
cd pharma-compliance-bi
pip install -r config/requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add GROQ_API_KEY=your_key_here

# 3. Generate sample compliance data
python -m data.generators.generate_compliance_data

# 4. Launch
uvicorn chatbot.main:app --reload --port 8000

# 5. Open the UI
open http://localhost:8000
```

The chatbot is immediately usable. Try: *"What is our CAPA on-time closure rate by site?"*

---

## Documentation Map

### Executive & Business

| Document | Audience | Description |
|---|---|---|
| [Platform Executive Overview](executive/00_platform_executive_overview.md) | Leadership, Steering Committee | Business case, ROI, roadmap, risk mitigations |
| [AI BI Chatbot — Executive Deck](executive/01_bi_chatbot_exec.md) | QA VPs, Compliance Directors | Feature value, demo scenarios, business impact |
| [Policy as a Service — Executive Deck](executive/02_policy_as_service_exec.md) | Regulatory Affairs, QA Leadership | Policy automation value, regulatory coverage |
| [Agentic Compliance — Executive Deck](executive/03_agentic_compliance_exec.md) | Operations, QA Leadership | Agent capabilities, autonomy model, governance |

### Architecture & Design

| Document | Audience | Description |
|---|---|---|
| [System Architecture](architecture/system_architecture.md) | Engineers, Architects, IT Security | Full technical architecture, data flows, security |
| [Agent Workflows](architecture/agent_workflows.md) | Engineers, QA SMEs | Step-by-step agent execution, tool registry, memory |

### Requirements

| Document | Audience | Description |
|---|---|---|
| [Functional Requirements](requirements/functional_requirements.md) | Product, Engineering, QA | 40+ formal requirements (FR-001 through FR-045+) |
| [Use Case Catalogue](requirements/use_cases.md) | Product, QA, Testing | 26 use cases across all three features |

### Data

| Document | Audience | Description |
|---|---|---|
| [Data Dictionary](data/data_dictionary.md) | Data Engineers, Analysts, QA | Every table, column, type, constraint, relationship |
| [Data Sources & Integration](data/data_sources.md) | Data Engineers, IT | Source inventory, quality rules, lineage, governance |

### Features

| Document | Audience | Description |
|---|---|---|
| [BI Chatbot User Guide](features/01_bi_chatbot/user_guide.md) | End Users (Compliance Officers, QA Analysts) | Interface walkthrough, 50+ example questions, FAQ |

### Development

| Document | Audience | Description |
|---|---|---|
| [Developer Setup Guide](development/setup_guide.md) | Engineers | Full setup, API reference, adding query types, contributing |

---

## Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Backend API | Python 3.11 + FastAPI | REST API, request handling, session management |
| AI / LLM | Groq — llama-3.3-70b-versatile | Intent extraction, narrative generation, follow-up resolution |
| Query Engine | DuckDB | In-process analytical SQL over CSV/Parquet data files |
| Data Layer | CSV files (production: BigQuery / Snowflake) | Compliance domain data storage |
| Visualization | Vega-Lite v5 | Declarative chart specs rendered in the browser |
| Frontend | HTML5 + Vanilla JS + Lucide Icons | Google Gemini-inspired chat UI |
| Policy Engine | Python rules engine (custom) | Policy evaluation against 21 CFR, ICH Q9/Q10, SOPs |
| Agent Runtime | Python async + Groq tool-calling | Autonomous agent execution with human-in-the-loop gates |
| Session Store | In-memory dict (production: Redis) | Multi-turn conversation context |
| Dependency Management | pip + requirements.txt | Package management |
| Environment Config | python-dotenv | Secret and config management |

---

## Project Structure

```
pharma-compliance-bi/
├── chatbot/                          # Core backend application
│   ├── main.py                       # FastAPI app, /chat, /sessions endpoints
│   └── services/
│       ├── intent_engine.py          # LLM-powered intent extraction (Groq)
│       ├── query_engine.py           # SQL query library + DuckDB execution
│       ├── session_manager.py        # Multi-turn session & context state
│       └── viz_builder.py            # Vega-Lite spec generation
│
├── frontend/                         # Browser UI
│   ├── index.html                    # Single-page chat application
│   └── src/                          # JS modules, CSS
│
├── data/
│   ├── csv/                          # Compliance data files (generated)
│   │   ├── capa_records.csv
│   │   ├── deviation_records.csv
│   │   ├── audit_findings.csv
│   │   ├── training_records.csv
│   │   ├── batch_records.csv
│   │   ├── supplier_inspections.csv
│   │   ├── risk_register.csv
│   │   ├── change_requests.csv
│   │   ├── regulatory_inspections.csv
│   │   ├── regulatory_commitments.csv
│   │   ├── documents.csv
│   │   ├── employees.csv
│   │   ├── departments.csv
│   │   ├── sites.csv
│   │   ├── products.csv
│   │   └── suppliers.csv
│   └── generators/
│       └── generate_compliance_data.py
│
├── schema/
│   └── compliance_schema.sql         # Full database schema (DDL)
│
├── ontology/                         # Domain ontology YAML (metrics, dimensions)
│
├── malloy/                           # Malloy semantic layer definitions
│
├── config/
│   ├── requirements.txt
│   └── example_conversations.md
│
├── docs/                             # This documentation tree
│   ├── README.md                     # This file
│   ├── executive/
│   ├── architecture/
│   ├── requirements/
│   ├── data/
│   ├── features/
│   └── development/
│
├── .env.example                      # Environment variable template
└── server.log
```

---

## Version History

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0 | 2025-01-15 | Platform Team | Initial architecture scaffold, schema design |
| 0.2.0 | 2025-02-01 | Platform Team | Intent engine + query library (CAPA, Deviations, Audit) |
| 0.3.0 | 2025-02-20 | Platform Team | Multi-turn session manager, follow-up intent resolution |
| 0.4.0 | 2025-03-05 | Platform Team | Visualization builder (13 chart types), Vega-Lite integration |
| 0.5.0 | 2025-03-20 | Platform Team | Supplier Quality, Risk, Regulatory query domains added |
| 0.6.0 | 2025-04-01 | Platform Team | Frontend UI (Google Gemini-inspired), Lucide icons |
| 0.7.0 | 2025-04-15 | Platform Team | Policy as a Service engine (Phase 1) |
| 0.8.0 | 2025-05-01 | Platform Team | Agentic framework: Deviation Watcher + CAPA Auto-Drafter |
| 0.9.0 | 2025-06-01 | Platform Team | All 7 agents, QMR generator, Inspection Readiness Agent |
| 1.0.0 | 2025-07-01 | Platform Team | Production release: full documentation, test suite |

---

## Contributing

See [Developer Setup Guide](development/setup_guide.md) for contribution guidelines, coding standards, and the process for adding new query types and agents.

---

## License & Regulatory Notice

This platform processes GMP-governed pharmaceutical compliance data. All data access, query execution, and agent actions are logged to an immutable audit trail in compliance with FDA 21 CFR Part 11 requirements for electronic records and electronic signatures.

---

*Documentation last updated: April 2026 | Platform version: 1.0.0*
