"""
Alerting Agent — proactive compliance monitor (Level 1-2 autonomy).

Runs on demand or on a schedule. Scans all compliance domains against
the Policy Registry, surfaces breaches grouped by severity, and generates
a prioritised remediation brief ready for the dashboard or email digest.

Autonomy Level:
  Level 1 — Detect + notify (no writes, human decides action)
  Level 2 — Detect + draft CAPA text (human approves before commit)
"""

from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

from chatbot.services.query_engine import get_conn
from chatbot.services.policy_registry import (
    evaluate_records,
    get_inspection_readiness_score,
    PolicyBreach,
    PolicyEvaluationResult,
)

load_dotenv(Path(__file__).parent.parent.parent / ".env")
_groq = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Domain scan queries ────────────────────────────────────────────
# Each returns the minimum fields needed for policy evaluation.

_SCAN_QUERIES: dict[str, tuple[str, str]] = {
    # domain: (sql, record_id_field)
    "capa": (
        """SELECT capa_id, severity, status, initiation_date, target_close_date,
                  actual_close_date, effectiveness_check_req, effectiveness_check_result,
                  reopen_count, source_type, site_id, department_id
           FROM capa_records
           WHERE status != 'Closed'""",
        "capa_id",
    ),
    "deviation": (
        """SELECT deviation_id, severity, status, detection_date,
                  investigation_required, investigation_close_dt,
                  batch_disposition_impact, capa_id, site_id
           FROM deviation_records
           WHERE status != 'Closed'""",
        "deviation_id",
    ),
    "training": (
        """SELECT t.training_record_id, t.employee_id, t.doc_id,
                  t.training_type, t.status, t.due_date, t.assigned_date,
                  e.gmp_role, e.site_id
           FROM training_records t
           JOIN employees e ON t.employee_id = e.employee_id
           WHERE t.status = 'Overdue'""",
        "training_record_id",
    ),
    "audit": (
        """SELECT finding_id, classification, process_area,
                  is_repeat_finding, capa_id, response_status,
                  response_date, close_date
           FROM audit_findings
           WHERE response_status IN ('Open', 'Submitted')""",
        "finding_id",
    ),
    "supplier": (
        """SELECT s.supplier_id, s.supplier_name, s.supplier_type,
                  s.qualification_status, s.requalification_due_dt,
                  ROUND(100.0 * SUM(CASE WHEN i.inspection_result='Fail' THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0), 2) AS rejection_rate_pct
           FROM suppliers s
           LEFT JOIN supplier_inspections i ON s.supplier_id = i.supplier_id
           WHERE s.qualification_status = 'Approved'
           GROUP BY s.supplier_id, s.supplier_name, s.supplier_type,
                    s.qualification_status, s.requalification_due_dt""",
        "supplier_id",
    ),
    "risk": (
        """SELECT risk_id, risk_title, risk_category, status,
                  residual_rpn, risk_acceptance_status,
                  linked_capa_id, last_review_date, next_review_date
           FROM risk_register
           WHERE status = 'Active'""",
        "risk_id",
    ),
    "document": (
        """SELECT doc_id, doc_title, doc_type, gxp_classification,
                  status, next_review_date, last_review_date, site_id
           FROM documents
           WHERE status = 'Effective'""",
        "doc_id",
    ),
    "regulatory": (
        """SELECT rc.commitment_id, rc.status, rc.target_response_date,
                  rc.actual_response_date, ri.inspecting_authority, ri.site_id
           FROM regulatory_commitments rc
           JOIN regulatory_inspections ri ON rc.inspection_id = ri.inspection_id
           WHERE rc.status IN ('Open', 'Overdue')""",
        "commitment_id",
    ),
}


# ── Main scan function ─────────────────────────────────────────────

def run_compliance_scan(
    domains: Optional[list[str]] = None,
    site_id: Optional[str] = None,
) -> dict:
    """
    Scan all (or specified) domains against the Policy Registry.
    Returns a full AlertReport dict ready to be served or rendered.
    """
    domains = domains or list(_SCAN_QUERIES.keys())
    conn = get_conn()

    domain_results: dict[str, PolicyEvaluationResult] = {}
    all_breaches: list[PolicyBreach] = []

    for domain in domains:
        if domain not in _SCAN_QUERIES:
            continue
        sql, id_field = _SCAN_QUERIES[domain]

        # Optionally filter by site
        if site_id:
            if "WHERE" in sql:
                sql += f" AND site_id = '{site_id}'"
            else:
                sql += f" WHERE site_id = '{site_id}'"

        try:
            records = conn.execute(sql).fetchdf().to_dict(orient="records")
        except Exception as e:
            records = []

        result = evaluate_records(records, domain, record_id_field=id_field)
        domain_results[domain] = result
        all_breaches.extend(result.breaches)

    # Build inspection readiness score
    domain_scores = {d: r.compliance_score for d, r in domain_results.items()}
    readiness = get_inspection_readiness_score(domain_scores)

    # Group breaches by severity
    critical_breaches = [b for b in all_breaches if b.severity == "critical"]
    major_breaches    = [b for b in all_breaches if b.severity == "major"]
    minor_breaches    = [b for b in all_breaches if b.severity == "minor"]

    report = {
        "scan_timestamp":       datetime.utcnow().isoformat(),
        "site_filter":          site_id or "All Sites",
        "domains_scanned":      domains,
        "total_records_scanned":sum(r.total_records for r in domain_results.values()),
        "total_breaches":       len(all_breaches),
        "critical_count":       len(critical_breaches),
        "major_count":          len(major_breaches),
        "minor_count":          len(minor_breaches),
        "inspection_readiness": readiness,
        "domain_summaries": {
            d: {
                "compliance_score": r.compliance_score,
                "rag_status":       r.to_dict()["rag_status"],
                "total_records":    r.total_records,
                "breach_count":     r.breach_count,
                "critical_count":   r.critical_count,
                "rules_applied":    r.rules_applied,
            }
            for d, r in domain_results.items()
        },
        "critical_breaches": [b.to_dict() for b in critical_breaches],
        "major_breaches":    [b.to_dict() for b in major_breaches[:20]],  # cap for payload
        "minor_breaches":    [b.to_dict() for b in minor_breaches[:10]],
    }

    # Generate AI executive brief
    report["executive_brief"] = _generate_brief(report)

    return report


