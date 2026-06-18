"""
Policy Registry — versioned rule engine grounded in pharma regulatory requirements.

Evaluates live compliance data against three rule types:
  1. Regulatory rules  — FDA 21 CFR, ICH Q9/Q10, EU GMP
  2. Internal policy   — Company SOPs, quality thresholds
  3. KPI thresholds    — RAG (Red/Amber/Green) bands per metric

Every rule carries: ID, description, regulatory citation, severity,
evaluation logic, remediation guidance, and version history.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable
import json


# ── Data structures ────────────────────────────────────────────────

@dataclass
class PolicyRule:
    rule_id:        str
    title:          str
    description:    str
    domain:         str           # capa | deviation | training | audit | supplier | risk | batch | regulatory
    rule_type:      str           # regulatory | internal | kpi_threshold
    severity:       str           # critical | major | minor | info
    regulatory_ref: str           # e.g. "21 CFR 211.192"
    internal_ref:   str           # e.g. "SOP-QA-003 §4.2"
    evaluate:       Callable      # fn(data_row) -> bool  — True means BREACH
    breach_message: str           # template, supports {field} interpolation
    remediation:    str           # plain-English guidance
    effective_date: date = field(default_factory=date.today)
    version:        str = "1.0"


@dataclass
class PolicyBreach:
    rule_id:        str
    rule_title:     str
    severity:       str
    regulatory_ref: str
    internal_ref:   str
    domain:         str
    record_id:      str
    breach_message: str
    remediation:    str
    evaluated_at:   datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "rule_id":        self.rule_id,
            "rule_title":     self.rule_title,
            "severity":       self.severity,
            "regulatory_ref": self.regulatory_ref,
            "internal_ref":   self.internal_ref,
            "domain":         self.domain,
            "record_id":      self.record_id,
            "breach_message": self.breach_message,
            "remediation":    self.remediation,
            "evaluated_at":   self.evaluated_at.isoformat(),
        }


@dataclass
class PolicyEvaluationResult:
    total_records:   int
    total_evaluated: int
    breach_count:    int
    critical_count:  int
    major_count:     int
    breaches:        list[PolicyBreach]
    compliance_score: float        # 0–100
    rules_applied:   list[str]
    domain:          str
    evaluated_at:    datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "total_records":    self.total_records,
            "total_evaluated":  self.total_evaluated,
            "breach_count":     self.breach_count,
            "critical_count":   self.critical_count,
            "major_count":      self.major_count,
            "compliance_score": round(self.compliance_score, 1),
            "rules_applied":    self.rules_applied,
            "domain":           self.domain,
            "evaluated_at":     self.evaluated_at.isoformat(),
            "breaches":         [b.to_dict() for b in self.breaches],
            "rag_status":       "green" if self.compliance_score >= 95
                                else "amber" if self.compliance_score >= 80
                                else "red",
        }


# ── Helper ─────────────────────────────────────────────────────────

def _days_since(date_str: Any) -> int | None:
    """Return days elapsed since a date string. None if unparseable."""
    if not date_str:
        return None
    try:
        if isinstance(date_str, (date, datetime)):
            d = date_str if isinstance(date_str, date) else date_str.date()
        else:
            d = date.fromisoformat(str(date_str)[:10])
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


def _days_until(date_str: Any) -> int | None:
    days = _days_since(date_str)
    return -days if days is not None else None


# ── RULE DEFINITIONS ───────────────────────────────────────────────
# Each rule's `evaluate(row)` returns True when a BREACH is detected.

RULES: list[PolicyRule] = [

    # ════════════════════════════════════════════════════════════════
    # CAPA RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-CAPA-001",
        title="Critical CAPA — 30-Day Closure Limit",
        description="Critical CAPAs must be closed within 30 calendar days of initiation per ICH Q10.",
        domain="capa",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="ICH Q10 §3.2.3",
        internal_ref="SOP-QA-002 §5.1",
        evaluate=lambda r: (
            r.get("severity") == "Critical"
            and r.get("actual_close_date") is None
            and (_days_since(r.get("initiation_date")) or 0) > 30
        ),
        breach_message="Critical CAPA {capa_id} has been open for {age_days} days — exceeds 30-day ICH Q10 limit.",
        remediation="Escalate to site QA Director immediately. Assign dedicated resource. Daily status update required.",
    ),

    PolicyRule(
        rule_id="POL-CAPA-002",
        title="Major CAPA — 60-Day Closure Limit",
        description="Major CAPAs must be closed within 60 calendar days of initiation.",
        domain="capa",
        rule_type="internal",
        severity="major",
        regulatory_ref="ICH Q10 §3.2",
        internal_ref="SOP-QA-002 §5.2",
        evaluate=lambda r: (
            r.get("severity") == "Major"
            and r.get("actual_close_date") is None
            and (_days_since(r.get("initiation_date")) or 0) > 60
        ),
        breach_message="Major CAPA {capa_id} has been open for {age_days} days — exceeds 60-day limit.",
        remediation="Review action item status. Escalate to QA Manager if blocked. Update target close date with justification.",
    ),

    PolicyRule(
        rule_id="POL-CAPA-003",
        title="Minor CAPA — 90-Day Closure Limit",
        description="Minor CAPAs must be closed within 90 calendar days.",
        domain="capa",
        rule_type="internal",
        severity="minor",
        regulatory_ref="ICH Q10 §3.2",
        internal_ref="SOP-QA-002 §5.3",
        evaluate=lambda r: (
            r.get("severity") == "Minor"
            and r.get("actual_close_date") is None
            and (_days_since(r.get("initiation_date")) or 0) > 90
        ),
        breach_message="Minor CAPA {capa_id} has been open for {age_days} days — exceeds 90-day limit.",
        remediation="Review and close if actions are complete. Document any barriers preventing closure.",
    ),

    PolicyRule(
        rule_id="POL-CAPA-004",
        title="Critical CAPA — Effectiveness Check Required",
        description="All Critical CAPAs must have an effectiveness check scheduled within 90 days of closure.",
        domain="capa",
        rule_type="regulatory",
        severity="major",
        regulatory_ref="21 CFR 820.100(a)(6), ICH Q10 §3.2.4",
        internal_ref="SOP-QA-002 §6.0",
        evaluate=lambda r: (
            r.get("severity") == "Critical"
            and r.get("actual_close_date") is not None
            and r.get("effectiveness_check_req") is True
            and r.get("effectiveness_check_result") is None
            and (_days_since(r.get("actual_close_date")) or 0) > 90
        ),
        breach_message="Critical CAPA {capa_id} closed {age_days} days ago — effectiveness check overdue.",
        remediation="Schedule effectiveness check immediately. Assign QA reviewer. Document results in the CAPA record.",
    ),

    PolicyRule(
        rule_id="POL-CAPA-005",
        title="CAPA Recurrence — Systemic Failure Signal",
        description="CAPAs that have been reopened more than once indicate systemic root cause failure.",
        domain="capa",
        rule_type="internal",
        severity="major",
        regulatory_ref="ICH Q10 §3.2.3",
        internal_ref="SOP-QA-002 §7.0",
        evaluate=lambda r: (r.get("reopen_count") or 0) >= 2,
        breach_message="CAPA {capa_id} has been reopened {reopen_count} times — systemic root cause failure suspected.",
        remediation="Perform enhanced root cause analysis (Ishikawa/5-Why). Engage cross-functional team. Consider risk elevation.",
    ),

    # ════════════════════════════════════════════════════════════════
    # DEVIATION RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-DEV-001",
        title="Critical Deviation — Investigation Before Release",
        description="Batches with Critical deviations must not be released without completed investigation (21 CFR 211.192).",
        domain="deviation",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="21 CFR 211.192",
        internal_ref="SOP-QA-003 §4.1",
        evaluate=lambda r: (
            r.get("severity") == "Critical"
            and r.get("batch_disposition_impact") == "Released"
            and r.get("investigation_close_dt") is None
        ),
        breach_message="Critical deviation {deviation_id} — batch released without completed investigation. 21 CFR 211.192 potential violation.",
        remediation="IMMEDIATE: Place batch on hold if not yet distributed. Complete investigation. Notify QA Director and Regulatory Affairs.",
    ),

    PolicyRule(
        rule_id="POL-DEV-002",
        title="Deviation Investigation — 30-Day Completion Limit",
        description="All deviations requiring investigation must be closed within 30 days of detection.",
        domain="deviation",
        rule_type="internal",
        severity="major",
        regulatory_ref="21 CFR 211.192",
        internal_ref="SOP-QA-003 §4.3",
        evaluate=lambda r: (
            r.get("investigation_required") is True
            and r.get("investigation_close_dt") is None
            and (_days_since(r.get("detection_date")) or 0) > 30
        ),
        breach_message="Deviation {deviation_id} investigation has been open for {age_days} days — exceeds 30-day limit.",
        remediation="Assign dedicated investigator. Escalate to department head. Provide interim batch disposition assessment.",
    ),

    PolicyRule(
        rule_id="POL-DEV-003",
        title="Critical Deviation — Mandatory CAPA",
        description="All Critical deviations must have an associated CAPA opened within 5 business days.",
        domain="deviation",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="21 CFR 820.100, ICH Q10 §3.2",
        internal_ref="SOP-QA-003 §5.0",
        evaluate=lambda r: (
            r.get("severity") == "Critical"
            and not r.get("capa_id")
            and (_days_since(r.get("detection_date")) or 0) > 5
        ),
        breach_message="Critical deviation {deviation_id} detected {age_days} days ago — no CAPA initiated.",
        remediation="Open CAPA immediately. Assign to area QA lead. Notify site QA Director.",
    ),

    # ════════════════════════════════════════════════════════════════
    # TRAINING RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-TRN-001",
        title="GMP Training Compliance Minimum — 98%",
        description="GMP-role employees must maintain >= 98% training completion rate at all times.",
        domain="training",
        rule_type="internal",
        severity="major",
        regulatory_ref="21 CFR 211.68",
        internal_ref="QP-TRN-001 §3.1",
        evaluate=lambda r: (
            r.get("gmp_role") == "GMP"
            and r.get("status") == "Overdue"
        ),
        breach_message="GMP employee {employee_id} has overdue training assignment {doc_id}. Compliance rate at risk.",
        remediation="Notify employee and manager. Set 72-hour completion deadline. If safety-critical SOP, restrict access until trained.",
    ),

    PolicyRule(
        rule_id="POL-TRN-002",
        title="Training Assignment Lag — 5 Days Post-Revision",
        description="Training must be assigned within 5 days of document effective date for all impacted roles.",
        domain="training",
        rule_type="internal",
        severity="minor",
        regulatory_ref="21 CFR 211.68",
        internal_ref="SOP-TRN-002 §4.0",
        evaluate=lambda r: (
            r.get("training_type") == "Change-Driven"
            and r.get("status") == "Overdue"
            and (_days_since(r.get("due_date")) or 0) > 14
        ),
        breach_message="Change-driven training {training_record_id} overdue by {overdue_days} days. Training lag policy breached.",
        remediation="Review assignment process. Escalate to Training Coordinator and document owner.",
    ),

    # ════════════════════════════════════════════════════════════════
    # AUDIT RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-AUD-001",
        title="Critical Audit Finding — Zero Tolerance",
        description="Critical audit findings require immediate CAPA and executive notification. No critical findings are acceptable.",
        domain="audit",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="ICH Q10 §3.2, EU GMP Chapter 9",
        internal_ref="SOP-QA-007 §5.0",
        evaluate=lambda r: (
            r.get("classification") == "Critical"
            and not r.get("capa_id")
        ),
        breach_message="Critical audit finding {finding_id} in {process_area} — no CAPA linked.",
        remediation="Open emergency CAPA within 24 hours. Notify site QA Director and VP Quality. Assess regulatory notification obligation.",
    ),

    PolicyRule(
        rule_id="POL-AUD-002",
        title="Audit Response — 30-Day Submission Limit",
        description="Written responses to all audit findings must be submitted within 30 days of audit close.",
        domain="audit",
        rule_type="regulatory",
        severity="major",
        regulatory_ref="FDA ORA Compliance Program 7356.002",
        internal_ref="SOP-QA-007 §6.1",
        evaluate=lambda r: (
            r.get("response_status") in ("Open", None)
            and r.get("response_date") is None
            and (_days_since(r.get("close_date")) or 0) > 30
        ),
        breach_message="Audit finding {finding_id} response overdue — {age_days} days since audit close.",
        remediation="Assign response owner immediately. Escalate to site head if regulatory body finding.",
    ),

    PolicyRule(
        rule_id="POL-AUD-003",
        title="Repeat Audit Finding — Systemic CAPA Required",
        description="Repeat findings (same observation in successive audits) require systemic CAPA with root cause analysis.",
        domain="audit",
        rule_type="internal",
        severity="major",
        regulatory_ref="ICH Q10 §3.2.3",
        internal_ref="SOP-QA-007 §7.0",
        evaluate=lambda r: r.get("is_repeat_finding") is True and not r.get("capa_id"),
        breach_message="Repeat finding {finding_id} in {process_area} — systemic CAPA not initiated.",
        remediation="Open CAPA specifically targeting systemic root cause. Engage cross-site quality team if finding appears at multiple sites.",
    ),

    # ════════════════════════════════════════════════════════════════
    # SUPPLIER RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-SUP-001",
        title="API Supplier Rejection Rate — 1% Threshold",
        description="Critical API suppliers with rejection rate >1% require immediate CAPA and supplier notification.",
        domain="supplier",
        rule_type="internal",
        severity="major",
        regulatory_ref="21 CFR 211.84(c)",
        internal_ref="SOP-QA-010 §5.3",
        evaluate=lambda r: (
            r.get("supplier_type") == "API"
            and (r.get("rejection_rate_pct") or 0) > 1.0
        ),
        breach_message="API supplier {supplier_name} rejection rate {rejection_rate_pct}% exceeds 1% policy threshold.",
        remediation="Open supplier CAPA. Initiate incoming inspection increase to 100%. Notify Procurement and QA Director. Schedule supplier audit within 30 days.",
    ),

    PolicyRule(
        rule_id="POL-SUP-002",
        title="Supplier Requalification Overdue",
        description="All approved suppliers must be requalified on schedule per approved vendor list policy.",
        domain="supplier",
        rule_type="internal",
        severity="major",
        regulatory_ref="21 CFR 211.84",
        internal_ref="SOP-QA-010 §4.1",
        evaluate=lambda r: (
            r.get("qualification_status") == "Approved"
            and r.get("requalification_due_dt") is not None
            and (_days_since(r.get("requalification_due_dt")) or 0) > 0
        ),
        breach_message="Supplier {supplier_name} requalification overdue by {overdue_days} days.",
        remediation="Suspend new purchase orders pending requalification. Assign Supplier Quality Engineer. Complete requalification within 30 days or escalate to conditional approval.",
    ),

    # ════════════════════════════════════════════════════════════════
    # RISK RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-RISK-001",
        title="Unacceptable Residual Risk — Action Required",
        description="Risk items with residual RPN >200 or classified Unacceptable must have linked CAPA.",
        domain="risk",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="ICH Q9 §5",
        internal_ref="SOP-QA-015 §6.2",
        evaluate=lambda r: (
            r.get("risk_acceptance_status") == "Unacceptable"
            and not r.get("linked_capa_id")
            and r.get("status") == "Active"
        ),
        breach_message="Risk {risk_id} classified Unacceptable (RPN={residual_rpn}) with no linked CAPA.",
        remediation="Open CAPA for risk mitigation within 5 business days. Implement interim controls. Notify site Risk Owner and QA Director.",
    ),

    PolicyRule(
        rule_id="POL-RISK-002",
        title="Risk Review — 6-Month Frequency",
        description="All active risk register items must be reviewed at minimum every 6 months per ICH Q9.",
        domain="risk",
        rule_type="regulatory",
        severity="minor",
        regulatory_ref="ICH Q9 §5.4",
        internal_ref="SOP-QA-015 §7.0",
        evaluate=lambda r: (
            r.get("status") == "Active"
            and (_days_since(r.get("last_review_date")) or 0) > 180
        ),
        breach_message="Risk {risk_id} has not been reviewed in {age_days} days — exceeds 6-month ICH Q9 requirement.",
        remediation="Schedule risk review meeting. Update residual RPN. Document review outcome and next review date.",
    ),

    # ════════════════════════════════════════════════════════════════
    # DOCUMENT CONTROL RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-DOC-001",
        title="Document Periodic Review Overdue",
        description="All controlled GxP documents must be reviewed at their scheduled frequency (typically 24 months).",
        domain="document",
        rule_type="regulatory",
        severity="major",
        regulatory_ref="21 CFR 211.100(a), 21 CFR Part 11",
        internal_ref="SOP-DC-001 §5.0",
        evaluate=lambda r: (
            r.get("status") == "Effective"
            and r.get("gxp_classification") in ("GMP", "GCP", "GLP")
            and r.get("next_review_date") is not None
            and (_days_since(r.get("next_review_date")) or 0) > 0
        ),
        breach_message="Document {doc_id} ({doc_title}) periodic review overdue by {overdue_days} days.",
        remediation="Assign document owner to initiate review. If review results in no change, document rationale and update next review date.",
    ),

    # ════════════════════════════════════════════════════════════════
    # REGULATORY COMMITMENT RULES
    # ════════════════════════════════════════════════════════════════

    PolicyRule(
        rule_id="POL-REG-001",
        title="Regulatory Commitment — Response Date Breach",
        description="All FDA/EMA commitments must be fulfilled by the committed response date.",
        domain="regulatory",
        rule_type="regulatory",
        severity="critical",
        regulatory_ref="FDA ORA Compliance Program, 21 CFR 314",
        internal_ref="SOP-RA-005 §4.0",
        evaluate=lambda r: (
            r.get("status") in ("Open", "Overdue")
            and r.get("target_response_date") is not None
            and (_days_since(r.get("target_response_date")) or 0) > 0
        ),
        breach_message="Regulatory commitment {commitment_id} to {inspecting_authority} overdue by {overdue_days} days.",
        remediation="IMMEDIATE: Notify VP Regulatory Affairs and Legal. Draft interim response. Assess risk of escalation to Warning Letter. All other work pauses.",
    ),
]


# ── Rule lookup by domain ──────────────────────────────────────────

_RULES_BY_DOMAIN: dict[str, list[PolicyRule]] = {}
for _r in RULES:
    _RULES_BY_DOMAIN.setdefault(_r.domain, []).append(_r)


def get_rules(domain: str | None = None) -> list[PolicyRule]:
    """Return all rules, optionally filtered by domain."""
    if domain:
        return _RULES_BY_DOMAIN.get(domain, [])
    return RULES


def get_rule(rule_id: str) -> PolicyRule | None:
    return next((r for r in RULES if r.rule_id == rule_id), None)


# ── Policy evaluation engine ───────────────────────────────────────

def evaluate_records(
    records: list[dict],
    domain: str,
    record_id_field: str = "id",
) -> PolicyEvaluationResult:
    """
    Evaluate a list of data records against all rules for a domain.
    Returns a PolicyEvaluationResult with all breaches.
    """
    rules = get_rules(domain)
    breaches: list[PolicyBreach] = []

    for record in records:
        record_id = str(record.get(record_id_field, "unknown"))
        age_days = _days_since(
            record.get("initiation_date") or
            record.get("detection_date") or
            record.get("assigned_date") or
            record.get("last_review_date")
        ) or 0
        overdue_days = _days_since(
            record.get("target_close_date") or
            record.get("due_date") or
            record.get("next_review_date") or
            record.get("requalification_due_dt") or
            record.get("target_response_date")
        ) or 0

        for rule in rules:
            try:
                if rule.evaluate(record):
                    msg = rule.breach_message
                    # Interpolate known fields
                    for key, val in record.items():
                        msg = msg.replace(f"{{{key}}}", str(val) if val is not None else "N/A")
                    msg = msg.replace("{age_days}", str(age_days))
                    msg = msg.replace("{overdue_days}", str(max(0, overdue_days)))

                    breaches.append(PolicyBreach(
                        rule_id=rule.rule_id,
                        rule_title=rule.title,
                        severity=rule.severity,
                        regulatory_ref=rule.regulatory_ref,
                        internal_ref=rule.internal_ref,
                        domain=domain,
                        record_id=record_id,
                        breach_message=msg,
                        remediation=rule.remediation,
                    ))
            except Exception:
                pass  # Malformed record — skip silently

    critical = sum(1 for b in breaches if b.severity == "critical")
    major    = sum(1 for b in breaches if b.severity == "major")
    n        = len(records)
    compliant = max(0, n - len(set(b.record_id for b in breaches)))
    score = (compliant / n * 100) if n > 0 else 100.0

    return PolicyEvaluationResult(
        total_records=n,
        total_evaluated=n,
        breach_count=len(breaches),
        critical_count=critical,
        major_count=major,
        breaches=breaches,
        compliance_score=score,
        rules_applied=[r.rule_id for r in rules],
        domain=domain,
    )


def evaluate_single(record: dict, domain: str, record_id: str) -> list[PolicyBreach]:
    """Evaluate a single record against all domain rules. Lightweight path."""
    result = evaluate_records([record], domain, record_id_field=list(record.keys())[0])
    for b in result.breaches:
        b.record_id = record_id
    return result.breaches


def get_inspection_readiness_score(domain_scores: dict[str, float]) -> dict:
    """
    Roll up per-domain compliance scores into a single inspection readiness score.
    Weights reflect regulatory inspection focus areas.
    """
    weights = {
        "capa":       0.25,
        "deviation":  0.20,
        "training":   0.15,
        "audit":      0.15,
        "document":   0.10,
        "supplier":   0.08,
        "risk":       0.05,
        "regulatory": 0.02,
    }
    weighted_score = sum(
        domain_scores.get(d, 100.0) * w
        for d, w in weights.items()
    )
    rag = "green" if weighted_score >= 90 else "amber" if weighted_score >= 75 else "red"
    return {
        "overall_score": round(weighted_score, 1),
        "rag_status": rag,
        "domain_scores": domain_scores,
        "weights_applied": weights,
        "interpretation": (
            "Inspection Ready" if weighted_score >= 90
            else "Remediation Required" if weighted_score >= 75
            else "High Regulatory Risk — Immediate Action"
        ),
    }
