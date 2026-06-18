"""
Session Manager — multi-turn conversation state with context threading.

Storage model:
  - In-memory dict acts as a hot cache (cheap, fast).
  - On every add_turn() the user's full session list is flushed to
    `data/sessions/{user_id}.json` so conversations survive process restarts.
  - On import, all per-user files are eagerly loaded back into the cache.
"""
import json
import uuid
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


SESSION_DIR = Path(__file__).parent.parent.parent / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ConversationTurn:
    turn_id: int
    user_query: str
    intent: dict
    query_key: str
    result_rows: list[dict]
    narrative: str
    viz_type: str
    viz_spec: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parent_turn_id: Optional[int] = None


@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    turns: list[ConversationTurn] = field(default_factory=list)

    active_domain: Optional[str] = None
    active_metrics: list[str] = field(default_factory=list)
    active_dimensions: list[str] = field(default_factory=list)
    active_filters: list[dict] = field(default_factory=list)
    active_time_filter: Optional[dict] = None

    def last_intent(self) -> Optional[dict]:
        return self.turns[-1].intent if self.turns else None

    def last_turn(self) -> Optional[ConversationTurn]:
        return self.turns[-1] if self.turns else None

    def add_turn(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)
        intent = turn.intent
        if intent.get("domain"):
            self.active_domain = intent["domain"]
        if intent.get("metrics"):
            self.active_metrics = intent["metrics"]
        if intent.get("dimensions"):
            self.active_dimensions = intent["dimensions"]
        if intent.get("filters"):
            self.active_filters = intent["filters"]
        if intent.get("time_filter"):
            self.active_time_filter = intent["time_filter"]
        # Persist the user's sessions to disk
        _flush_user(self.user_id)

    def conversation_history(self) -> list[dict]:
        """Last-5-turns summary used as LLM context."""
        return [
            {
                "user_query": t.user_query,
                "intent": t.intent,
                "narrative_summary": t.narrative[:200] if t.narrative else "",
            }
            for t in self.turns[-5:]
        ]


# ── Cache + persistence ─────────────────────────────────────────────────────
_sessions: dict[str, Session] = {}


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _session_to_dict(s: Session) -> dict:
    return {
        "session_id": s.session_id,
        "user_id":    s.user_id,
        "created_at": s.created_at.isoformat(),
        "active_domain":     s.active_domain,
        "active_metrics":    s.active_metrics,
        "active_dimensions": s.active_dimensions,
        "active_filters":    s.active_filters,
        "active_time_filter": s.active_time_filter,
        "turns": [
            {
                "turn_id":        t.turn_id,
                "user_query":     t.user_query,
                "intent":         t.intent,
                "query_key":      t.query_key,
                "result_rows":    t.result_rows,
                "narrative":      t.narrative,
                "viz_type":       t.viz_type,
                "viz_spec":       t.viz_spec,
                "timestamp":      t.timestamp.isoformat(),
                "parent_turn_id": t.parent_turn_id,
            }
            for t in s.turns
        ],
    }


def _session_from_dict(d: dict) -> Session:
    s = Session(
        session_id=d["session_id"],
        user_id=d["user_id"],
        created_at=datetime.fromisoformat(d["created_at"]),
        active_domain=d.get("active_domain"),
        active_metrics=d.get("active_metrics") or [],
        active_dimensions=d.get("active_dimensions") or [],
        active_filters=d.get("active_filters") or [],
        active_time_filter=d.get("active_time_filter"),
    )
    for t in d.get("turns", []):
        s.turns.append(ConversationTurn(
            turn_id=t["turn_id"],
            user_query=t["user_query"],
            intent=t.get("intent") or {},
            query_key=t.get("query_key") or "",
            result_rows=t.get("result_rows") or [],
            narrative=t.get("narrative") or "",
            viz_type=t.get("viz_type") or "",
            viz_spec=t.get("viz_spec") or {},
            timestamp=datetime.fromisoformat(t["timestamp"]) if t.get("timestamp") else datetime.utcnow(),
            parent_turn_id=t.get("parent_turn_id"),
        ))
    return s


def _user_file(user_id: str) -> Path:
    # Sanitize user_id to a safe filename
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in user_id)
    return SESSION_DIR / f"{safe}.json"


def _flush_user(user_id: str) -> None:
    """Write all sessions for a user to their JSON file."""
    user_sessions = [s for s in _sessions.values() if s.user_id == user_id]
    payload = {"user_id": user_id, "sessions": [_session_to_dict(s) for s in user_sessions]}
    try:
        with open(_user_file(user_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, default=_json_default)
    except Exception as e:
        # Persistence is best-effort — log but never break the request path
        print(f"[session_manager] flush failed for {user_id}: {e}")


def _load_all_from_disk() -> None:
    for path in SESSION_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            for s_dict in payload.get("sessions", []):
                s = _session_from_dict(s_dict)
                _sessions[s.session_id] = s
        except Exception as e:
            print(f"[session_manager] load failed for {path.name}: {e}")


_load_all_from_disk()


# ── Public API ──────────────────────────────────────────────────────────────

def create_session(user_id: str) -> Session:
    session_id = str(uuid.uuid4())
    session = Session(session_id=session_id, user_id=user_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)


def get_or_create_session(session_id: Optional[str], user_id: str) -> Session:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    return create_session(user_id)


def list_sessions(user_id: str) -> list[dict]:
    user_sessions = [s for s in _sessions.values() if s.user_id == user_id]
    # Newest first by created_at
    user_sessions.sort(key=lambda s: s.created_at, reverse=True)
    return [
        {
            "session_id":  s.session_id,
            "created_at":  s.created_at.isoformat(),
            "turn_count":  len(s.turns),
            "first_query": s.turns[0].user_query  if s.turns else None,
            "last_query":  s.turns[-1].user_query if s.turns else None,
            "last_domain": s.active_domain,
            "last_active": s.turns[-1].timestamp.isoformat() if s.turns else s.created_at.isoformat(),
        }
        for s in user_sessions
    ]
