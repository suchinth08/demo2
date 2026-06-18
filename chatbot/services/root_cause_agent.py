"""
Root-Cause Agent — "Why Is Share Moving?"

Given a brand (and optionally a category), fans out across six hypothesis
families, computes current-13W vs prior-13W deltas for each, ranks them by
magnitude + signal-to-noise, and uses an LLM to narrate each finding with
evidence. Output is a ranked list of hypotheses, each carrying its own
evidence chain so a Brand Director can defend the call to their CFO.

Hypothesis families:
  1. DISTRIBUTION   — did ACV-weighted distribution expand or contract?
  2. VELOCITY       — did $/store/week move (independent of distribution)?
  3. PRICING        — did the price index vs category change?
  4. PROMOTION      — did promo intensity (depth + frequency) shift?
  5. INNOVATION     — is this a recent launch still on its Year-1 curve?
  6. RETAILER MIX   — did the brand expand into new retailers / channels?
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from chatbot.services.intent_engine import _call_groq
from chatbot.services.query_engine import get_conn


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Hypothesis:
    family:      str          # DISTRIBUTION / VELOCITY / PRICING / PROMOTION / INNOVATION / RETAILER_MIX
    headline:    str          # short label e.g. "Distribution expanded +14.2 ACV pts"
    direction:   str          # "supports_gain" | "supports_loss" | "neutral"
    magnitude:   float        # 0-100 — drives ranking
    confidence:  str          # "high" | "medium" | "low"
    evidence:    dict         # raw numbers backing the finding
    narrative:   str = ""     # LLM-written explanation


@dataclass
class RootCauseReport:
    brand_name:       str
    category_name:    Optional[str]
    share_movement:   dict                          # {current_pct, prior_pct, share_pt_change}
    hypotheses:       list[Hypothesis] = field(default_factory=list)
    summary:          str = ""
    generated_at:     str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─────────────────────────────────────────────────────────────────────────────
# Data collectors — each returns the raw evidence for one hypothesis family
# ─────────────────────────────────────────────────────────────────────────────

def _scalar(rows: list, key: str, default=0):
    if rows and rows[0].get(key) is not None:
        return rows[0][key]
    return default


def _fetch_share_movement(brand: str, category: Optional[str]) -> dict:
    """Confirm there IS a share movement to explain; compute it cleanly."""
    conn = get_conn()
    cat_filter = f"AND c.category_name = '{category.replace(chr(39), chr(39)*2)}'" if category else ""
    sql = f"""
        WITH per_brand_period AS (
          SELECT b.brand_name, c.category_name, pr.category_id,
                 CASE
                   WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                        THEN 'L13W'
                   WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                        AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                        THEN 'P13W'
                 END AS period_label,
                 SUM(p.dollars) AS dollars
          FROM pos_weekly p
          JOIN products pr   ON p.sku_id   = pr.sku_id
          JOIN brands  b     ON pr.brand_id = b.brand_id
          JOIN categories c  ON pr.category_id = c.category_id
          WHERE CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
            AND b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            {cat_filter}
          GROUP BY b.brand_name, c.category_name, pr.category_id, period_label
        ),
        cat_period AS (
          SELECT pbp.category_id, pbp.period_label,
                 (SELECT SUM(p2.dollars)
                  FROM pos_weekly p2 JOIN products pr2 ON p2.sku_id = pr2.sku_id
                  WHERE pr2.category_id = pbp.category_id
                    AND ((pbp.period_label = 'L13W' AND CAST(p2.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK)
                      OR (pbp.period_label = 'P13W' AND CAST(p2.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                                                     AND CAST(p2.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK))
                 ) AS cat_d
          FROM per_brand_period pbp
          WHERE pbp.period_label IS NOT NULL
          GROUP BY pbp.category_id, pbp.period_label
        )
        SELECT pbp.category_name,
               ROUND(MAX(CASE WHEN pbp.period_label='L13W' THEN 100.0 * pbp.dollars / cp.cat_d END), 2) AS current_share_pct,
               ROUND(MAX(CASE WHEN pbp.period_label='P13W' THEN 100.0 * pbp.dollars / cp.cat_d END), 2) AS prior_share_pct,
               ROUND(MAX(CASE WHEN pbp.period_label='L13W' THEN pbp.dollars END) / 1e6, 2) AS current_dollars_mm,
               ROUND(MAX(CASE WHEN pbp.period_label='P13W' THEN pbp.dollars END) / 1e6, 2) AS prior_dollars_mm
        FROM per_brand_period pbp
        JOIN cat_period cp ON pbp.category_id = cp.category_id AND pbp.period_label = cp.period_label
        GROUP BY pbp.category_name
        ORDER BY current_share_pct DESC
        LIMIT 1
    """
    rows = conn.execute(sql).fetchdf().to_dict("records")
    if not rows:
        return {"current_share_pct": 0, "prior_share_pct": 0, "share_pt_change": 0,
                "current_dollars_mm": 0, "prior_dollars_mm": 0, "category_name": category}
    r = rows[0]
    r["share_pt_change"] = round((r.get("current_share_pct") or 0) - (r.get("prior_share_pct") or 0), 2)
    return r


def _fetch_distribution_change(brand: str) -> dict:
    """Has ACV / store count moved between the two 13W windows?"""
    conn = get_conn()
    sql = f"""
        WITH per_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            AVG(p.acv_weighted_distribution_pct) AS avg_acv_pct,
            SUM(p.stores_selling) / COUNT(DISTINCT p.week_ending) AS avg_stores_selling,
            COUNT(DISTINCT p.retailer_id) AS retailer_count
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands b ON pr.brand_id = b.brand_id
          WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label
        )
        SELECT
          ROUND(MAX(CASE WHEN period_label='L13W' THEN avg_acv_pct END), 1) AS current_acv_pct,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN avg_acv_pct END), 1) AS prior_acv_pct,
          ROUND(MAX(CASE WHEN period_label='L13W' THEN avg_stores_selling END), 0) AS current_stores,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN avg_stores_selling END), 0) AS prior_stores,
          MAX(CASE WHEN period_label='L13W' THEN retailer_count END) AS current_retailers,
          MAX(CASE WHEN period_label='P13W' THEN retailer_count END) AS prior_retailers
        FROM per_period WHERE period_label IS NOT NULL
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


