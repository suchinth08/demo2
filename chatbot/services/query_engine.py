"""
Query Engine — translates structured intent into DuckDB queries
and executes them against the CPG / GM Market Insights CSV data files.

For production: swap DuckDB CSV reads for Snowflake / BigQuery via the
same QUERY_LIBRARY (SQL is portable).
"""
from pathlib import Path
import duckdb

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "csv"

# Shared DuckDB connection with all tables pre-registered as views over CSVs
_conn: duckdb.DuckDBPyConnection | None = None

def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        _conn = duckdb.connect()
        _register_tables(_conn)
    return _conn


def _register_tables(conn: duckdb.DuckDBPyConnection) -> None:
    tables = {
        "retailers":         "retailers.csv",
        "categories":        "categories.csv",
        "manufacturers":     "manufacturers.csv",
        "brands":            "brands.csv",
        "products":          "products.csv",
        "pos_weekly":        "pos_weekly.csv",
        "promo_events":      "promo_events.csv",
        "panel_household":   "panel_household.csv",
    }
    for name, filename in tables.items():
        path = DATA_DIR / filename
        if path.exists():
            conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS "
                f"SELECT * FROM read_csv_auto('{path.as_posix()}')"
            )


# ─────────────────────────────────────────────────────────────────────────────
# QUERY LIBRARY — maps intent keys to executable SQL
# Convention: <domain>.<query_name>
# All queries assume the latest 13 weeks unless an explicit time filter
# is injected by route_intent_to_query().
# ─────────────────────────────────────────────────────────────────────────────

# Maximum week_ending in the dataset — used as the anchor for relative-time windows
LATEST_WEEK_SQL = "(SELECT MAX(CAST(week_ending AS DATE)) FROM pos_weekly)"

