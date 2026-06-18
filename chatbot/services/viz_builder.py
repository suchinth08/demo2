"""
Visualization Builder — generates Vega-Lite specs from query results + intent.
Each function returns a JSON-serializable Vega-Lite specification.
"""
from typing import Any


def build_viz_spec(viz_type: str, data: list[dict], intent: dict) -> dict:
    """Route to the appropriate Vega-Lite spec builder."""
    builders = {
        "metric_card":       _metric_card,
        "line_chart":        _line_chart,
        "bar_chart":         _bar_chart,
        "horizontal_bar":    _horizontal_bar,
        "grouped_bar":       _grouped_bar,
        "pie":               _pie_chart,
        "heatmap":           _heatmap,
        "scatter":           _scatter_plot,
        "risk_matrix":       _risk_matrix,
        "radar_chart":       _radar_chart,
        "data_table":        _data_table,
        "table_with_rag":    _table_with_rag,
        "timeline":          _timeline,
    }
    builder = builders.get(viz_type, _bar_chart)
    return builder(data, intent)


def _metric_card(data: list[dict], intent: dict) -> dict:
    """Single KPI metric card with trend indicator."""
    metrics = intent.get("metrics", [])
    if not data or not metrics:
        return {"type": "metric_card", "values": {}}

    row = data[0] if data else {}
    cards = []
    for m in metrics:
        if m in row:
            cards.append({"metric": m, "value": row[m], "label": _humanize(m)})

    return {
        "type": "metric_card",
        "cards": cards,
        "data": data
    }


def _line_chart(data: list[dict], intent: dict) -> dict:
    """Time series line chart — detects time field automatically."""
    if not data:
        return _empty_spec("line")

    # Find time field (first field with 'month', 'quarter', 'year', 'date' in name)
    time_field = _find_time_field(data[0])
    metric_fields = [k for k in data[0].keys() if k != time_field and _is_numeric(data[0][k])]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 700, "height": 350,
        "data": {"values": _serialize(data)},
        "transform": [{"fold": metric_fields, "as": ["metric", "value"]}],
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {"field": time_field, "type": "temporal", "title": _humanize(time_field),
                  "axis": {"labelAngle": -30}},
            "y": {"field": "value", "type": "quantitative", "title": "Value"},
            "color": {"field": "metric", "type": "nominal",
                      "scale": {"scheme": "tableau10"}}
        },
        "config": {"view": {"stroke": None}}
    }
    return spec


def _bar_chart(data: list[dict], intent: dict) -> dict:
    """Vertical bar chart for categorical breakdowns."""
    if not data:
        return _empty_spec("bar")

    cat_field = _find_categorical_field(data[0])
    metrics = intent.get("metrics", [])
    val_field = next((m for m in metrics if m in data[0]), None) or _find_first_numeric(data[0])

    if not val_field:
        return _data_table(data, intent)

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 600, "height": 350,
        "data": {"values": _serialize(data)},
        "mark": {"type": "bar", "tooltip": True, "cornerRadiusEnd": 3},
        "encoding": {
            "x": {"field": cat_field, "type": "nominal", "sort": "-y",
                  "axis": {"labelAngle": -30}, "title": _humanize(cat_field)},
            "y": {"field": val_field, "type": "quantitative",
                  "title": _humanize(val_field)},
            "color": {
                "condition": {
                    "test": f"datum['{val_field}'] > 90",
                    "value": "#2ecc71"
                },
                "value": "#e74c3c"
            },
            "tooltip": [{"field": cat_field, "type": "nominal"},
                        {"field": val_field, "type": "quantitative", "format": ".1f"}]
        }
    }