def _fetch_velocity_change(brand: str) -> dict:
    conn = get_conn()
    sql = f"""
        WITH per_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            SUM(p.dollars) AS total_dollars,
            SUM(p.stores_selling) AS total_store_weeks
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands b ON pr.brand_id = b.brand_id
          WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label
        )
        SELECT
          ROUND(MAX(CASE WHEN period_label='L13W' THEN total_dollars / NULLIF(total_store_weeks,0) END), 2) AS current_dpsw,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN total_dollars / NULLIF(total_store_weeks,0) END), 2) AS prior_dpsw
        FROM per_period WHERE period_label IS NOT NULL
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


def _fetch_pricing_change(brand: str, category: Optional[str]) -> dict:
    conn = get_conn()
    cat_filter = ""
    if category:
        cat_filter = f"AND c.category_name = '{category.replace(chr(39), chr(39)*2)}'"
    sql = f"""
        WITH brand_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            pr.category_id,
            AVG(p.avg_price) AS brand_avg_price
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands b ON pr.brand_id = b.brand_id
          JOIN categories c ON pr.category_id = c.category_id
          WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            {cat_filter}
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label, pr.category_id
        ),
        cat_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            pr.category_id,
            AVG(p.avg_price) AS cat_avg_price
          FROM pos_weekly p JOIN products pr ON p.sku_id = pr.sku_id
          WHERE pr.category_id IN (SELECT category_id FROM brand_period)
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label, pr.category_id
        )
        SELECT
          ROUND(AVG(CASE WHEN bp.period_label='L13W' THEN 100.0 * bp.brand_avg_price / cp.cat_avg_price END), 1) AS current_price_index,
          ROUND(AVG(CASE WHEN bp.period_label='P13W' THEN 100.0 * bp.brand_avg_price / cp.cat_avg_price END), 1) AS prior_price_index,
          ROUND(AVG(CASE WHEN bp.period_label='L13W' THEN bp.brand_avg_price END), 2) AS current_avg_price,
          ROUND(AVG(CASE WHEN bp.period_label='P13W' THEN bp.brand_avg_price END), 2) AS prior_avg_price
        FROM brand_period bp
        JOIN cat_period cp ON bp.category_id = cp.category_id AND bp.period_label = cp.period_label
        WHERE bp.period_label IS NOT NULL
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