QUERY_LIBRARY: dict[str, str] = {

    # ── SHARE ────────────────────────────────────────────────────────────
    "share.by_brand_in_category": f"""
        WITH cat_dollars AS (
          SELECT pr.category_id, SUM(p.dollars) AS cat_dollars
          FROM pos_weekly p JOIN products pr ON p.sku_id = pr.sku_id
          WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
          GROUP BY pr.category_id
        )
        SELECT
          c.category_name,
          b.brand_name,
          ROUND(SUM(p.dollars) / 1e6, 2)                   AS dollars_mm,
          ROUND(100.0 * SUM(p.dollars) / MAX(cd.cat_dollars), 2) AS dollar_share_pct
        FROM pos_weekly p
        JOIN products pr      ON p.sku_id        = pr.sku_id
        JOIN brands  b        ON pr.brand_id     = b.brand_id
        JOIN categories c     ON pr.category_id  = c.category_id
        JOIN cat_dollars cd   ON pr.category_id  = cd.category_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY c.category_name, b.brand_name
        HAVING SUM(p.dollars) > 100000
        ORDER BY c.category_name, dollar_share_pct DESC
    """,

    "share.trend_by_brand": f"""
        WITH cat_month AS (
          SELECT pr.category_id,
                 DATE_TRUNC('month', CAST(p.week_ending AS DATE)) AS mo,
                 SUM(p.dollars) AS cat_dollars
          FROM pos_weekly p JOIN products pr ON p.sku_id = pr.sku_id
          GROUP BY pr.category_id, mo
        )
        SELECT
          DATE_TRUNC('month', CAST(p.week_ending AS DATE))     AS month,
          b.brand_name,
          ROUND(100.0 * SUM(p.dollars) / MAX(cm.cat_dollars), 2) AS dollar_share_pct,
          ROUND(SUM(p.dollars) / 1e6, 2)                          AS dollars_mm
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN cat_month cm ON pr.category_id = cm.category_id
                         AND DATE_TRUNC('month', CAST(p.week_ending AS DATE)) = cm.mo
        GROUP BY month, b.brand_name
        HAVING SUM(p.dollars) > 50000
        ORDER BY month, dollar_share_pct DESC
    """,

    "share.top_gainers_losers": f"""
        WITH per_brand_period AS (
          SELECT b.brand_name,
                 c.category_name,
                 CASE
                   WHEN CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
                        THEN 'L13W'
                   WHEN CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 26 WEEK
                        AND CAST(p.week_ending AS DATE) <  {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
                        THEN 'P13W'
                 END AS period_label,
                 SUM(p.dollars) AS dollars,
                 pr.category_id
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN brands   b  ON pr.brand_id = b.brand_id
          JOIN categories c ON pr.category_id = c.category_id
          WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 26 WEEK
          GROUP BY b.brand_name, c.category_name, period_label, pr.category_id
        ),
        cat_period AS (
          SELECT category_id, period_label, SUM(dollars) AS cat_d
          FROM per_brand_period
          WHERE period_label IS NOT NULL
          GROUP BY 1,2
        ),
        share_per_brand AS (
          SELECT pbp.brand_name, pbp.category_name, pbp.period_label,
                 100.0 * pbp.dollars / cp.cat_d AS share_pct
          FROM per_brand_period pbp
          JOIN cat_period cp
            ON pbp.category_id = cp.category_id
           AND pbp.period_label = cp.period_label
          WHERE pbp.period_label IS NOT NULL
        )
        SELECT brand_name, category_name,
               ROUND(MAX(CASE WHEN period_label='L13W' THEN share_pct END), 2) AS current_share_pct,
               ROUND(MAX(CASE WHEN period_label='P13W' THEN share_pct END), 2) AS prior_share_pct,
               ROUND(MAX(CASE WHEN period_label='L13W' THEN share_pct END)
                   - MAX(CASE WHEN period_label='P13W' THEN share_pct END), 2) AS share_pt_change
        FROM share_per_brand
        GROUP BY brand_name, category_name
        HAVING current_share_pct > 0.5 AND prior_share_pct > 0.5
        ORDER BY share_pt_change DESC
        LIMIT 25
    """,

    "share.by_retailer": f"""
        WITH retailer_cat AS (
          SELECT pr.category_id, p.retailer_id, SUM(p.dollars) AS rc_dollars
          FROM pos_weekly p JOIN products pr ON p.sku_id = pr.sku_id
          WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
          GROUP BY 1,2
        )
        SELECT
          r.retailer_name,
          c.category_name,
          b.brand_name,
          ROUND(SUM(p.dollars) / 1e6, 2)                            AS dollars_mm,
          ROUND(100.0 * SUM(p.dollars) / MAX(rc.rc_dollars), 2)     AS share_in_retailer_pct
        FROM pos_weekly p
        JOIN products pr  ON p.sku_id        = pr.sku_id
        JOIN brands  b    ON pr.brand_id     = b.brand_id
        JOIN categories c ON pr.category_id  = c.category_id
        JOIN retailers r  ON p.retailer_id   = r.retailer_id
        JOIN retailer_cat rc ON pr.category_id = rc.category_id
                            AND p.retailer_id  = rc.retailer_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY r.retailer_name, c.category_name, b.brand_name
        HAVING SUM(p.dollars) > 50000
        ORDER BY r.retailer_name, c.category_name, share_in_retailer_pct DESC
    """,

    # ── VELOCITY ─────────────────────────────────────────────────────────
    "velocity.ranking": f"""
        SELECT
          b.brand_name,
          c.category_name,
          ROUND(SUM(p.dollars) / NULLIF(SUM(p.stores_selling), 0), 2) AS dollars_per_store_per_week,
          ROUND(SUM(p.units)   / NULLIF(SUM(p.stores_selling), 0), 2) AS units_per_store_per_week,
          ROUND(AVG(p.acv_weighted_distribution_pct), 1)              AS avg_acv_pct,
          ROUND(SUM(p.dollars) / 1e6, 2)                              AS dollars_mm
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY b.brand_name, c.category_name
        HAVING SUM(p.stores_selling) > 0
        ORDER BY dollars_per_store_per_week DESC
        LIMIT 30
    """,

    "velocity.by_retailer": f"""
        SELECT
          r.retailer_name,
          b.brand_name,
          ROUND(SUM(p.dollars) / NULLIF(SUM(p.stores_selling), 0), 2) AS dollars_per_store_per_week,
          ROUND(AVG(p.acv_weighted_distribution_pct), 1)              AS avg_acv_pct,
          ROUND(SUM(p.dollars), 0)                                    AS dollars_total
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN retailers r ON p.retailer_id = r.retailer_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY r.retailer_name, b.brand_name
        HAVING SUM(p.stores_selling) > 0
        ORDER BY r.retailer_name, dollars_per_store_per_week DESC
    """,

    # ── DISTRIBUTION ─────────────────────────────────────────────────────
    "distribution.acv_by_brand_retailer": f"""
        SELECT
          r.retailer_name,
          b.brand_name,
          ROUND(AVG(p.acv_weighted_distribution_pct), 1) AS avg_acv_pct,
          ROUND(100 - AVG(p.acv_weighted_distribution_pct), 1) AS distribution_gap_pct,
          SUM(p.stores_selling) / COUNT(DISTINCT p.week_ending) AS avg_stores_selling
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN retailers r ON p.retailer_id = r.retailer_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY r.retailer_name, b.brand_name
        ORDER BY r.retailer_name, distribution_gap_pct DESC
    """,

    "distribution.gaps_high_velocity": f"""
        SELECT
          b.brand_name, c.category_name,
          ROUND(AVG(p.acv_weighted_distribution_pct), 1)              AS avg_acv_pct,
          ROUND(100 - AVG(p.acv_weighted_distribution_pct), 1)         AS distribution_gap_pct,
          ROUND(SUM(p.dollars) / NULLIF(SUM(p.stores_selling), 0), 2)  AS dollars_per_store_per_week,
          ROUND(SUM(p.dollars) / 1e6, 2)                               AS dollars_mm
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY b.brand_name, c.category_name
        HAVING AVG(p.acv_weighted_distribution_pct) < 70
           AND SUM(p.dollars) / NULLIF(SUM(p.stores_selling), 0) > 200
        ORDER BY distribution_gap_pct DESC, dollars_per_store_per_week DESC
        LIMIT 20
    """,

    # ── PRICING ──────────────────────────────────────────────────────────
    "pricing.gap_vs_category": f"""
        WITH cat_avg AS (
          SELECT pr.category_id,
                 AVG(p.avg_price) AS cat_avg_price
          FROM pos_weekly p JOIN products pr ON p.sku_id = pr.sku_id
          WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
          GROUP BY pr.category_id
        )
        SELECT
          c.category_name,
          b.brand_name,
          ROUND(AVG(p.avg_price), 2)                              AS brand_avg_price,
          ROUND(MAX(ca.cat_avg_price), 2)                         AS category_avg_price,
          ROUND(100.0 * AVG(p.avg_price) / MAX(ca.cat_avg_price), 1) AS price_index
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        JOIN cat_avg ca   ON pr.category_id = ca.category_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY c.category_name, b.brand_name
        ORDER BY c.category_name, price_index DESC
    """,

    # ── PROMOTION ────────────────────────────────────────────────────────
    "promotion.lift_by_brand": f"""
        SELECT
          b.brand_name,
          c.category_name,
          ROUND(100.0 * SUM(p.incremental_units) / NULLIF(SUM(p.base_units), 0), 1) AS promo_lift_pct,
          ROUND(100.0 * SUM(CASE WHEN p.on_promo THEN p.units END)
              / NULLIF(SUM(p.units), 0), 1) AS pct_volume_on_promo,
          ROUND(SUM(p.incremental_dollars) / 1e6, 2) AS incremental_dollars_mm
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
        GROUP BY b.brand_name, c.category_name
        HAVING SUM(p.base_units) > 1000
        ORDER BY promo_lift_pct DESC
        LIMIT 25
    """,

    "promotion.roi_ranking": """
        SELECT
          b.brand_name, c.category_name,
          pe.promo_type,
          COUNT(*)                                          AS event_count,
          ROUND(AVG(pe.lift_pct), 1)                        AS avg_lift_pct,
          ROUND(SUM(pe.incremental_dollars) / 1e6, 3)       AS incremental_dollars_mm,
          ROUND(AVG(pe.discount_pct), 1)                    AS avg_discount_pct
        FROM promo_events pe
        JOIN products pr ON pe.sku_id    = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        GROUP BY b.brand_name, c.category_name, pe.promo_type
        HAVING COUNT(*) >= 5
        ORDER BY avg_lift_pct DESC
        LIMIT 25
    """,

    # ── PANEL ────────────────────────────────────────────────────────────
    "panel.penetration_by_brand": f"""
        SELECT
          b.brand_name, c.category_name,
          ROUND(AVG(ph.hh_penetration_pct), 1) AS hh_penetration_pct,
          ROUND(AVG(ph.buyers_mm), 2)          AS buyers_mm,
          ROUND(AVG(ph.trips_per_buyer), 2)    AS trips_per_buyer,
          ROUND(AVG(ph.dollars_per_trip), 2)   AS dollars_per_trip,
          ROUND(AVG(ph.repeat_rate_pct), 1)    AS repeat_rate_pct
        FROM panel_household ph
        JOIN brands b   ON ph.brand_id = b.brand_id
        JOIN categories c ON b.primary_category_id = c.category_id
        WHERE CAST(ph.period_month AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 6 MONTH
        GROUP BY b.brand_name, c.category_name
        ORDER BY hh_penetration_pct DESC
        LIMIT 30
    """,

    "panel.penetration_trend": """
        SELECT
          ph.period_month,
          b.brand_name,
          ROUND(ph.hh_penetration_pct, 2) AS hh_penetration_pct,
          ROUND(ph.buyers_mm, 2)          AS buyers_mm
        FROM panel_household ph
        JOIN brands b ON ph.brand_id = b.brand_id
        ORDER BY ph.period_month, hh_penetration_pct DESC
    """,

    # ── INNOVATION / PACESETTER ──────────────────────────────────────────
    "innovation.pacesetter_watch": f"""
        SELECT
          b.brand_name,
          c.category_name,
          pr.launch_date,
          ROUND(SUM(p.dollars) / 1e6, 2)                               AS year1_dollars_mm,
          ROUND(SUM(p.units) / 1e3, 1)                                  AS year1_units_k,
          ROUND(AVG(p.acv_weighted_distribution_pct), 1)                AS avg_acv_pct,
          ROUND(SUM(p.dollars) / NULLIF(SUM(p.stores_selling), 0), 2)   AS dollars_per_store_per_week,
          MIN(p.week_ending)                                            AS first_week,
          MAX(p.week_ending)                                            AS latest_week
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN brands  b   ON pr.brand_id  = b.brand_id
        JOIN categories c ON pr.category_id = c.category_id
        WHERE CAST(pr.launch_date AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 18 MONTH
        GROUP BY b.brand_name, c.category_name, pr.launch_date
        HAVING SUM(p.dollars) > 100000
        ORDER BY year1_dollars_mm DESC
        LIMIT 20
    """,

    # ── CATEGORY HEALTH ──────────────────────────────────────────────────
    "category.growth": f"""
        WITH per_period AS (
          SELECT c.category_name,
                 CASE
                   WHEN CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
                        THEN 'L13W'
                   WHEN CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 26 WEEK
                        AND CAST(p.week_ending AS DATE) <  {LATEST_WEEK_SQL} - INTERVAL 13 WEEK
                        THEN 'P13W'
                 END AS period_label,
                 SUM(p.dollars) AS dollars
          FROM pos_weekly p
          JOIN products pr ON p.sku_id = pr.sku_id
          JOIN categories c ON pr.category_id = c.category_id
          WHERE CAST(p.week_ending AS DATE) >= {LATEST_WEEK_SQL} - INTERVAL 26 WEEK
          GROUP BY 1, 2
        )
        SELECT category_name,
               ROUND(MAX(CASE WHEN period_label='L13W' THEN dollars END) / 1e6, 2) AS current_dollars_mm,
               ROUND(MAX(CASE WHEN period_label='P13W' THEN dollars END) / 1e6, 2) AS prior_dollars_mm,
               ROUND(100.0 * (MAX(CASE WHEN period_label='L13W' THEN dollars END)
                            - MAX(CASE WHEN period_label='P13W' THEN dollars END))
                          / NULLIF(MAX(CASE WHEN period_label='P13W' THEN dollars END), 0), 1) AS growth_pct
        FROM per_period
        WHERE period_label IS NOT NULL
        GROUP BY category_name
        ORDER BY growth_pct DESC
    """,

    "category.trend_monthly": """
        SELECT
          DATE_TRUNC('month', CAST(p.week_ending AS DATE)) AS month,
          c.category_name,
          ROUND(SUM(p.dollars) / 1e6, 2)                   AS dollars_mm,
          SUM(p.units)                                     AS units
        FROM pos_weekly p
        JOIN products pr ON p.sku_id     = pr.sku_id
        JOIN categories c ON pr.category_id = c.category_id
        GROUP BY month, c.category_name
        ORDER BY month
    """,
}


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def execute_query(query_key: str, extra_filters: dict | None = None) -> list[dict]:
    """Execute a named query, optionally injecting extra WHERE conditions."""
    if query_key not in QUERY_LIBRARY:
        raise ValueError(f"Unknown query key: {query_key}. Available: {list(QUERY_LIBRARY.keys())}")
    sql = QUERY_LIBRARY[query_key]

    conn = get_conn()

    if extra_filters:
        # Introspect the subquery's columns first — only apply filters whose
        # field is actually emitted, otherwise DuckDB raises "Column not found"
        # (the LLM sometimes asks for category_name on a query that doesn't
        # project it, etc.).
        try:
            schema = conn.execute(f"SELECT * FROM ({sql}) AS sub LIMIT 0").description
            available_cols = {c[0] for c in schema}
        except Exception:
            available_cols = set()

        conditions = []
        for field, value in extra_filters.items():
            if field not in available_cols:
                continue
            if isinstance(value, str):
                safe_val = value.replace("'", "''")
                conditions.append(f"{field} = '{safe_val}'")
            elif isinstance(value, list):
                vals = ", ".join(f"'{str(v).replace(chr(39), chr(39)*2)}'" for v in value)
                conditions.append(f"{field} IN ({vals})")
            elif isinstance(value, dict) and "gte" in value:
                conditions.append(f"{field} >= '{value['gte']}'")
        if conditions:
            where_clause = " AND ".join(conditions)
            sql = f"SELECT * FROM ({sql}) AS sub WHERE {where_clause}"

    result = conn.execute(sql).fetchdf()
    return result.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# INTENT ROUTING