def _generate_brief(report: dict) -> str:
    """Generate a concise executive brief from the scan report using Groq."""
    system = (
        "You are a Pharma Compliance Director. Write a concise executive compliance brief "
        "based on a policy scan result. Use professional pharma regulatory language. "
        "Structure: 1) Overall status (1 sentence), "
        "2) Critical issues requiring immediate action (bullet list), "
        "3) Top 3 recommended actions with owner and timeline. "
        "Keep total length under 200 words."
    )

    summary = {
        "overall_readiness_score": report["inspection_readiness"]["overall_score"],
        "rag_status":              report["inspection_readiness"]["rag_status"],
        "total_breaches":          report["total_breaches"],
        "critical_count":          report["critical_count"],
        "major_count":             report["major_count"],
        "domain_summaries":        report["domain_summaries"],
        "sample_critical":         report["critical_breaches"][:3],
    }

    try:
        resp = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": f"Compliance scan results:\n{str(summary)[:2000]}"},
            ],
            max_tokens=400,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        score = report["inspection_readiness"]["overall_score"]
        return (
            f"Compliance scan complete. Overall readiness score: {score}/100. "
            f"{report['critical_count']} critical and {report['major_count']} major "
            f"policy breaches detected across {len(report['domains_scanned'])} domains. "
            "Review critical breaches immediately and assign remediation owners."
        )


def draft_capa_for_breach(breach: dict) -> dict:
    """
    Level-2 autonomy: Draft a CAPA record for a critical/major breach.
    Returns a draft dict — NOT written to DB until human approves.
    """
    system = (
        "You are a Pharma QA specialist. Draft a CAPA record for a compliance policy breach. "
        "Return ONLY valid JSON with these keys: "
        "description, root_cause_category, root_cause_detail, "
        "suggested_actions (list of 3 strings), suggested_owner_role, "
        "suggested_target_days (integer), severity."
    )
    prompt = (
        f"Policy breach details:\n"
        f"Rule: {breach.get('rule_title')}\n"
        f"Regulatory ref: {breach.get('regulatory_ref')}\n"
        f"Breach: {breach.get('breach_message')}\n"
        f"Remediation guidance: {breach.get('remediation')}\n\n"
        "Draft the CAPA record JSON."
    )
    try:
        resp = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=512,
            temperature=0.1,
        )
        import re, json
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        draft = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
        draft["source_breach"] = breach
        draft["draft_status"] = "pending_approval"
        return draft
    except Exception as e:
        return {
            "error": str(e),
            "description": breach.get("breach_message", ""),
            "remediation": breach.get("remediation", ""),
            "draft_status": "pending_approval",
            "source_breach": breach,
        }


def evaluate_record_live(record: dict, domain: str, record_id: str) -> dict:
    """
    Evaluate a single record inline (used by /chat for policy-aware responses).
    Returns breaches + narrative suitable for embedding in chat response.
    """
    from chatbot.services.policy_registry import evaluate_single
    breaches = evaluate_single(record, domain, record_id)
    if not breaches:
        return {"compliant": True, "breaches": [], "policy_narrative": "No policy violations detected."}

    critical = [b for b in breaches if b.severity == "critical"]
    major    = [b for b in breaches if b.severity == "major"]

    narrative_parts = []
    if critical:
        narrative_parts.append(
            f"**{len(critical)} CRITICAL policy violation(s):** " +
            "; ".join(b.breach_message for b in critical[:2])
        )
    if major:
        narrative_parts.append(
            f"**{len(major)} major policy gap(s):** " +
            "; ".join(b.breach_message for b in major[:2])
        )

    return {
        "compliant": False,
        "breaches": [b.to_dict() for b in breaches],
        "critical_count": len(critical),
        "major_count": len(major),
        "policy_narrative": " | ".join(narrative_parts),
    }
