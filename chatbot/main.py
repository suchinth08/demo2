"""
Ask Liquid Data — Conversational Market Insights Chatbot (CPG + GM)
Endpoints: /chat, /sessions, /sessions/{id}/history, / (UI)

Run:  uvicorn chatbot.main:app --reload --port 8000
Then open: http://localhost:8000
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import traceback

from chatbot.services.intent_engine import extract_intent, build_insight_narrative
from chatbot.services.query_engine import route_intent_to_query, execute_query
from chatbot.services.session_manager import (
    get_or_create_session, get_session, list_sessions, ConversationTurn
)
from chatbot.services.viz_builder import build_viz_spec
from chatbot.services.root_cause_agent import investigate as run_root_cause
from chatbot.services.mbr_agent import (
    generate_mbr, resolve_download_path, ScopeValidationError,
)

app = FastAPI(
    title="Ask Liquid Data — Market Insights Chatbot",
    description="Conversational AI for CPG and General Merchandise market insights — "
                "share, velocity, distribution, promo, panel, innovation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend UI
FRONTEND_DIR    = Path(__file__).parent.parent / "frontend"
LOGO_PATH       = Path(__file__).parent.parent / "circana-logo.png"
FAVICON_ICO     = Path(__file__).parent.parent / "circana-favicon.ico"
FAVICON_PNG     = Path(__file__).parent.parent / "circana-favicon.png"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/circana-logo.png", include_in_schema=False)
async def serve_logo():
    return FileResponse(str(LOGO_PATH))


@app.get("/circana-favicon.png", include_in_schema=False)
async def serve_favicon_png():
    return FileResponse(str(FAVICON_PNG))


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    return FileResponse(str(FAVICON_ICO))


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    session_id: str
    turn_id: int
    user_query: str
    intent: dict
    narrative: str
    viz_type: str
    viz_spec: dict
    data: list[dict]
    suggested_followups: list[str]
    error: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint for Ask Liquid Data. Accepts natural-language queries
    about CPG / GM market insights data.

    Example queries:
      - "Which brands are losing share in Energy Drinks?"
      - "Show me the Pacesetter candidates"
      - "What is Liquid Death's distribution looking like?"
      - "How is Celsius trending vs Red Bull?"
      - "Top 10 brands by velocity"
      - "Which categories are growing fastest?"
    """
    session = get_or_create_session(req.session_id, req.user_id)
    prior_intent = session.last_intent()
    history = session.conversation_history()

    try:
        # 1. Extract structured intent from natural language
        intent = extract_intent(
            user_query=req.query,
            conversation_history=history,
            prior_intent=prior_intent,
        )

        if "error" in intent:
            return ChatResponse(
                session_id=session.session_id,
                turn_id=len(session.turns) + 1,
                user_query=req.query,
                intent=intent,
                narrative="I couldn't understand that query. Could you rephrase it?",
                viz_type="none",
                viz_spec={},
                data=[],
                suggested_followups=_default_followups(),
                error=intent.get("raw"),
            )

        # 2. Route intent to a query in the library
        query_key, extra_filters = route_intent_to_query(intent)

        # 3. Execute query against DuckDB
        data: list[dict] = []
        query_error = None
        if query_key:
            try:
                data = execute_query(query_key, extra_filters)
            except Exception as e:
                query_error = str(e)
                data = []

        # 4. Build visualization spec
        viz_type = intent.get("viz_type", "bar_chart")
        viz_spec = build_viz_spec(viz_type, data, intent)

        # 5. Generate insight narrative (LLM-powered)
        narrative = ""
        if data:
            try:
                narrative = build_insight_narrative(intent, {"data": data[:10]}, req.query)
            except Exception:
                narrative = f"Found {len(data)} records for your query."
        else:
            narrative = "No data found for this query. Try adjusting your filters."

        # 6. Suggested follow-up questions
        followups = _generate_followups(intent, data)

        # 7. Store turn in session
        turn = ConversationTurn(
            turn_id=len(session.turns) + 1,
            user_query=req.query,
            intent=intent,
            query_key=query_key or "",
            result_rows=data,
            narrative=narrative,
            viz_type=viz_type,
            viz_spec=viz_spec,
            parent_turn_id=len(session.turns) if session.turns else None,
        )
        session.add_turn(turn)

        return ChatResponse(
            session_id=session.session_id,
            turn_id=turn.turn_id,
            user_query=req.query,
            intent=intent,
            narrative=narrative,
            viz_type=viz_type,
            viz_spec=viz_spec,
            data=_safe_serialize(data[:50]),
            suggested_followups=followups,
            error=query_error,
        )

    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{tb}")