# ─────────────────────────────────────────────────────────────────────────────

def route_intent_to_query(intent: dict) -> tuple[str, dict | None]:
    """Map a structured intent dict to a query key + optional filter overrides."""
    domain      = (intent.get("domain") or "").lower()
    intent_type = (intent.get("intent") or "").upper()
    dimensions  = intent.get("dimensions") or []
    filters     = intent.get("filters") or []

    # Only inject filters for known dimension fields with concrete values.
    # The LLM occasionally produces vague filters like
    # {field: "dollars_per_store_per_week", value: "average"} — those would
    # break the underlying query if applied literally.
    ALLOWED_FILTER_FIELDS = {
        "brand_name", "category_name", "sub_category", "department",
        "retailer_name", "channel", "region",
        "manufacturer_name", "is_private_label", "premium_tier",
        "on_promo", "promo_type",
    }
    VAGUE_VALUES = {"average", "avg", "high", "low", "above average",
                    "below average", "any", "all", "none", "n/a"}

    extra: dict = {}
    for f in filters:
        if not (isinstance(f, dict) and "field" in f and "value" in f):
            continue
        field = f["field"]
        value = f["value"]
        if field not in ALLOWED_FILTER_FIELDS:
            continue
        if isinstance(value, str) and value.strip().lower() in VAGUE_VALUES:
            continue
        extra[field] = value

    # Static routes
    static_map: dict[tuple, str] = {
        ("share", "METRIC_SNAPSHOT"):        "share.by_brand_in_category",
        ("share", "BREAKDOWN"):              "share.by_brand_in_category",
        ("share", "RANKING"):                "share.by_brand_in_category",
        ("share", "TREND_ANALYSIS"):         "share.trend_by_brand",
        ("share", "SHARE_MOVEMENT"):         "share.top_gainers_losers",
        ("share", "ANOMALY_DETECTION"):      "share.top_gainers_losers",
        ("share", "COMPARISON"):             "share.by_retailer",

        ("velocity", "METRIC_SNAPSHOT"):     "velocity.ranking",
        ("velocity", "RANKING"):             "velocity.ranking",
        ("velocity", "BREAKDOWN"):           "velocity.by_retailer",
        ("velocity", "COMPARISON"):          "velocity.by_retailer",

        ("distribution", "METRIC_SNAPSHOT"): "distribution.acv_by_brand_retailer",
        ("distribution", "BREAKDOWN"):       "distribution.acv_by_brand_retailer",
        ("distribution", "DISTRIBUTION_GAP"):"distribution.gaps_high_velocity",
        ("distribution", "RANKING"):         "distribution.gaps_high_velocity",
        ("distribution", "DRILL_DOWN"):      "distribution.acv_by_brand_retailer",

        ("pricing", "METRIC_SNAPSHOT"):      "pricing.gap_vs_category",
        ("pricing", "BREAKDOWN"):            "pricing.gap_vs_category",
        ("pricing", "PRICE_GAP"):            "pricing.gap_vs_category",
        ("pricing", "COMPARISON"):           "pricing.gap_vs_category",

        ("promotion", "METRIC_SNAPSHOT"):    "promotion.lift_by_brand",
        ("promotion", "BREAKDOWN"):          "promotion.lift_by_brand",
        ("promotion", "PROMO_EFFECTIVENESS"):"promotion.roi_ranking",
        ("promotion", "RANKING"):            "promotion.roi_ranking",

        ("panel", "METRIC_SNAPSHOT"):        "panel.penetration_by_brand",
        ("panel", "BREAKDOWN"):              "panel.penetration_by_brand",
        ("panel", "RANKING"):                "panel.penetration_by_brand",
        ("panel", "TREND_ANALYSIS"):         "panel.penetration_trend",
        ("panel", "PANEL_DEEP_DIVE"):        "panel.penetration_by_brand",

        ("innovation", "METRIC_SNAPSHOT"):   "innovation.pacesetter_watch",
        ("innovation", "PACESETTER_WATCH"):  "innovation.pacesetter_watch",
        ("innovation", "RANKING"):           "innovation.pacesetter_watch",
        ("innovation", "TREND_ANALYSIS"):    "innovation.pacesetter_watch",

        ("category", "TREND_ANALYSIS"):      "category.trend_monthly",
        ("category", "BREAKDOWN"):           "category.growth",
        ("category", "RANKING"):             "category.growth",
        ("category", "METRIC_SNAPSHOT"):     "category.growth",
    }

    query_key = static_map.get((domain, intent_type))

    # Fallback by domain
    if query_key is None:
        fallback = {
            "share":        "share.by_brand_in_category",
            "velocity":     "velocity.ranking",
            "distribution": "distribution.acv_by_brand_retailer",
            "pricing":      "pricing.gap_vs_category",
            "promotion":    "promotion.lift_by_brand",
            "panel":        "panel.penetration_by_brand",
            "innovation":   "innovation.pacesetter_watch",
            "category":     "category.growth",
        }
        query_key = fallback.get(domain, "share.by_brand_in_category")

    # Dimension-aware tweaks
    if "retailer_name" in dimensions and domain == "share":
        query_key = "share.by_retailer"
    if "retailer_name" in dimensions and domain == "velocity":
        query_key = "velocity.by_retailer"

    return query_key, extra if extra else None