def _horizontal_bar(data: list[dict], intent: dict) -> dict:
    """Horizontal bar chart for rankings."""
    if not data:
        return _empty_spec("bar")

    cat_field = _find_categorical_field(data[0])
    metrics = intent.get("metrics", [])
    val_field = next((m for m in metrics if m in data[0]), None) or _find_first_numeric(data[0])

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 550, "height": max(200, len(data) * 30),
        "data": {"values": _serialize(data)},
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "y": {"field": cat_field, "type": "nominal", "sort": "-x",
                  "title": _humanize(cat_field)},
            "x": {"field": val_field, "type": "quantitative",
                  "title": _humanize(val_field)},
            "color": {"field": val_field, "type": "quantitative",
                      "scale": {"scheme": "reds"}},
            "tooltip": [{"field": cat_field}, {"field": val_field, "format": ".2f"}]
        }
    }


def _grouped_bar(data: list[dict], intent: dict) -> dict:
    """Grouped bar chart for comparisons."""
    return _bar_chart(data, intent)  # simplified


def _pie_chart(data: list[dict], intent: dict) -> dict:
    """Donut/pie chart for composition."""
    if not data:
        return _empty_spec("arc")

    cat_field = _find_categorical_field(data[0])
    val_field = _find_first_numeric(data[0])

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 400, "height": 350,
        "data": {"values": _serialize(data)},
        "mark": {"type": "arc", "innerRadius": 80, "tooltip": True},
        "encoding": {
            "theta": {"field": val_field, "type": "quantitative"},
            "color": {"field": cat_field, "type": "nominal",
                      "scale": {"scheme": "tableau10"}},
            "tooltip": [{"field": cat_field}, {"field": val_field}]
        }
    }


def _heatmap(data: list[dict], intent: dict) -> dict:
    """2D heatmap for matrix views."""
    if not data:
        return _empty_spec("rect")

    keys = list(data[0].keys())
    x_field = keys[0] if len(keys) > 0 else "x"
    y_field = keys[1] if len(keys) > 1 else "y"
    val_field = _find_first_numeric(data[0])

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 500, "height": 400,
        "data": {"values": _serialize(data)},
        "mark": {"type": "rect", "tooltip": True},
        "encoding": {
            "x": {"field": x_field, "type": "ordinal", "title": _humanize(x_field)},
            "y": {"field": y_field, "type": "ordinal", "title": _humanize(y_field)},
            "color": {"field": val_field, "type": "quantitative",
                      "scale": {"scheme": "reds", "reverse": False}},
            "tooltip": [{"field": x_field}, {"field": y_field},
                        {"field": val_field, "format": ".1f"}]
        }
    }


def _risk_matrix(data: list[dict], intent: dict) -> dict:
    """ICH Q9 Risk Matrix: Severity × Occurrence, bubble size = count."""
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 450, "height": 400,
        "title": "Risk Matrix (Severity × Occurrence × Count)",
        "data": {"values": _serialize(data)},
        "layer": [
            {
                "mark": {"type": "rect", "opacity": 0.15},
                "encoding": {
                    "x": {"field": "occurrence", "type": "ordinal"},
                    "y": {"field": "severity", "type": "ordinal", "sort": "descending"},
                    "color": {
                        "condition": [
                            {"test": "datum.severity * datum.occurrence >= 16", "value": "#e74c3c"},
                            {"test": "datum.severity * datum.occurrence >= 8",  "value": "#f39c12"}
                        ],
                        "value": "#2ecc71"
                    }
                }
            },
            {
                "mark": {"type": "circle", "tooltip": True},
                "encoding": {
                    "x": {"field": "occurrence", "type": "ordinal", "title": "Occurrence (1-10)"},
                    "y": {"field": "severity", "type": "ordinal", "sort": "descending",
                          "title": "Severity (1-10)"},
                    "size": {"field": "risk_count", "type": "quantitative",
                             "scale": {"range": [100, 2000]}},
                    "color": {"field": "avg_rpn", "type": "quantitative",
                              "scale": {"scheme": "reds"}},
                    "tooltip": [{"field": "severity"}, {"field": "occurrence"},
                                {"field": "risk_count"}, {"field": "avg_rpn", "format": ".0f"}]
                }
            }
        ],
        "config": {"view": {"stroke": None}}
    }


