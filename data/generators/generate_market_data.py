"""
Circana-style Market Insights - Synthetic Data Generator (CPG + GM)
Produces a coherent panel of POS, distribution, panel, and promo data with
deliberate, demo-quality storylines baked in:
  - Celsius surging in Energy Drinks (taking share from Bang)
  - Coca-Cola gaining vs PepsiCo in CSDs late 2024
  - CeraVe taking share from Olay in Skincare
  - "Liquid Death" Sparkling Water - Year-1 Pacesetter trajectory
  - A clear price-gap story: Doritos vs Pringles in Kroger
  - Walmart soft in CSDs Q4 2024 (loses share to Amazon)
  - LEGO holiday spike; Apple Q4 dominance in Electronics

Usage: python -m data.generators.generate_market_data
Output: data/csv/*.csv (consumed by DuckDB)
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)

OUT_DIR = Path(__file__).parent.parent / "csv"
OUT_DIR.mkdir(exist_ok=True)

# Window: 104 weeks ending late 2024
END_WEEK = date(2024, 12, 28)          # Saturday
START_WEEK = END_WEEK - timedelta(weeks=103)
WEEKS = [START_WEEK + timedelta(weeks=i) for i in range(104)]


def write_csv(filename: str, rows: list[dict], headers: list[str]) -> None:
    path = OUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {len(rows):>6,} rows  ->  {filename}")


# -----------------------------------------------------------------------------
# DIMENSION TABLES
# -----------------------------------------------------------------------------

RETAILERS = [
    # retailer_id, name, channel, region, total_stores, channel_acv_share_pct
    ("RET-001", "Walmart",         "Mass",                "USA", 4615, 18.4),
    ("RET-002", "Target",          "Mass",                "USA", 1956,  6.2),
    ("RET-003", "Kroger",          "Grocery",             "USA", 2719,  9.1),
    ("RET-004", "Albertsons",      "Grocery",             "USA", 2271,  5.4),
    ("RET-005", "Publix",          "Grocery",             "USA", 1356,  3.2),
    ("RET-006", "Whole Foods",     "Grocery",             "USA",  535,  1.1),
    ("RET-007", "Costco",          "Club",                "USA",  600,  5.9),
    ("RET-008", "Sam's Club",      "Club",                "USA",  600,  3.7),
    ("RET-009", "Amazon",          "eCommerce",           "USA",    1, 14.5),
    ("RET-010", "CVS",             "Drug",                "USA", 9967,  3.4),
    ("RET-011", "Walgreens",       "Drug",                "USA", 8886,  3.1),
    ("RET-012", "Sephora",         "Beauty Specialty",    "USA",  600,  1.0),
    ("RET-013", "Ulta Beauty",     "Beauty Specialty",    "USA", 1385,  1.4),
    ("RET-014", "Best Buy",        "Electronics",         "USA",  977,  2.0),
    ("RET-015", "Home Depot",      "Home Improvement",    "USA", 2335,  3.0),
]
RETAILER_HEADERS = ["retailer_id", "retailer_name", "channel", "region",
                    "total_stores", "channel_acv_share_pct"]

CATEGORIES = [
    # category_id, department, category_name, sub_category, total_market_dollars_mm
    ("CAT-001", "CPG-Food",        "Salty Snacks",         "Tortilla Chips",  6200),
    ("CAT-002", "CPG-Food",        "Salty Snacks",         "Potato Chips",    7800),
    ("CAT-003", "CPG-Food",        "Cookies",              "Sandwich Cookies", 4100),
    ("CAT-004", "CPG-Food",        "Cereal",               "Ready-to-Eat",   10200),
    ("CAT-005", "CPG-Beverage",    "Carbonated Beverages", "Regular CSDs",   23400),
    ("CAT-006", "CPG-Beverage",    "Carbonated Beverages", "Diet CSDs",      11700),
    ("CAT-007", "CPG-Beverage",    "Sparkling Water",      "Flavored",        3900),
    ("CAT-008", "CPG-Beverage",    "Energy Drinks",        "Performance",     8700),
    ("CAT-009", "CPG-Beauty",      "Skincare",             "Facial Cleanser", 2900),
    ("CAT-010", "CPG-Beauty",      "Skincare",             "Moisturizer",     5800),
    ("CAT-011", "CPG-Beauty",      "Color Cosmetics",      "Foundation",      2400),
    ("CAT-012", "CPG-HBA",         "Oral Care",            "Toothpaste",      3200),
    ("CAT-013", "CPG-HBA",         "Personal Wash",        "Body Wash",       2700),
    ("CAT-014", "GM-Electronics",  "Smartphones",          "Premium",        88500),
    ("CAT-015", "GM-Electronics",  "Headphones",           "Wireless",        9400),
    ("CAT-016", "GM-Electronics",  "Televisions",          "OLED/QLED",      24300),
    ("CAT-017", "GM-Toys",         "Building Sets",        "Plastic Bricks",  4100),
    ("CAT-018", "GM-Toys",         "Dolls",                "Fashion Dolls",   2200),
    ("CAT-019", "GM-Home",         "Small Appliances",     "Coffee Makers",   3700),
    ("CAT-020", "GM-Home",         "Vacuums",              "Robotic",         2900),
]
CATEGORY_HEADERS = ["category_id", "department", "category_name",
                    "sub_category", "total_market_dollars_mm"]

# manufacturer_id, name, country, is_private_label
MANUFACTURERS = [
    ("MFR-001", "PepsiCo",                 "USA", False),
    ("MFR-002", "The Coca-Cola Company",   "USA", False),
    ("MFR-003", "Keurig Dr Pepper",        "USA", False),
    ("MFR-004", "Mondelez International",  "USA", False),
    ("MFR-005", "Kellanova",               "USA", False),
    ("MFR-006", "General Mills",           "USA", False),
    ("MFR-007", "Post Holdings",           "USA", False),
    ("MFR-008", "Nestle",                  "Switzerland", False),
    ("MFR-009", "National Beverage",       "USA", False),
    ("MFR-010", "Celsius Holdings",        "USA", False),
    ("MFR-011", "Monster Beverage",        "USA", False),
    ("MFR-012", "Red Bull GmbH",           "Austria", False),
    ("MFR-013", "Liquid Death Inc.",       "USA", False),
    ("MFR-014", "L'Oreal Group",           "France", False),
    ("MFR-015", "Procter & Gamble",        "USA", False),
    ("MFR-016", "Unilever",                "UK", False),
    ("MFR-017", "Estee Lauder Companies",  "USA", False),
    ("MFR-018", "Colgate-Palmolive",       "USA", False),
    ("MFR-019", "Apple Inc.",              "USA", False),
    ("MFR-020", "Samsung Electronics",     "South Korea", False),
    ("MFR-021", "Sony Group",              "Japan", False),
    ("MFR-022", "LG Electronics",          "South Korea", False),
    ("MFR-023", "Bose Corporation",        "USA", False),
    ("MFR-024", "The LEGO Group",          "Denmark", False),
    ("MFR-025", "Mattel",                  "USA", False),
    ("MFR-026", "Hasbro",                  "USA", False),
    ("MFR-027", "Keurig",                  "USA", False),  # small appliances
    ("MFR-028", "iRobot (Amazon)",         "USA", False),
    ("MFR-029", "SharkNinja",              "USA", False),
    ("MFR-030", "Private Label",           "USA", True),
]
MANUFACTURER_HEADERS = ["manufacturer_id", "manufacturer_name", "hq_country", "is_private_label"]

# (brand_id, brand_name, manufacturer_id, category_ids[], premium_tier, share_trend)
# share_trend in {strong_up, up, flat, down, strong_down} - drives the story
BRANDS_RAW = [
    # Salty Snacks
    ("BRD-001", "Doritos",              "MFR-001", ["CAT-001"], "Mainstream", "flat"),
    ("BRD-002", "Tostitos",             "MFR-001", ["CAT-001"], "Mainstream", "up"),
    ("BRD-003", "Lay's",                "MFR-001", ["CAT-002"], "Mainstream", "flat"),
    ("BRD-004", "Pringles",             "MFR-005", ["CAT-002"], "Mainstream", "down"),
    ("BRD-005", "Ruffles",              "MFR-001", ["CAT-002"], "Mainstream", "up"),
    ("BRD-006", "Private Label Chips",  "MFR-030", ["CAT-001", "CAT-002"], "Value", "strong_up"),
    # Cookies
    ("BRD-007", "Oreo",                 "MFR-004", ["CAT-003"], "Mainstream", "up"),
    ("BRD-008", "Chips Ahoy!",          "MFR-004", ["CAT-003"], "Mainstream", "flat"),
    # Cereal
    ("BRD-009", "Cheerios",             "MFR-006", ["CAT-004"], "Mainstream", "flat"),
    ("BRD-010", "Frosted Flakes",       "MFR-005", ["CAT-004"], "Mainstream", "down"),
    ("BRD-011", "Honey Bunches of Oats","MFR-007", ["CAT-004"], "Mainstream", "up"),
    # Regular CSDs
    ("BRD-012", "Coca-Cola",            "MFR-002", ["CAT-005"], "Mainstream", "up"),
    ("BRD-013", "Pepsi",                "MFR-001", ["CAT-005"], "Mainstream", "down"),
    ("BRD-014", "Dr Pepper",            "MFR-003", ["CAT-005"], "Mainstream", "strong_up"),
    # Diet CSDs
    ("BRD-015", "Diet Coke",            "MFR-002", ["CAT-006"], "Mainstream", "down"),
    ("BRD-016", "Coke Zero Sugar",      "MFR-002", ["CAT-006"], "Mainstream", "strong_up"),
    ("BRD-017", "Diet Pepsi",           "MFR-001", ["CAT-006"], "Mainstream", "down"),
    # Sparkling Water
    ("BRD-018", "LaCroix",              "MFR-009", ["CAT-007"], "Premium",    "down"),
    ("BRD-019", "Bubly",                "MFR-001", ["CAT-007"], "Mainstream", "up"),
    ("BRD-020", "Liquid Death",         "MFR-013", ["CAT-007"], "Premium",    "strong_up"),  # Pacesetter
    # Energy Drinks
    ("BRD-021", "Red Bull",             "MFR-012", ["CAT-008"], "Premium",    "flat"),
    ("BRD-022", "Monster",              "MFR-011", ["CAT-008"], "Mainstream", "flat"),
    ("BRD-023", "Celsius",              "MFR-010", ["CAT-008"], "Premium",    "strong_up"),  # Hero story
    # Skincare - Cleanser
    ("BRD-024", "CeraVe",               "MFR-014", ["CAT-009"], "Mainstream", "strong_up"),
    ("BRD-025", "Cetaphil",             "MFR-014", ["CAT-009"], "Mainstream", "flat"),
    # Skincare - Moisturizer
    ("BRD-026", "Olay",                 "MFR-015", ["CAT-010"], "Mainstream", "down"),
    ("BRD-027", "Neutrogena",           "MFR-008", ["CAT-010"], "Mainstream", "flat"),
    ("BRD-028", "The Ordinary",         "MFR-017", ["CAT-010"], "Premium",    "strong_up"),
    # Color Cosmetics
    ("BRD-029", "Maybelline",           "MFR-014", ["CAT-011"], "Mainstream", "flat"),
    ("BRD-030", "L'Oreal Paris",        "MFR-014", ["CAT-011"], "Mainstream", "up"),
    # Oral Care
    ("BRD-031", "Crest",                "MFR-015", ["CAT-012"], "Mainstream", "flat"),
    ("BRD-032", "Colgate",              "MFR-018", ["CAT-012"], "Mainstream", "up"),
    ("BRD-033", "Sensodyne",            "MFR-016", ["CAT-012"], "Premium",    "up"),
    # Body Wash
    ("BRD-034", "Dove",                 "MFR-016", ["CAT-013"], "Mainstream", "flat"),
    ("BRD-035", "Old Spice",            "MFR-015", ["CAT-013"], "Mainstream", "up"),
    # Smartphones
    ("BRD-036", "iPhone",               "MFR-019", ["CAT-014"], "Premium",    "up"),
    ("BRD-037", "Galaxy",               "MFR-020", ["CAT-014"], "Premium",    "flat"),
    # Headphones
    ("BRD-038", "AirPods",              "MFR-019", ["CAT-015"], "Premium",    "up"),
    ("BRD-039", "Sony WH",              "MFR-021", ["CAT-015"], "Premium",    "flat"),
    ("BRD-040", "Bose QC",              "MFR-023", ["CAT-015"], "Premium",    "down"),
    # Televisions
    ("BRD-041", "Samsung TV",           "MFR-020", ["CAT-016"], "Premium",    "flat"),
    ("BRD-042", "LG OLED",              "MFR-022", ["CAT-016"], "Premium",    "up"),
    ("BRD-043", "Sony Bravia",          "MFR-021", ["CAT-016"], "Premium",    "down"),
    # Toys - Building Sets
    ("BRD-044", "LEGO",                 "MFR-024", ["CAT-017"], "Premium",    "strong_up"),
    # Toys - Dolls
    ("BRD-045", "Barbie",               "MFR-025", ["CAT-018"], "Mainstream", "strong_up"),  # post-movie
    # Coffee Makers
    ("BRD-046", "Keurig K-Series",      "MFR-027", ["CAT-019"], "Mainstream", "flat"),
    ("BRD-047", "Ninja CFP",            "MFR-029", ["CAT-019"], "Mainstream", "strong_up"),
    # Vacuums
    ("BRD-048", "Roomba",               "MFR-028", ["CAT-020"], "Premium",    "down"),
    ("BRD-049", "Shark IQ",             "MFR-029", ["CAT-020"], "Premium",    "strong_up"),
]
BRAND_HEADERS = ["brand_id", "brand_name", "manufacturer_id", "premium_tier",
                 "primary_category_id", "share_trend"]

TREND_FACTOR = {
    "strong_up":   0.0055,   # per week
    "up":          0.0022,
    "flat":        0.0,
    "down":       -0.0022,
    "strong_down":-0.0050,
}

# -----------------------------------------------------------------------------
# SKU GENERATION (3-6 SKUs per brand x primary category)
# -----------------------------------------------------------------------------

PACK_FORMS = {
    "CAT-001": [("13oz Bag", "EA"), ("1oz Multipack 18ct", "EA"), ("Family Size 18oz", "EA")],
    "CAT-002": [("8oz Bag", "EA"), ("Party Size 14oz", "EA"), ("Single Serve 6pk", "EA")],
    "CAT-003": [("14oz Family Pack", "EA"), ("Single Serve 12ct", "EA"), ("Mini Bites Tub", "EA")],
    "CAT-004": [("18oz Box", "EA"), ("Family Size 24oz", "EA"), ("Single Serve Cup 6pk", "EA")],
    "CAT-005": [("12pk 12oz Can", "EA"), ("2L Bottle", "EA"), ("20oz Bottle", "EA"),
                ("8pk 12oz Can", "EA"), ("Mini 7.5oz 10pk", "EA")],
    "CAT-006": [("12pk 12oz Can", "EA"), ("2L Bottle", "EA"), ("20oz Bottle", "EA"),
                ("8pk 12oz Can", "EA")],
    "CAT-007": [("8pk 12oz Can", "EA"), ("12pk 12oz Can", "EA"), ("Single 16oz", "EA")],
    "CAT-008": [("4pk 12oz Can", "EA"), ("16oz Single", "EA"), ("12pk Can", "EA")],
    "CAT-009": [("12oz Bottle", "EA"), ("8oz Bottle", "EA"), ("16oz Refill", "EA")],
    "CAT-010": [("1.7oz Jar", "EA"), ("3.4oz Tube", "EA"), ("1oz Travel", "EA")],
    "CAT-011": [("1oz Bottle", "EA"), ("0.5oz Compact", "EA")],
    "CAT-012": [("4.6oz Tube", "EA"), ("6oz Twin Pack", "EA"), ("4.6oz 3pk", "EA")],
    "CAT-013": [("18oz Bottle", "EA"), ("32oz Pump", "EA"), ("Travel 3oz", "EA")],
    "CAT-014": [("128GB", "EA"), ("256GB", "EA"), ("512GB", "EA"), ("1TB", "EA")],
    "CAT-015": [("Gen 2 White", "EA"), ("Gen 2 Black", "EA"), ("Pro Model", "EA")],
    "CAT-016": [('55"', "EA"), ('65"', "EA"), ('75"', "EA"), ('85"', "EA")],
    "CAT-017": [("Starter Set", "EA"), ("Classic Brick Box", "EA"), ("Large Build Set", "EA")],
    "CAT-018": [("Standard Doll", "EA"), ("Dreamhouse Doll", "EA"), ("Movie Edition", "EA")],
    "CAT-019": [("K-Mini", "EA"), ("K-Classic", "EA"), ("K-Elite", "EA")],
    "CAT-020": [("Standard Model", "EA"), ("Pro Self-Empty", "EA"), ("Premium Mapping", "EA")],
}

BASE_PRICE_BY_CAT = {
    "CAT-001": 4.49,  "CAT-002": 4.99,  "CAT-003": 4.79,  "CAT-004": 5.49,
    "CAT-005": 7.99,  "CAT-006": 7.99,  "CAT-007": 8.49,  "CAT-008": 9.99,
    "CAT-009": 14.99, "CAT-010": 24.99, "CAT-011": 18.99,
    "CAT-012": 4.99,  "CAT-013": 7.99,
    "CAT-014": 899.00,"CAT-015": 199.00,"CAT-016": 799.00,
    "CAT-017": 49.99, "CAT-018": 24.99,
    "CAT-019": 119.00,"CAT-020": 399.00,
}

PREMIUM_PRICE_MULT = {"Value": 0.68, "Mainstream": 1.0, "Premium": 1.22}


def build_brands_and_skus():
    brand_rows, sku_rows = [], []
    sku_counter = 1
    for bid, bname, mid, cat_ids, tier, trend in BRANDS_RAW:
        primary_cat = cat_ids[0]
        brand_rows.append({
            "brand_id": bid, "brand_name": bname,
            "manufacturer_id": mid, "premium_tier": tier,
            "primary_category_id": primary_cat,
            "share_trend": trend,
        })
        for cat_id in cat_ids:
            packs = PACK_FORMS.get(cat_id, [("Standard", "EA")])
            base_price = BASE_PRICE_BY_CAT[cat_id] * PREMIUM_PRICE_MULT[tier]
            for pack_desc, uom in packs:
                if bid == "BRD-020":
                    launch = date(2024, 5, 4)
                elif bid == "BRD-016":
                    launch = date(2023, 3, 4)
                elif bid == "BRD-047":
                    launch = date(2023, 8, 5)
                else:
                    launch = date(2021, 1, 2)
                sku_rows.append({
                    "sku_id":          f"SKU-{sku_counter:04d}",
                    "sku_description": f"{bname} {pack_desc}",
                    "brand_id":        bid,
                    "category_id":     cat_id,
                    "pack_size":       pack_desc,
                    "unit_of_measure": uom,
                    "list_price":      round(base_price * random.uniform(0.95, 1.06), 2),
                    "launch_date":     launch.isoformat(),
                })
                sku_counter += 1
    return brand_rows, sku_rows


# -----------------------------------------------------------------------------
# DISTRIBUTION - which retailers each SKU sells in
# -----------------------------------------------------------------------------

CHANNEL_FIT = {
    "CPG-Food":      ["Mass", "Grocery", "Club", "eCommerce", "Drug"],
    "CPG-Beverage":  ["Mass", "Grocery", "Club", "eCommerce", "Drug"],
    "CPG-Beauty":    ["Mass", "Grocery", "Drug", "Beauty Specialty", "eCommerce"],
    "CPG-HBA":       ["Mass", "Grocery", "Drug", "eCommerce"],
    "GM-Electronics":["Mass", "Electronics", "Club", "eCommerce"],
    "GM-Toys":       ["Mass", "Club", "eCommerce"],
    "GM-Home":       ["Mass", "Club", "Electronics", "Home Improvement", "eCommerce"],
}

def pick_retailers_for_sku(department: str, brand_tier: str) -> list[str]:
    valid_channels = set(CHANNEL_FIT.get(department, []))
    options = [r for r in RETAILERS if r[2] in valid_channels]
    if brand_tier == "Premium":
        for r in options:
            pass
    n = random.randint(5, min(9, len(options)))
    chosen = random.sample(options, n)
    return [c[0] for c in chosen]


# -----------------------------------------------------------------------------
# POS WEEKLY GENERATION
# -----------------------------------------------------------------------------

CATEGORY_LOOKUP = {c[0]: {"department": c[1], "category_name": c[2],
                          "sub_category": c[3], "total_mm": c[4]} for c in CATEGORIES}
RETAILER_LOOKUP = {r[0]: {"name": r[1], "channel": r[2], "stores": r[4],
                          "acv_share": r[5]} for r in RETAILERS}


def category_seasonality(category_id: str, week_idx: int) -> float:
    week_of_year = (START_WEEK + timedelta(weeks=week_idx)).isocalendar().week
    dept = CATEGORY_LOOKUP[category_id]["department"]
    cat_name = CATEGORY_LOOKUP[category_id]["category_name"]

    base = 1.0 + 0.05 * math.sin(2 * math.pi * week_of_year / 52)

    if cat_name == "Carbonated Beverages":
        base *= 1.18 if 22 <= week_of_year <= 35 else 1.0
    if cat_name == "Sparkling Water":
        base *= 1.15 if 18 <= week_of_year <= 38 else 1.0
    if cat_name == "Energy Drinks":
        base *= 1.08 if 14 <= week_of_year <= 32 else 1.0
    if cat_name == "Cereal":
        base *= 1.05 if week_of_year <= 14 else 1.0
    if cat_name == "Skincare":
        base *= 1.10 if week_of_year in range(46, 52) else 1.0
    if dept in ("GM-Electronics", "GM-Toys", "GM-Home"):
        base *= 1.45 if 45 <= week_of_year <= 51 else 1.0
        base *= 0.75 if 1 <= week_of_year <= 8 else 1.0
    if cat_name == "Building Sets":
        base *= 1.20 if 45 <= week_of_year <= 51 else 1.0

    return base


def brand_base_volume(brand_id: str, category_id: str) -> float:
    dept = CATEGORY_LOOKUP[category_id]["department"]

    big_cpg = {"BRD-001","BRD-003","BRD-007","BRD-009","BRD-012","BRD-013","BRD-015","BRD-021","BRD-022"}
    mid_cpg = {"BRD-002","BRD-004","BRD-005","BRD-008","BRD-010","BRD-011","BRD-014","BRD-019","BRD-024"}
    small_cpg = {"BRD-018","BRD-020","BRD-028","BRD-033"}

    if dept.startswith("CPG"):
        if brand_id in big_cpg:   return random.uniform(28000, 42000)
        if brand_id in mid_cpg:   return random.uniform(14000, 22000)
        if brand_id in small_cpg: return random.uniform(2500, 5500)
        return random.uniform(6000, 12000)
    if dept == "GM-Electronics":  return random.uniform(800, 1800)
    if dept == "GM-Toys":         return random.uniform(1500, 3000)
    if dept == "GM-Home":         return random.uniform(600, 1200)
    return 5000.0


def special_story_overrides(sku, week_idx, units_so_far):
    bid = sku["brand_id"]
    week = START_WEEK + timedelta(weeks=week_idx)

    if bid == "BRD-023":  # Celsius accelerating
        units_so_far *= 1.0 + 0.012 * week_idx

    if bid == "BRD-016" and week >= date(2024, 7, 1):  # Coke Zero late 2024 surge
        units_so_far *= 1.0 + 0.008 * (week_idx - 78)

    if bid == "BRD-020":  # Liquid Death launch May 2024
        if week < date(2024, 5, 4):
            return 0.0
        weeks_since_launch = (week - date(2024, 5, 4)).days // 7
        units_so_far = 800 + 180 * weeks_since_launch + random.uniform(-150, 300)

    if bid == "BRD-045" and date(2023, 7, 1) <= week <= date(2024, 6, 30):  # Barbie halo
        units_so_far *= 1.45

    if bid == "BRD-036" and week >= date(2024, 9, 14):  # iPhone 16 launch
        units_so_far *= 1.35

    return units_so_far


def split_to_retailers(total_units, sku_retailers, week_idx, sku):
    splits = {}
    week = START_WEEK + timedelta(weeks=week_idx)
    weights = {}
    for rid in sku_retailers:
        r = RETAILER_LOOKUP[rid]
        w = r["acv_share"]

        if sku["category_id"] in {"CAT-005", "CAT-006"} and r["name"] == "Walmart" \
                and week >= date(2024, 10, 1):
            w *= 0.78
        if sku["category_id"] in {"CAT-005", "CAT-006"} and r["name"] == "Amazon" \
                and week >= date(2024, 10, 1):
            w *= 1.35
        if sku["category_id"] in {"CAT-009", "CAT-010", "CAT-011"} \
                and r["channel"] == "Beauty Specialty":
            w *= 1.6
        if sku["brand_id"] == "BRD-024" and r["channel"] in {"Mass", "Drug"}:
            w *= 1.3
        weights[rid] = max(0.01, w)

    total_w = sum(weights.values()) or 1.0
    for rid, w in weights.items():
        share = w / total_w
        splits[rid] = max(0, total_units * share * random.uniform(0.88, 1.12))
    return splits


def gen_pos_weekly(skus, sku_retailers_map):
    rows = []
    promo_events = []
    promo_id_counter = 1

    for sku in skus:
        bid       = sku["brand_id"]
        cat_id    = sku["category_id"]
        list_price = float(sku["list_price"])
        retailers = sku_retailers_map[sku["sku_id"]]

        brand_trend = next(b["share_trend"] for b in BRANDS if b["brand_id"] == bid)
        trend_per_week = TREND_FACTOR[brand_trend]
        base_weekly_units = brand_base_volume(bid, cat_id)

        promo_freq = {"Premium": 0.12, "Mainstream": 0.18, "Value": 0.25}
        ptier = next(b["premium_tier"] for b in BRANDS if b["brand_id"] == bid)
        p_per_week = promo_freq[ptier]

        for w_idx, week in enumerate(WEEKS):
            units = base_weekly_units \
                  * (1 + trend_per_week * w_idx) \
                  * category_seasonality(cat_id, w_idx) \
                  * random.uniform(0.85, 1.15)

            units = special_story_overrides(sku, w_idx, units)
            if units <= 0:
                continue

            on_promo = random.random() < p_per_week
            disc_pct = 0.0
            promo_type = "None"
            if on_promo:
                disc_pct = random.choice([0.10, 0.15, 0.20, 0.25, 0.30])
                promo_type = random.choices(
                    ["TPR", "Feature", "Display", "Feature & Display"],
                    weights=[0.45, 0.20, 0.15, 0.20]
                )[0]
                units *= 1 + (disc_pct * random.uniform(2.5, 4.2))

            splits = split_to_retailers(units, retailers, w_idx, sku)

            for rid, ru in splits.items():
                if ru < 1:
                    continue
                r_info = RETAILER_LOOKUP[rid]
                base_dist = 0.78 if bid in {"BRD-001","BRD-003","BRD-007","BRD-009",
                                            "BRD-012","BRD-013","BRD-021","BRD-022"} else 0.55
                if bid == "BRD-020":
                    weeks_in_market = max(0,(week - date(2024, 5, 4)).days // 7)
                    base_dist = min(0.35, 0.08 + 0.012 * weeks_in_market)
                if bid == "BRD-023":
                    base_dist = min(0.85, 0.50 + 0.0033 * w_idx)
                dist_noise = random.uniform(-0.06, 0.06)
                stores_selling = max(1, int(r_info["stores"] * max(0.05, base_dist + dist_noise)))
                acv_w_dist = round(min(99.5, (stores_selling / r_info["stores"]) * 100 *
                                       random.uniform(0.95, 1.08)), 1)

                price_mult = {"Walmart": 0.95, "Costco": 0.88, "Sam's Club": 0.89,
                              "Whole Foods": 1.08, "Sephora": 1.06, "Ulta Beauty": 1.04}.get(r_info["name"], 1.0)
                price = list_price * price_mult * (1 - disc_pct)
                base_price = list_price * price_mult
                dollars = round(ru * price, 2)
                base_units = ru / max(1.0, 1 + (disc_pct * random.uniform(2.5, 4.2))) if on_promo else ru
                base_dollars = round(base_units * base_price, 2)

                rows.append({
                    "week_ending":    week.isoformat(),
                    "sku_id":         sku["sku_id"],
                    "retailer_id":    rid,
                    "units":          int(round(ru)),
                    "dollars":        dollars,
                    "base_units":     int(round(base_units)),
                    "base_dollars":   base_dollars,
                    "incremental_units": int(round(ru - base_units)) if on_promo else 0,
                    "incremental_dollars": round(dollars - base_dollars, 2) if on_promo else 0.0,
                    "avg_price":      round(price, 2),
                    "base_price":     round(base_price, 2),
                    "stores_selling": stores_selling,
                    "total_stores":   r_info["stores"],
                    "acv_weighted_distribution_pct": acv_w_dist,
                    "on_promo":       on_promo,
                    "promo_type":     promo_type,
                    "discount_pct":   round(disc_pct * 100, 1),
                })

                if on_promo and random.random() < 0.4:
                    promo_events.append({
                        "promo_id":     f"PRM-{promo_id_counter:06d}",
                        "sku_id":       sku["sku_id"],
                        "retailer_id":  rid,
                        "start_date":   week.isoformat(),
                        "end_date":     (week + timedelta(days=6)).isoformat(),
                        "promo_type":   promo_type,
                        "discount_pct": round(disc_pct * 100, 1),
                        "incremental_units":   int(round(ru - base_units)),
                        "incremental_dollars": round(dollars - base_dollars, 2),
                        "lift_pct":     round(((ru / max(1, base_units)) - 1) * 100, 1),
                    })
                    promo_id_counter += 1

    return rows, promo_events


# -----------------------------------------------------------------------------
# PANEL (HOUSEHOLD) DATA - monthly grain
# -----------------------------------------------------------------------------

def gen_panel_data(brands):
    rows = []
    months = []
    cur = date(START_WEEK.year, START_WEEK.month, 1)
    while cur <= END_WEEK:
        months.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    for b in brands:
        bid = b["brand_id"]
        trend = TREND_FACTOR[b["share_trend"]] * 4
        tier = b["premium_tier"]
        if tier == "Mainstream":
            base_pen, base_trips, base_dpt = random.uniform(8.0, 24.0), random.uniform(3.2, 5.6), random.uniform(4.10, 8.20)
        elif tier == "Premium":
            base_pen, base_trips, base_dpt = random.uniform(2.5, 9.0),  random.uniform(2.4, 4.2), random.uniform(7.20, 14.50)
        else:
            base_pen, base_trips, base_dpt = random.uniform(11.0, 28.0), random.uniform(3.8, 6.2), random.uniform(2.80, 5.60)
        if bid == "BRD-020":
            base_pen, base_trips, base_dpt = 0.0, 0.0, 0.0
        if bid == "BRD-023":
            base_pen, base_trips, base_dpt = 6.5, 3.1, 9.20

        for m_idx, month in enumerate(months):
            pen = base_pen * (1 + trend * m_idx) * random.uniform(0.95, 1.05)
            if bid == "BRD-020" and month >= date(2024, 5, 1):
                weeks_in = (month - date(2024, 5, 1)).days // 7
                pen = min(7.5, 0.4 + 0.18 * weeks_in)
            if bid == "BRD-023":
                pen = min(18.0, base_pen + 0.42 * m_idx)
            if pen <= 0:
                continue
            trips = base_trips * (1 + trend * 0.5 * m_idx) * random.uniform(0.96, 1.04)
            dpt = base_dpt * random.uniform(0.97, 1.05)
            buyers_mm = round(pen * 1.32 + random.uniform(-0.3, 0.3), 2)
            rows.append({
                "period_month":          month.isoformat(),
                "brand_id":              bid,
                "hh_penetration_pct":    round(max(0, pen), 2),
                "buyers_mm":             max(0.0, buyers_mm),
                "trips_per_buyer":       round(max(0, trips), 2),
                "dollars_per_trip":      round(max(0, dpt), 2),
                "repeat_rate_pct":       round(random.uniform(42, 78), 1),
                "share_of_wallet_pct":   round(random.uniform(8, 38), 1),
            })
    return rows


# -----------------------------------------------------------------------------
# RUN
# -----------------------------------------------------------------------------

print(f"Generating CPG/GM Market Insights dataset -> {OUT_DIR.resolve()}")
print(f"Window: {START_WEEK.isoformat()} -> {END_WEEK.isoformat()} ({len(WEEKS)} weeks)")

write_csv("retailers.csv",
          [dict(zip(RETAILER_HEADERS, r)) for r in RETAILERS],
          RETAILER_HEADERS)
write_csv("categories.csv",
          [dict(zip(CATEGORY_HEADERS, c)) for c in CATEGORIES],
          CATEGORY_HEADERS)
write_csv("manufacturers.csv",
          [dict(zip(MANUFACTURER_HEADERS, m)) for m in MANUFACTURERS],
          MANUFACTURER_HEADERS)

BRANDS, SKUS = build_brands_and_skus()
write_csv("brands.csv", BRANDS, BRAND_HEADERS)
write_csv("products.csv", SKUS,
          ["sku_id", "sku_description", "brand_id", "category_id",
           "pack_size", "unit_of_measure", "list_price", "launch_date"])

SKU_RETAILERS = {}
for sku in SKUS:
    dept = CATEGORY_LOOKUP[sku["category_id"]]["department"]
    tier = next(b["premium_tier"] for b in BRANDS if b["brand_id"] == sku["brand_id"])
    SKU_RETAILERS[sku["sku_id"]] = pick_retailers_for_sku(dept, tier)

pos_rows, promo_rows = gen_pos_weekly(SKUS, SKU_RETAILERS)
write_csv("pos_weekly.csv", pos_rows,
          ["week_ending", "sku_id", "retailer_id", "units", "dollars",
           "base_units", "base_dollars", "incremental_units", "incremental_dollars",
           "avg_price", "base_price", "stores_selling", "total_stores",
           "acv_weighted_distribution_pct", "on_promo", "promo_type", "discount_pct"])
write_csv("promo_events.csv", promo_rows,
          ["promo_id", "sku_id", "retailer_id", "start_date", "end_date",
           "promo_type", "discount_pct", "incremental_units", "incremental_dollars", "lift_pct"])

panel_rows = gen_panel_data(BRANDS)
write_csv("panel_household.csv", panel_rows,
          ["period_month", "brand_id", "hh_penetration_pct", "buyers_mm",
           "trips_per_buyer", "dollars_per_trip", "repeat_rate_pct", "share_of_wallet_pct"])

print("\nDone. Built-in demo storylines:")
print("  - Celsius hyper-growth in Energy Drinks")
print("  - Coca-Cola gaining vs Pepsi (esp. Coke Zero in Diet)")
print("  - CeraVe surging in Skincare Cleanser")
print("  - Liquid Death: Pacesetter trajectory from May 2024")
print("  - Walmart soft in CSDs Q4 2024 (Amazon picks up)")
print("  - LEGO holiday spike; iPhone 16 launch lift Sept 2024")
print("  - Barbie movie halo on Mattel dolls 2023-H2 to 2024-H1")
