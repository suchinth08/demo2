"""
Intent Engine — extracts structured analytical intent from natural language
using a configurable LLM provider, grounded in the CPG / GM market insights
domain ontology (Circana-style: POS, panel, distribution, promo).

Providers (set via LLM_PROVIDER in .env):
  - openrouter  : OpenRouter free-tier API (production default)
  - groq        : Groq API, llama-3.3-70b-versatile  (cloud, rate-limited)
  - claude_cli  : local `claude` CLI (Claude Code) — uses your already-
                  authenticated session, no API key, no daily token cap.
                  Slower per call but unlimited at the personal-use tier.
"""
import json
import os
import platform
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter").lower()

# ── OpenRouter config ────────────────────────────────────────────────────────
OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL    = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_MAX_TOKENS = int(os.environ.get("OPENROUTER_MAX_TOKENS", "4096"))

# ── Lazy-init the Groq client only when needed ──────────────────────────────
_groq_client = None
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _groq_client

# ── Domain ontology injected into the system prompt ───────────────────────
ONTOLOGY_CONTEXT = """
You are an Ask Liquid Data assistant — a conversational market insights analyst for
CPG and General Merchandise manufacturers and retailers. You understand POS sales,
panel data, distribution, promotions, pricing, and innovation/Pacesetter analytics.

AVAILABLE DOMAINS (use exact lowercase keys):
  share         - Market share analytics ($/unit share, gainers, losers, share-point change)
  velocity      - Rate-of-sale ($/store/week, units/store/week)
  distribution  - ACV-weighted distribution, distribution gaps, store count
  pricing       - Price levels, price gap vs category/competitor, price index
  promotion     - Promo lift, % volume on deal, promo ROI by event type
  panel         - Household penetration, buyers, frequency, basket, repeat
  innovation    - New launches, Year-1 trajectory, Pacesetter candidates
  category      - Category health, growth rate, segment mix

AVAILABLE METRICS:
  share:        dollar_share_pct, unit_share_pct, share_pt_change
  velocity:     dollars_per_store_per_week, units_per_store_per_week
  distribution: avg_acv_pct, distribution_gap_pct, stores_selling
  pricing:      avg_price, base_price, price_index
  promotion:    promo_lift_pct, pct_volume_on_promo, incremental_dollars_mm,
                avg_discount_pct
  panel:        hh_penetration_pct, buyers_mm, trips_per_buyer,
                dollars_per_trip, repeat_rate_pct
  general:      dollars_mm, units, growth_pct

AVAILABLE DIMENSIONS:
  product:   sku_id, sku_description, brand_name, manufacturer_name,
             premium_tier, pack_size, launch_date
  category:  category_name, sub_category, department
  retailer:  retailer_name, channel, region
  promo:     promo_type, on_promo, discount_pct
  time:      week_ending, period_month, fiscal_quarter, fiscal_year

DOMAIN SYNONYMS — resolve these to the canonical term:
  "share" / "market share" / "$ share" / "value share" / "dollar share"  -> dollar_share_pct
  "unit share" / "volume share"                                          -> unit_share_pct
  "velocity" / "ROS" / "rate of sale" / "$/STR/WK"                       -> velocity (domain)
  "ACV" / "% ACV" / "PCV" / "distribution"                               -> distribution (domain)
  "distribution gap" / "whitespace" / "untapped"                         -> DISTRIBUTION_GAP intent
  "lift" / "promo lift" / "uplift" / "incremental %"                     -> promo_lift_pct
  "TPR"                                                                  -> promo_type='TPR'
  "feature" / "ad feature" / "circular"                                  -> promo_type='Feature'
  "display" / "end cap"                                                  -> promo_type='Display'
  "penetration" / "% HH" / "household reach" / "reach"                   -> hh_penetration_pct
  "frequency" / "repeat purchase"                                        -> trips_per_buyer
  "basket" / "$ per trip" / "spend per trip"                             -> dollars_per_trip
  "loyalty" / "repeat"                                                   -> repeat_rate_pct
  "Pacesetter" / "Year-1 launch" / "new launch winner"                   -> innovation (domain)
  "JBP" / "joint business plan" / "top-to-top"                           -> retailer (context)
  "non-conformance" / "deviation" — IGNORE, not a CPG term
  "CAPA" — IGNORE, not a CPG term

INDUSTRY DOMAIN NOTES:
  - "Share" in CPG/GM is always within a category. "Share of Beverages" means
    share within the Beverage category. If the user doesn't name a category,
    assume they mean across all categories the brand competes in.
  - "ACV" = % of All-Commodity-Volume — the gold-standard CPG distribution metric.
    99% ACV means a brand is in stores accounting for 99% of category $ volume.
  - "Velocity" = $ or units per store per week — i.e. how fast the product
    moves once it's on shelf. The leading indicator of innovation success.
  - "Pacesetter" = Circana's name for Year-1 launch winners ($7.5M+ in Year-1
    sales is the typical Pacesetter threshold).
  - Use channel context: Mass (Walmart/Target), Grocery (Kroger/Albertsons/Publix),
    Club (Costco/Sam's), Drug (CVS/Walgreens), eCom (Amazon),
    Beauty Specialty (Sephora/Ulta), Electronics (Best Buy).

TIME EXPRESSIONS (convert to filter):
  - "L4W" / "last 4 weeks"                          -> trailing 4 weeks
  - "L13W" / "last 13 weeks" / "last quarter"       -> trailing 13 weeks
  - "L26W" / "last half"                             -> trailing 26 weeks
  - "L52W" / "rolling year" / "last 12 months"      -> trailing 52 weeks
  - "YTD" / "year to date"                          -> Jan 1 of current year
  - "YA" / "year ago"                                -> prior year same period
  - "last quarter"                                   -> trailing 13 weeks

INTENT TYPES (each picks a default visualization):
  METRIC_SNAPSHOT      - single KPI value or small dashboard (-> metric_card)
  TREND_ANALYSIS       - metric over time (-> line_chart)
  BREAKDOWN            - metric split by dimension (-> bar_chart)
  RANKING              - top/bottom N (-> horizontal_bar)
  COMPARISON           - A vs B or retailer vs retailer (-> grouped_bar)
  SHARE_MOVEMENT       - share gainers / losers vs prior period (-> horizontal_bar)
  DISTRIBUTION_GAP     - high velocity but low distribution (-> table_with_rag)
  PROMO_EFFECTIVENESS  - lift, ROI by promo type (-> bar_chart)
  PRICE_GAP            - price index vs category/competitor (-> bar_chart)
  PACESETTER_WATCH     - new-launch Year-1 trajectory (-> line_chart)
  PANEL_DEEP_DIVE      - penetration / loyalty / basket (-> bar_chart)
  ANOMALY_DETECTION    - why did X spike/drop (-> line_chart)
  DRILL_DOWN           - details behind an aggregate (-> data_table)

OUTPUT: Always return valid JSON in this exact structure (no prose, no markdown fences):
{
  "intent": "INTENT_TYPE",
  "domain": "share|velocity|distribution|pricing|promotion|panel|innovation|category",
  "metrics": ["metric_key1", "metric_key2"],
  "dimensions": ["dimension_key"],
  "time_filter": {"type": "relative|absolute", "value": "description"},
  "filters": [{"field": "field_name", "op": "eq|gt|lt|in|contains", "value": "filter_value"}],
  "sort": {"field": "metric_key", "dir": "desc"},
  "limit": null,
  "viz_type": "metric_card|line_chart|bar_chart|horizontal_bar|grouped_bar|pie|heatmap|scatter|data_table|table_with_rag|timeline",
  "nl_response_hint": "how to phrase the narrative response",
  "needs_clarification": null
}

EXAMPLES:

  Q: "Which brands are losing share in Energy Drinks?"
  A: {"intent":"SHARE_MOVEMENT","domain":"share","metrics":["share_pt_change"],
      "dimensions":["brand_name"],"filters":[{"field":"category_name","op":"eq","value":"Energy Drinks"}],
      "viz_type":"horizontal_bar","sort":{"field":"share_pt_change","dir":"asc"}}

  Q: "Show me the Pacesetter candidates"
  A: {"intent":"PACESETTER_WATCH","domain":"innovation","metrics":["year1_dollars_mm"],
      "dimensions":["brand_name","category_name"],"viz_type":"horizontal_bar"}

  Q: "What is Liquid Death's distribution looking like?"
  A: {"intent":"DISTRIBUTION_GAP","domain":"distribution","metrics":["avg_acv_pct"],
      "dimensions":["retailer_name"],"filters":[{"field":"brand_name","op":"eq","value":"Liquid Death"}],
      "viz_type":"horizontal_bar"}

  Q: "How is Celsius trending in Energy Drinks?"
  A: {"intent":"TREND_ANALYSIS","domain":"share","metrics":["dollar_share_pct"],
      "dimensions":["brand_name"],"filters":[{"field":"category_name","op":"eq","value":"Energy Drinks"}],
      "viz_type":"line_chart"}

  Q: "Top 10 brands by velocity"
  A: {"intent":"RANKING","domain":"velocity","metrics":["dollars_per_store_per_week"],
      "dimensions":["brand_name"],"limit":10,"viz_type":"horizontal_bar"}
"""