def _scatter_plot(data: list[dict], intent: dict) -> dict:
    """Scatter plot for correlations."""
    if not data:
        return _empty_spec("point")
    keys = [k for k in data[0].keys() if _is_numeric(data[0][k])]
    x_field = keys[0] if len(keys) > 0 else "x"
    y_field = keys[1] if len(keys) > 1 else "y"
    cat_field = _find_categorical_field(data[0])

    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 550, "height": 400,
        "data": {"values": _serialize(data)},
        "mark": {"type": "point", "filled": True, "size": 100, "tooltip": True},
        "encoding": {
            "x": {"field": x_field, "type": "quantitative", "title": _humanize(x_field)},
            "y": {"field": y_field, "type": "quantitative", "title": _humanize(y_field)},
            "color": {"field": cat_field, "type": "nominal"},
            "tooltip": [{"field": cat_field}, {"field": x_field, "format": ".2f"},
                        {"field": y_field, "format": ".2f"}]
        }
    }


def _radar_chart(data: list[dict], intent: dict) -> dict:
    """Compliance health radar — returns structured data for frontend rendering."""
    return {
        "type": "radar_chart",
        "data": _serialize(data),
        "note": "Render with Chart.js Radar or D3 radar component"
    }


def _data_table(data: list[dict], intent: dict) -> dict:
    """Simple data table spec."""
    if not data:
        return {"type": "table", "columns": [], "rows": []}
    columns = [{"field": k, "header": _humanize(k)} for k in data[0].keys()]
    return {
        "type": "table",
        "columns": columns,
        "rows": _serialize(data),
        "sortable": True,
        "searchable": True
    }


def _table_with_rag(data: list[dict], intent: dict) -> dict:
    """Data table with Red/Amber/Green row coloring based on compliance thresholds."""
    spec = _data_table(data, intent)
    spec["rag_enabled"] = True
    spec["rag_field"] = _find_rag_field(data[0] if data else {})
    spec["rag_thresholds"] = {"red": 0.9, "amber": 0.95, "green": 0.98}
    return spec


def _timeline(data: list[dict], intent: dict) -> dict:
    """Timeline for regulatory inspection history."""
    return {
        "type": "timeline",
        "data": _serialize(data),
        "note": "Render with D3 timeline or react-vis timeline component"
    }


# ── Utilities ──────────────────────────────────────────────────

def _find_time_field(row: dict) -> str:
    time_keywords = ["month", "quarter", "year", "date", "week", "time", "period"]
    for k in row.keys():
        if any(t in k.lower() for t in time_keywords):
            return k
    return list(row.keys())[0]


def _find_categorical_field(row: dict) -> str:
    skip = ["count", "total", "rate", "pct", "score", "days", "avg", "sum", "num"]
    for k in row.keys():
        if not any(s in k.lower() for s in skip):
            return k
    return list(row.keys())[0]


def _find_first_numeric(row: dict) -> str | None:
    for k, v in row.items():
        if _is_numeric(v):
            return k
    return None


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _humanize(field: str) -> str:
    return field.replace("_", " ").replace("pct", "%").title()


def _serialize(data: list[dict]) -> list[dict]:
    """Convert date objects to ISO strings for JSON serialization."""
    import json
    from datetime import date, datetime
    result = []
    for row in data:
        clean = {}
        for k, v in row.items():
            if isinstance(v, (date, datetime)):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        result.append(clean)
    return result


def _find_rag_field(row: dict) -> str | None:
    rag_candidates = ["compliance_rate_pct", "on_time_closure_rate_pct",
                      "rejection_rate_pct", "repeat_rate_pct"]
    for c in rag_candidates:
        if c in row:
            return c
    return _find_first_numeric(row)


def _empty_spec(mark_type: str) -> dict:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": mark_type,
        "data": {"values": []},
        "encoding": {},
        "title": "No data available"
    }