def _fetch_promo_change(brand: str) -> dict:
    conn = get_conn()
    sql = f"""
        WITH per_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            100.0 * SUM(CASE WHEN p.on_promo THEN p.units END) / NULLIF(SUM(p.units),0) AS pct_vol_on_promo,
            AVG(CASE WHEN p.on_promo THEN p.discount_pct END) AS avg_discount_pct,
            100.0 * SUM(p.incremental_units) / NULLIF(SUM(p.base_units),0) AS promo_lift_pct
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands b ON pr.brand_id = b.brand_id
          WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label
        )
        SELECT
          ROUND(MAX(CASE WHEN period_label='L13W' THEN pct_vol_on_promo END), 1) AS current_pct_on_promo,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN pct_vol_on_promo END), 1) AS prior_pct_on_promo,
          ROUND(MAX(CASE WHEN period_label='L13W' THEN avg_discount_pct END), 1) AS current_avg_discount,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN avg_discount_pct END), 1) AS prior_avg_discount,
          ROUND(MAX(CASE WHEN period_label='L13W' THEN promo_lift_pct END), 1) AS current_lift_pct,
          ROUND(MAX(CASE WHEN period_label='P13W' THEN promo_lift_pct END), 1) AS prior_lift_pct
        FROM per_period WHERE period_label IS NOT NULL
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


def _fetch_innovation_signal(brand: str) -> dict:
    """Is this a recent launch still on its Year-1 curve?"""
    conn = get_conn()
    sql = f"""
        SELECT
          MIN(pr.launch_date)                                              AS earliest_launch,
          DATEDIFF('week', MIN(CAST(pr.launch_date AS DATE)),
                          (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly)) AS weeks_since_launch,
          COUNT(DISTINCT pr.sku_id)                                        AS sku_count
        FROM products pr
        JOIN brands b ON pr.brand_id = b.brand_id
        WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


def _fetch_retailer_mix_change(brand: str) -> dict:
    """Did the brand expand into new retailers in the recent window?"""
    conn = get_conn()
    sql = f"""
        WITH per_period AS (
          SELECT
            CASE
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'L13W'
              WHEN CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
                   AND CAST(p.week_ending AS DATE) <  (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 13 WEEK
                   THEN 'P13W'
            END AS period_label,
            r.retailer_name
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands b ON pr.brand_id = b.brand_id
          JOIN retailers r ON p.retailer_id = r.retailer_id
          WHERE b.brand_name = '{brand.replace(chr(39), chr(39)*2)}'
            AND CAST(p.week_ending AS DATE) >= (SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly) - INTERVAL 26 WEEK
          GROUP BY period_label, r.retailer_name
        )
        SELECT
          COUNT(DISTINCT CASE WHEN period_label='L13W' THEN retailer_name END) AS current_retailer_count,
          COUNT(DISTINCT CASE WHEN period_label='P13W' THEN retailer_name END) AS prior_retailer_count,
          STRING_AGG(DISTINCT CASE
            WHEN period_label='L13W' AND retailer_name NOT IN (
              SELECT retailer_name FROM per_period WHERE period_label='P13W'
            ) THEN retailer_name END, ', ') AS newly_added_retailers
        FROM per_period
    """
    return conn.execute(sql).fetchdf().to_dict("records")[0] if conn.execute(sql).fetchdf().shape[0] else {}


# ─────────────────────────────────────────────────────────────────────────────
# Hypothesis builders — turn raw evidence into ranked hypotheses
# ─────────────────────────────────────────────────────────────────────────────

def _direction_from_delta(delta: float, share_change_sign: int) -> str:
    """A positive delta in this driver supports a gain when both signs align."""
    if abs(delta) < 0.01:
        return "neutral"
    if (delta > 0 and share_change_sign > 0) or (delta < 0 and share_change_sign < 0):
        return "supports_gain" if share_change_sign > 0 else "supports_loss"
    return "supports_loss" if share_change_sign > 0 else "supports_gain"