FOLLOWUP_SYSTEM = """
You are resolving a follow-up question in a CPG/GM market insights conversation.
Given the PREVIOUS INTENT JSON and the NEW QUESTION, produce an UPDATED INTENT JSON.

Rules for follow-up resolution:
1. "by {dimension}" / "by retailer" / "by brand" -> replace/add dimension, inherit everything else
2. "{new time}" / "for last 4 weeks" / "YTD"     -> replace time_filter, inherit everything else
3. "what about {metric}"                          -> replace metrics, inherit everything else
4. "only {filter}" / "just for {retailer}"        -> add filter, inherit everything else
5. "show details" / "which ones"                  -> change to DRILL_DOWN, inherit filters
6. "same for {brand/category}"                    -> update that specific filter
7. "why" / "what's driving"                       -> change to ANOMALY_DETECTION or SHARE_MOVEMENT
8. Completely new question                        -> fresh intent, no inheritance

Return ONLY the updated JSON object, no prose, no markdown code fences.
"""


def _call_openrouter_provider(system: str, messages: list[dict], max_tokens: int) -> str:
    """OpenRouter API call using the free-tier model (used when LLM_PROVIDER=openrouter).
    Uses the OpenAI-compatible /chat/completions endpoint — no extra SDK needed.
    Retries up to 4 times on 429 with exponential backoff.
    """
    import httpx
    full_messages = [{"role": "system", "content": system}] + messages
    cap = min(max_tokens, OPENROUTER_MAX_TOKENS)
    delays = [5, 15, 30, 60]
    for attempt, delay in enumerate(delays + [None]):
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "Ask-Liquid-Data",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": full_messages,
                "max_tokens": cap,
                "temperature": 0.1,
            },
            timeout=120.0,
        )
        if resp.status_code == 429 and delay is not None:
            time.sleep(delay)
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def _call_groq_provider(system: str, messages: list[dict], max_tokens: int) -> str:
    """Direct Groq API call (used when LLM_PROVIDER=groq)."""
    full_messages = [{"role": "system", "content": system}] + messages
    response = _get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


