-- =============================================================================
-- Circana-style Market Insights — Schema (CPG + GM)
-- Target: DuckDB (dev) / Snowflake / BigQuery (prod). DDL is portable.
-- =============================================================================

-- ── Dimensions ───────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE retailers (
  retailer_id              VARCHAR PRIMARY KEY,
  retailer_name            VARCHAR NOT NULL,
  channel                  VARCHAR NOT NULL,   -- Mass / Grocery / Club / eCommerce / Drug / Beauty Specialty / Electronics / Home Improvement
  region                   VARCHAR,
  total_stores             INTEGER,
  channel_acv_share_pct    DECIMAL(5,2)
);

CREATE OR REPLACE TABLE manufacturers (
  manufacturer_id          VARCHAR PRIMARY KEY,
  manufacturer_name        VARCHAR NOT NULL,
  hq_country               VARCHAR,
  is_private_label         BOOLEAN
);

CREATE OR REPLACE TABLE categories (
  category_id              VARCHAR PRIMARY KEY,
  department               VARCHAR NOT NULL,    -- CPG-Food / CPG-Beverage / CPG-Beauty / CPG-HBA / GM-Electronics / GM-Toys / GM-Home
  category_name            VARCHAR NOT NULL,
  sub_category             VARCHAR,
  total_market_dollars_mm  DECIMAL(12,1)
);

CREATE OR REPLACE TABLE brands (
  brand_id                 VARCHAR PRIMARY KEY,
  brand_name               VARCHAR NOT NULL,
  manufacturer_id          VARCHAR REFERENCES manufacturers(manufacturer_id),
  premium_tier             VARCHAR,             -- Value / Mainstream / Premium
  primary_category_id      VARCHAR REFERENCES categories(category_id),
  share_trend              VARCHAR              -- strong_up / up / flat / down / strong_down
);

CREATE OR REPLACE TABLE products (
  sku_id                   VARCHAR PRIMARY KEY,
  sku_description          VARCHAR NOT NULL,
  brand_id                 VARCHAR REFERENCES brands(brand_id),
  category_id              VARCHAR REFERENCES categories(category_id),
  pack_size                VARCHAR,
  unit_of_measure          VARCHAR,
  list_price               DECIMAL(10,2),
  launch_date              DATE
);

-- ── Facts ────────────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE pos_weekly (
  week_ending                     DATE NOT NULL,
  sku_id                          VARCHAR REFERENCES products(sku_id),
  retailer_id                     VARCHAR REFERENCES retailers(retailer_id),
  units                           INTEGER,
  dollars                         DECIMAL(14,2),
  base_units                      INTEGER,
  base_dollars                    DECIMAL(14,2),
  incremental_units               INTEGER,
  incremental_dollars             DECIMAL(14,2),
  avg_price                       DECIMAL(10,2),
  base_price                      DECIMAL(10,2),
  stores_selling                  INTEGER,
  total_stores                    INTEGER,
  acv_weighted_distribution_pct   DECIMAL(5,2),
  on_promo                        BOOLEAN,
  promo_type                      VARCHAR,
  discount_pct                    DECIMAL(5,2),
  PRIMARY KEY (week_ending, sku_id, retailer_id)
);

CREATE OR REPLACE TABLE promo_events (
  promo_id                 VARCHAR PRIMARY KEY,
  sku_id                   VARCHAR REFERENCES products(sku_id),
  retailer_id              VARCHAR REFERENCES retailers(retailer_id),
  start_date               DATE,
  end_date                 DATE,
  promo_type               VARCHAR,
  discount_pct             DECIMAL(5,2),
  incremental_units        INTEGER,
  incremental_dollars      DECIMAL(14,2),
  lift_pct                 DECIMAL(8,2)
);

CREATE OR REPLACE TABLE panel_household (
  period_month             DATE NOT NULL,
  brand_id                 VARCHAR REFERENCES brands(brand_id),
  hh_penetration_pct       DECIMAL(5,2),
  buyers_mm                DECIMAL(8,2),
  trips_per_buyer          DECIMAL(5,2),
  dollars_per_trip         DECIMAL(8,2),
  repeat_rate_pct          DECIMAL(5,2),
  share_of_wallet_pct      DECIMAL(5,2),
  PRIMARY KEY (period_month, brand_id)
);

-- ── Helpful indexes for analytical query patterns ────────────────────────────
CREATE INDEX IF NOT EXISTS idx_pos_week         ON pos_weekly(week_ending);
CREATE INDEX IF NOT EXISTS idx_pos_sku          ON pos_weekly(sku_id);
CREATE INDEX IF NOT EXISTS idx_pos_retailer     ON pos_weekly(retailer_id);
CREATE INDEX IF NOT EXISTS idx_products_brand   ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_cat     ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_brands_mfr       ON brands(manufacturer_id);
