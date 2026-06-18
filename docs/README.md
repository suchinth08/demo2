# Ask Liquid Data — Market Insights AI

> Conversational, agentic AI for **CPG and General Merchandise** market insights.
> A working reference implementation of the three-layer AI-for-BI pattern, configured
> for the Circana measurement vocabulary — share, velocity, distribution, promo, panel,
> innovation, category health.

---

## What this project is

**Ask Liquid Data** is the first vertical of a reusable AI-for-BI reference architecture.
It demonstrates Layer 1 of the three-layer pattern — a natural-language conversational BI
chatbot over CPG / GM market measurement data. The platform is designed to grow into
Layer 2 (policy / commercial-guardrails engine) and Layer 3 (autonomous agents:
Auto-MBR Generator, Share-Movement Watcher, Pacesetter Watch, Top-to-Top Readiness, etc).

### What you can ask it today

| Domain | Example question |
|---|---|
| Share | *"Which brands are losing share in Energy Drinks?"* |
| Share movement | *"Top 10 share gainers across all CPG categories"* |
| Velocity | *"Top 10 brands by velocity"* |
| Distribution | *"Which high-velocity brands have distribution gaps?"* |
| Pricing | *"Show the price index for Energy Drinks vs category average"* |
| Promotion | *"Top promo lift by brand last quarter"* |
| Panel | *"Household penetration ranking across CPG brands"* |
| Innovation | *"Show me the Pacesetter candidates"* |
| Category | *"Which categories are growing fastest?"* |

---

## Quick start

### Prerequisites

- Python 3.11+
- A Groq API key (free tier works for development)

### Five-minute setup

```bash
# 1. Install
pip install -r config/requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set GROQ_API_KEY=your_key_here

# 3. Generate the synthetic CPG/GM market dataset
python -m data.generators.generate_market_data

# 4. Launch
uvicorn chatbot.main:app --reload --port 8000

# 5. Open
# http://localhost:8000
```

Try the welcome chips, or ask: *"Show me the Pacesetter candidates"*.

---

## What's in the data

The synthetic dataset is shaped like a slice of the Circana POS + Panel universe,
with **deliberate demo storylines** baked in for a punchy 5-minute demo:

| Storyline | What you see in the chart |
|---|---|
| **Liquid Death — Pacesetter trajectory** | Launched May 2024, building from 0 → 42% ACV by Dec 2024, +10 pts of share in Sparkling Water |
| **Celsius hyper-growth in Energy Drinks** | ~30% category share by end-2024, accelerating week-over-week |
| **Coca-Cola gaining vs Pepsi in CSDs** | Especially Coke Zero Sugar in Diet CSDs from mid-2024 |
| **Walmart soft in CSDs Q4 2024** | Amazon absorbs the share loss |
| **CeraVe surging in Skincare Cleanser** | Taking share from Olay; over-indexed in Mass and Drug |
| **iPhone 16 launch** | September 2024 volume lift in Smartphones |
| **LEGO holiday spike** | Weeks 45–51 in Building Sets |
| **Barbie movie halo on Mattel** | 2023-H2 through 2024-H1 |

### Data tables

| Table | Grain | Key measures |
|---|---|---|
| `pos_weekly` | week × SKU × retailer | dollars, units, ACV %, base vs incremental, price, on-promo |
| `panel_household` | month × brand | household penetration, buyers, trips, basket, repeat |
| `promo_events` | promo event | promo type, discount %, lift %, incremental $/units |
| `products` | SKU | brand, category, pack size, list price, launch date |
| `brands` | brand | manufacturer, premium tier, primary category |
| `manufacturers` / `categories` / `retailers` | dimension | reference data |

Generator: `data/generators/generate_market_data.py`
Schema DDL: `schema/market_insights_schema.sql`
Semantic ontology: `ontology/market_insights_ontology.yaml`

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BROWSER  (frontend/index.html)                │
│           Circana-branded chat UI · Vega-Lite · Lucide icons         │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ HTTP (REST)
┌────────────────────────────────▼─────────────────────────────────────┐
│                    FastAPI APPLICATION  (chatbot/main.py)            │
│  /chat   /sessions   /sessions/{id}/history   /example-queries       │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│                          CORE SERVICES                               │
│  intent_engine.py   - LLM-based intent extraction (Groq + ontology)  │
│  query_engine.py    - Query library → DuckDB execution               │
│  session_manager.py - Multi-turn conversational memory               │
│  viz_builder.py     - Vega-Lite spec generation                      │
└──────────┬───────────────────────────────────────┬───────────────────┘
           │                                       │
┌──────────▼──────────────┐         ┌──────────────▼──────────────────┐
│      LLM (Groq)         │         │     DATA (DuckDB → CSV)         │
│  llama-3.3-70b-versatile│         │  8 tables registered as views   │
└─────────────────────────┘         └─────────────────────────────────┘
```

Tech stack is **LLM-agnostic** (swap Groq for Azure OpenAI, Bedrock, or on-prem Llama)
and **engine-agnostic** (swap DuckDB CSV for Snowflake / BigQuery — SQL is portable).

---

## Project layout

```
ask-liquid-data/
├── chatbot/
│   ├── main.py                      # FastAPI app
│   └── services/
│       ├── intent_engine.py         # NL → structured intent (Groq)
│       ├── query_engine.py          # Intent → SQL → DuckDB
│       ├── session_manager.py       # Multi-turn context
│       └── viz_builder.py           # Vega-Lite spec generator
│
├── frontend/
│   └── index.html                   # Circana-branded chat UI
│
├── data/
│   ├── csv/                         # Generated CPG/GM dataset
│   └── generators/
│       └── generate_market_data.py  # Synthetic data generator
│
├── ontology/
│   └── market_insights_ontology.yaml  # CPG/GM measures + dimensions
│
├── schema/
│   └── market_insights_schema.sql     # Portable DDL
│
├── docs/
│   ├── README.md                      # This file
│   ├── circana_ai_for_bi_pitch.html   # Pitch one-pager
│   └── circana_ai_for_bi_pitch.pptx   # Pitch deck (9 slides)
│
├── _archive_pharma/                 # Prior pharma-compliance reference (not loaded)
├── circana-logo.png                 # Brand asset
├── config/requirements.txt
└── .env.example
```

---

## Roadmap

| Phase | Capability | Status |
|---|---|---|
| 1. Conversational BI | "Ask Liquid Data" surface, 16 query templates, NL + viz + narrative | **Available** |
| 2. Policy as a Service | Commercial guardrails engine (JBP, MAP, distribution thresholds) | Planned |
| 3. Agents | Auto-MBR Generator, Share-Movement Watcher, Pacesetter Watch, Top-to-Top Readiness | Planned |
| 4. Live data | Replace DuckDB+CSV with Snowflake / BigQuery connectors | Planned |

---

## License & Notice

This project is an internal reference implementation. Circana, Liquid Data, Liquid AI,
Complete Why, and New Product Pacesetters are trademarks of Circana, LLC. The dataset
shipped here is **fully synthetic** — brand names are used to make the demo concrete,
but no real Circana measurement data is included.