CLAUDE_CLI_TIMEOUT = int(os.environ.get("CLAUDE_CLI_TIMEOUT", "300"))
_IS_WIN = platform.system() == "Windows"


def _call_claude_cli_provider(system: str, messages: list[dict], max_tokens: int) -> str:
    """Invoke the local `claude` CLI as a subprocess. Uses the user's already-
    authenticated Claude Code session — no API key, no daily token cap.

    The CLI is one-shot, so multi-turn `messages` lists are collapsed into one
    prompt with prior turns marked as context. System prompt goes to a temp file
    (--system-prompt-file) to avoid command-line length limits on Windows.
    """
    # 1. Compose a single user-facing prompt from the messages list
    if len(messages) == 1:
        user_payload = messages[0]["content"]
    else:
        parts: list[str] = []
        for m in messages[:-1]:
            role = "USER" if m.get("role") == "user" else "ASSISTANT"
            parts.append(f"[Previous turn — {role}]\n{m['content']}\n")
        parts.append(f"[Current turn — USER]\n{messages[-1]['content']}")
        user_payload = "\n".join(parts)

    # 2. Write the system prompt to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8",
                                     delete=False) as f:
        f.write(system)
        sys_path = f.name

    try:
        args = [
            "claude", "-p",
            "--output-format", "text",
            "--system-prompt-file", sys_path,
        ]
        proc = subprocess.run(
            args,
            input=user_payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=CLAUDE_CLI_TIMEOUT,
            shell=_IS_WIN,            # claude.cmd needs cmd shell on Windows
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (exit {proc.returncode}): "
                f"{(proc.stderr or '').strip()[:500]}"
            )
        return (proc.stdout or "").strip()
    finally:
        try:
            os.unlink(sys_path)
        except Exception:
            pass