@app.get("/sessions")
async def get_sessions(user_id: str = "default_user"):
    return list_sessions(user_id)


@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = "default_user"):
    """Lightweight summary of each turn — for a session-list preview."""
    session = get_or_create_session(session_id, user_id)
    return [
        {
            "turn_id":    t.turn_id,
            "user_query": t.user_query,
            "intent_type": t.intent.get("intent"),
            "domain":      t.intent.get("domain"),
            "narrative":   t.narrative,
            "viz_type":    t.viz_type,
            "row_count":   len(t.result_rows),
            "timestamp":   t.timestamp.isoformat(),
        }
        for t in session.turns
    ]


@app.get("/sessions/{session_id}/full")
async def get_session_full(session_id: str):
    """
    Full turn-by-turn payload for replay in the UI — includes intent, narrative,
    viz_spec, and the underlying data rows so the frontend can rerender the
    entire conversation exactly as it appeared the first time.
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {
        "session_id":  session.session_id,
        "user_id":     session.user_id,
        "created_at":  session.created_at.isoformat(),
        "turn_count":  len(session.turns),
        "turns": [
            {
                "turn_id":     t.turn_id,
                "user_query":  t.user_query,
                "intent":      t.intent,
                "narrative":   t.narrative,
                "viz_type":    t.viz_type,
                "viz_spec":    t.viz_spec,
                "data":        _safe_serialize(t.result_rows[:50]),
                "timestamp":   t.timestamp.isoformat(),
            }
            for t in session.turns
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ask-liquid-data-market-insights"}


# ── AI Agents ────────────────────────────────────────────────────────────────

class RootCauseRequest(BaseModel):
    brand_name: str
    category_name: Optional[str] = None


@app.post("/agents/root-cause")
async def root_cause(req: RootCauseRequest):
    """Why-Is-Share-Moving? Multi-hypothesis investigation for a brand."""
    try:
        return run_root_cause(req.brand_name, req.category_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AutoMBRRequest(BaseModel):
    brand_name: Optional[str] = None
    category_name: Optional[str] = None


@app.post("/agents/auto-mbr")
async def auto_mbr(req: AutoMBRRequest):
    """Generate a 5-section Monthly Business Review .pptx for a brand or category."""
    if not req.brand_name and not req.category_name:
        raise HTTPException(status_code=400, detail="Provide brand_name or category_name")
    try:
        return generate_mbr(req.brand_name, req.category_name)
    except ScopeValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/auto-mbr/download/{filename}")
async def auto_mbr_download(filename: str):
    """Stream a generated MBR .pptx by filename."""
    path = resolve_download_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail=f"MBR file not found: {filename}")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@app.get("/example-queries")
async def example_queries():
    return {
        "share": [
            "Which brands are losing share in Energy Drinks?",
            "Top 10 share gainers across all CPG categories",
            "Show me Coca-Cola's share trend in Carbonated Beverages",
            "Compare Celsius and Red Bull share over time",
        ],
        "velocity": [
            "Top 10 brands by velocity",
            "Which brands have the highest $/store/week in CPG?",
            "Velocity ranking in Beauty Specialty channel",
        ],
        "distribution": [
            "Which high-velocity brands have distribution gaps?",
            "What is Liquid Death's ACV by retailer?",
            "Show me distribution gaps in Sparkling Water",
        ],
        "pricing": [
            "Show the price index for Energy Drinks vs category average",
            "Which brands are priced above category in Skincare?",
            "What is Celsius's price gap to Red Bull?",
        ],
        "promotion": [
            "Top promo lift by brand last quarter",
            "Which promo types deliver the highest lift?",
            "What is the % volume on promo for Salty Snacks?",
        ],
        "panel": [
            "Household penetration ranking across CPG brands",
            "Show the panel penetration trend for Celsius",
            "Which brands have the highest repeat rate?",
        ],
        "innovation": [
            "Show me the Pacesetter candidates",
            "Year-1 trajectory for Liquid Death",
            "Which new launches are gaining traction?",
        ],
        "category": [
            "Which categories are growing fastest?",
            "Show monthly trend for Carbonated Beverages",
            "Compare growth rates across CPG departments",
        ],
    }


# ── Utilities ───────────────────────────────────────────────────────────────

def _generate_followups(intent: dict, data: list[dict]) -> list[str]:
    """Generate contextually relevant follow-up questions."""
    domain      = intent.get("domain", "")
    intent_type = intent.get("intent", "")

    followup_map = {
        "share": {
            "METRIC_SNAPSHOT": [
                "Show the trend over time",
                "Break it down by retailer",
                "Who are the biggest gainers and losers?",
            ],
            "TREND_ANALYSIS": [
                "Which retailer is driving the change?",
                "What's the velocity story?",
                "Show share gainers and losers",
            ],
            "SHARE_MOVEMENT": [
                "Why is Liquid Death gaining?",
                "Show distribution for the top gainers",
                "Which retailers are over-indexed?",
            ],
        },
        "velocity": {
            "RANKING": [
                "Show ACV distribution for these brands",
                "Compare velocity across retailers",
                "Which have distribution gaps?",
            ],
        },
        "distribution": {
            "DISTRIBUTION_GAP": [
                "Show velocity for these brands",
                "Which retailers don't carry them?",
                "What's the panel penetration for these?",
            ],
        },
        "promotion": {
            "PROMO_EFFECTIVENESS": [
                "Show promo lift by retailer",
                "Which discount depth maximises ROI?",
                "Compare TPR vs Feature & Display",
            ],
        },
        "panel": {
            "PANEL_DEEP_DIVE": [
                "Show penetration trend over time",
                "Compare repeat rates across brands",
                "What's the basket size by brand?",
            ],
        },
        "innovation": {
            "PACESETTER_WATCH": [
                "Show Liquid Death's distribution build",
                "How does Year-1 trajectory compare to category average?",
                "Which retailers are early adopters?",
            ],
        },
        "category": {
            "BREAKDOWN": [
                "Show the brand share within the top categories",
                "Which retailers are growing the category?",
                "Show monthly trend",
            ],
        },
    }

    suggestions = followup_map.get(domain, {}).get(intent_type, [])

    if not suggestions:
        suggestions = [
            "Show the top share gainers and losers",
            "Which brands have distribution gaps?",
            "Show the Pacesetter candidates",
        ]

    return suggestions[:3]


def _default_followups() -> list[str]:
    return [
        "Show me the top share gainers across all CPG",
        "Top 10 brands by velocity",
        "Show me the Pacesetter candidates",
    ]


def _safe_serialize(data: list[dict]) -> list[dict]:
    """Convert non-JSON-serializable types for the API response."""
    from datetime import date, datetime
    result = []
    for row in data:
        clean = {}
        for k, v in row.items():
            if isinstance(v, (date, datetime)):
                clean[k] = v.isoformat()
            elif v is None:
                clean[k] = None
            else:
                clean[k] = v
        result.append(clean)
    return result