def _build_hypotheses(brand: str, category: Optional[str], share: dict) -> list[Hypothesis]:
    sign = 1 if share.get("share_pt_change", 0) >= 0 else -1
    hyps: list[Hypothesis] = []

    # 1. DISTRIBUTION
    d = _fetch_distribution_change(brand)
    cur_acv = d.get("current_acv_pct") or 0
    prior_acv = d.get("prior_acv_pct") or 0
    acv_delta = round(cur_acv - prior_acv, 1)
    hyps.append(Hypothesis(
        family="DISTRIBUTION",
        headline=f"ACV {'+' if acv_delta>=0 else ''}{acv_delta} pts ({prior_acv}% → {cur_acv}%)",
        direction=_direction_from_delta(acv_delta, sign),
        magnitude=min(100, abs(acv_delta) * 6),
        confidence="high" if abs(acv_delta) >= 2 else "medium" if abs(acv_delta) >= 0.5 else "low",
        evidence=d | {"acv_pt_change": acv_delta},
    ))

    # 2. VELOCITY
    v = _fetch_velocity_change(brand)
    cur_vel = v.get("current_dpsw") or 0
    prior_vel = v.get("prior_dpsw") or 0
    vel_delta_pct = round(100.0 * (cur_vel - prior_vel) / prior_vel, 1) if prior_vel else 0
    hyps.append(Hypothesis(
        family="VELOCITY",
        headline=f"Velocity {'+' if vel_delta_pct>=0 else ''}{vel_delta_pct}% (${prior_vel:.0f} → ${cur_vel:.0f}/store/wk)",
        direction=_direction_from_delta(vel_delta_pct, sign),
        magnitude=min(100, abs(vel_delta_pct) * 2.5),
        confidence="high" if abs(vel_delta_pct) >= 8 else "medium" if abs(vel_delta_pct) >= 3 else "low",
        evidence=v | {"velocity_pct_change": vel_delta_pct},
    ))

    # 3. PRICING
    p = _fetch_pricing_change(brand, category)
    cur_pi = p.get("current_price_index") or 0
    prior_pi = p.get("prior_price_index") or 0
    pi_delta = round(cur_pi - prior_pi, 1)
    # Lower price index supports a share gain (cheaper = more attractive)
    pricing_direction = _direction_from_delta(-pi_delta, sign)
    hyps.append(Hypothesis(
        family="PRICING",
        headline=f"Price index {'+' if pi_delta>=0 else ''}{pi_delta} pts ({prior_pi} → {cur_pi})",
        direction=pricing_direction,
        magnitude=min(100, abs(pi_delta) * 4),
        confidence="high" if abs(pi_delta) >= 3 else "medium" if abs(pi_delta) >= 1 else "low",
        evidence=p | {"price_index_pt_change": pi_delta},
    ))

    # 4. PROMOTION
    pr = _fetch_promo_change(brand)
    cur_promo = pr.get("current_pct_on_promo") or 0
    prior_promo = pr.get("prior_pct_on_promo") or 0
    promo_delta = round(cur_promo - prior_promo, 1)
    hyps.append(Hypothesis(
        family="PROMOTION",
        headline=f"% Volume on promo {'+' if promo_delta>=0 else ''}{promo_delta} pts ({prior_promo}% → {cur_promo}%)",
        direction=_direction_from_delta(promo_delta, sign),
        magnitude=min(100, abs(promo_delta) * 3),
        confidence="high" if abs(promo_delta) >= 5 else "medium" if abs(promo_delta) >= 2 else "low",
        evidence=pr | {"promo_pct_change": promo_delta},
    ))

    # 5. INNOVATION
    inn = _fetch_innovation_signal(brand)
    weeks_since = inn.get("weeks_since_launch") or 9999
    is_recent = weeks_since <= 78  # <= 18 months
    hyps.append(Hypothesis(
        family="INNOVATION",
        headline=(f"Brand launched {weeks_since} weeks ago - still on Year-1 launch curve"
                  if is_recent else f"Established brand - launched {weeks_since} weeks ago"),
        direction="supports_gain" if (is_recent and sign > 0) else "neutral",
        magnitude=max(0, min(100, (80 - weeks_since) * 1.2)) if is_recent else 0,
        confidence="high" if weeks_since <= 52 else "medium" if weeks_since <= 78 else "low",
        evidence=inn,
    ))

    # 6. RETAILER MIX
    rm = _fetch_retailer_mix_change(brand)
    cur_r = rm.get("current_retailer_count") or 0
    prior_r = rm.get("prior_retailer_count") or 0
    rcount_delta = cur_r - prior_r
    new_rs = rm.get("newly_added_retailers") or ""
    hyps.append(Hypothesis(
        family="RETAILER_MIX",
        headline=(f"Expanded to {rcount_delta} new retailers ({prior_r} → {cur_r})"
                  if rcount_delta > 0 else
                  f"Lost {abs(rcount_delta)} retailers ({prior_r} → {cur_r})" if rcount_delta < 0 else
                  f"Retailer footprint unchanged ({cur_r} retailers)"),
        direction=_direction_from_delta(rcount_delta, sign),
        magnitude=min(100, abs(rcount_delta) * 18),
        confidence="high" if abs(rcount_delta) >= 2 else "medium" if abs(rcount_delta) >= 1 else "low",
        evidence=rm | {"retailer_count_change": rcount_delta, "newly_added": new_rs},
    ))

    # Sort by magnitude, supporting hypotheses on top
    hyps.sort(key=lambda h: (h.direction == "neutral", -h.magnitude))
    return hyps