def _call_groq(system: str, messages: list[dict], max_tokens: int = 1024) -> str:
    """
    Provider-agnostic LLM call. Routes to OpenRouter, Groq, or local Claude CLI
    based on the LLM_PROVIDER env var. Kept under the old name so that
    root_cause_agent / mbr_agent imports continue to work unchanged.
    """
    if LLM_PROVIDER == "openrouter":
        return _call_openrouter_provider(system, messages, max_tokens)
    if LLM_PROVIDER == "groq":
        return _call_groq_provider(system, messages, max_tokens)
    if LLM_PROVIDER == "claude_cli":
        return _call_claude_cli_provider(system, messages, max_tokens)
    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r} (use 'openrouter', 'groq', or 'claude_cli')"
    )


def extract_intent(
    user_query: str,
    conversation_history: list[dict],
    prior_intent: Optional[dict] = None
) -> dict:
    """Extract structured intent from natural language query."""
    messages = []

    for turn in conversation_history[-3:]:
        messages.append({"role": "user",      "content": turn["user_query"]})
        messages.append({"role": "assistant", "content": json.dumps(turn["intent"])})

    is_followup = prior_intent is not None and _looks_like_followup(user_query)

    if is_followup:
        system = FOLLOWUP_SYSTEM
        query_content = (
            f"PREVIOUS INTENT:\n{json.dumps(prior_intent, indent=2)}\n\n"
            f'NEW QUESTION: "{user_query}"\n\n'
            "Return the updated intent JSON."
        )
    else:
        system = ONTOLOGY_CONTEXT
        query_content = f'Extract intent for: "{user_query}"'

    messages.append({"role": "user", "content": query_content})

    raw = _call_groq(system, messages, max_tokens=1024)

    # Strip markdown code fences if the model wraps JSON in ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {"error": "Could not parse intent", "raw": raw}


def _looks_like_followup(query: str) -> bool:
    followup_signals = [
        r"^(now|also|what about|and|but|instead|same|those|that)",
        r"^(break it|show me|filter by|only for|just|specifically)",
        r"^(by \w+)",
        r"\bsame\b",
        r"\binstead\b",
        r"\bmore detail\b",
        r"\bdrilldown\b",
        r"\bwhy\b.*(that|those|this)",
        r"\bexpand\b",
    ]
    q = query.lower().strip()
    return any(re.search(p, q) for p in followup_signals)


def build_insight_narrative(
    intent: dict,
    query_result: dict,
    user_query: str
) -> str:
    """
    Generate a natural-language insight narrative from query results, grounded
    in CPG/GM market measurement context (share, velocity, ACV, lift, panel).
    """
    result_summary = json.dumps(query_result, indent=2, default=str)[:3000]

    system = (
        "You are an Ask Liquid Data market insights analyst for CPG and General "
        "Merchandise manufacturers. Write concise, professional insights grounded "
        "in standard CPG measurement: dollar/unit share, ACV-weighted distribution, "
        "velocity ($/store/week), promo lift, household penetration, Pacesetter "
        "trajectory. Use industry vocabulary naturally. Never hallucinate numbers "
        "that are not in the query results."
    )
    prompt = (
        f'User asked: "{user_query}"\n'
        f"Query intent: {intent.get('intent')} on {intent.get('domain')}\n\n"
        f"Query results:\n{result_summary}\n\n"
        "Write a concise insight (3-5 sentences) that:\n"
        "1. Directly answers the question, citing the most important numbers\n"
        "2. Highlights the most interesting finding (biggest mover, outlier, anomaly)\n"
        "3. Suggests one commercial implication (distribution opportunity, "
        "promo dependency risk, share-gain reason, etc.)\n"
        "4. Ends with: \"Follow-up: [one suggested follow-up question]\""
    )

    return _call_groq(system, [{"role": "user", "content": prompt}], max_tokens=512)