# ─────────────────────────────────────────────────────────────────────────────
# Narration — LLM passes for per-hypothesis explanations + executive summary
# ─────────────────────────────────────────────────────────────────────────────

def _narrate_hypothesis(brand: str, h: Hypothesis, share: dict) -> str:
    system = (
        "You are a CPG/GM market insights analyst. Write a single 1-2 sentence "
        "explanation grounded in the evidence numbers provided. Use industry vocabulary "
        "(ACV, velocity, price index, promo lift, distribution). Do not invent numbers."
    )
    prompt = (
        f"Brand: {brand}\n"
        f"Share movement: {share.get('prior_share_pct')}% -> {share.get('current_share_pct')}% "
        f"(change: {share.get('share_pt_change')} pts)\n"
        f"Hypothesis family: {h.family}\n"
        f"Headline: {h.headline}\n"
        f"Direction: {h.direction}\n"
        f"Evidence: {json.dumps(h.evidence, default=str)}\n\n"
        f"Write the 1-2 sentence explanation."
    )
    try:
        return _call_groq(system, [{"role": "user", "content": prompt}], max_tokens=180)
    except Exception:
        return h.headline


def _executive_summary(brand: str, category: Optional[str], share: dict,
                       hyps: list[Hypothesis]) -> str:
    top = [h for h in hyps if h.direction != "neutral"][:3]
    system = (
        "You are a CPG/GM market insights analyst. Write a 3-4 sentence executive "
        "summary explaining why share is moving for this brand, citing the top 2-3 "
        "drivers with their evidence. Be specific. End with one suggested action."
    )
    prompt = (
        f"Brand: {brand}\nCategory: {category or 'all'}\n"
        f"Share movement: {share.get('prior_share_pct')}% -> {share.get('current_share_pct')}% "
        f"(change: {share.get('share_pt_change')} pts)\n"
        f"Top hypotheses:\n" +
        "\n".join(f"  - {h.family}: {h.headline} (direction: {h.direction}, magnitude: {h.magnitude:.0f})"
                  for h in top) +
        "\n\nWrite the executive summary."
    )
    try:
        return _call_groq(system, [{"role": "user", "content": prompt}], max_tokens=320)
    except Exception:
        return (
            f"{brand} moved {share.get('share_pt_change', 0):+.2f} share points. "
            f"Top driver: {top[0].headline if top else 'no significant driver'}."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def investigate(brand_name: str, category_name: Optional[str] = None) -> dict:
    share = _fetch_share_movement(brand_name, category_name)
    if category_name is None:
        category_name = share.get("category_name")
    hyps = _build_hypotheses(brand_name, category_name, share)
    # Narrate hypotheses + summary in parallel (each call is ~20s through the
    # claude CLI, so 7 calls sequential = ~2.5 min, parallel = ~20-30 s).
    with ThreadPoolExecutor(max_workers=8) as pool:
        narr_futures = [
            pool.submit(_narrate_hypothesis, brand_name, h, share) for h in hyps
        ]
        summary_future = pool.submit(
            _executive_summary, brand_name, category_name, share, hyps
        )
        for h, fut in zip(hyps, narr_futures):
            h.narrative = fut.result()
        summary = summary_future.result()
    return {
        "brand_name":     brand_name,
        "category_name":  category_name,
        "share_movement": share,
        "hypotheses": [asdict(h) for h in hyps],
        "summary":        summary,
        "generated_at":   datetime.utcnow().isoformat(),
    }
