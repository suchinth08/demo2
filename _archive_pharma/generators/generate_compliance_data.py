"""
Pharma Compliance BI — Synthetic Data Generator
Generates realistic CSV data for all compliance domains.
Embeds real-world patterns: seasonal spikes, site variation, trends, correlations.

Usage: python generate_compliance_data.py
Output: ../csv/*.csv  (ready for DuckDB / Malloy / pandas)
"""

import csv
import random
import os
from datetime import date, timedelta, datetime
from pathlib import Path

random.seed(42)  # reproducible

OUT_DIR = Path(__file__).parent.parent / "csv"
OUT_DIR.mkdir(exist_ok=True)

START_DATE = date(2022, 1, 1)
END_DATE   = date(2024, 12, 31)

def rdate(start=START_DATE, end=END_DATE):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def rdate_after(d, min_days=1, max_days=60):
    return d + timedelta(days=random.randint(min_days, max_days))

def write_csv(filename, rows, headers):
    path = OUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):>5} rows -> {filename}")

# ─────────────────────────────────────────
# REFERENCE DATA
# ─────────────────────────────────────────

SITES = [
    {"site_id": "SITE-US-01", "site_name": "Philadelphia Manufacturing", "country": "USA",     "site_type": "Manufacturing", "gxp_scope": "GMP",     "fda_estab_id": "3001234", "is_active": True},
    {"site_id": "SITE-US-02", "site_name": "Boston R&D Center",          "country": "USA",     "site_type": "R&D",           "gxp_scope": "GMP+GLP", "fda_estab_id": "3005678", "is_active": True},
    {"site_id": "SITE-EU-01", "site_name": "Dublin Manufacturing",        "country": "Ireland", "site_type": "Manufacturing", "gxp_scope": "GMP",     "fda_estab_id": "4001100", "is_active": True},
    {"site_id": "SITE-EU-02", "site_name": "Frankfurt QC Laboratory",     "country": "Germany", "site_type": "QC Lab",        "gxp_scope": "GMP+GLP", "fda_estab_id": "4002200", "is_active": True},
    {"site_id": "SITE-AP-01", "site_name": "Hyderabad API Manufacturing", "country": "India",   "site_type": "Manufacturing", "gxp_scope": "GMP",     "fda_estab_id": "5001001", "is_active": True},
]
SITE_IDS = [s["site_id"] for s in SITES]

DEPARTMENTS = []
dept_id = 1
DEPT_MAP = {}  # site_id → list of dept_ids
dept_names_by_type = {
    "Manufacturing": ["Manufacturing-Suite A", "Manufacturing-Suite B", "Fill & Finish", "Packaging", "Warehouse"],
    "R&D":           ["Formulation R&D", "Analytical R&D", "Process Development"],
    "QC Lab":        ["Microbiology QC", "Analytical QC", "Stability QC"],
    "default":       ["Quality Assurance", "Regulatory Affairs", "Supply Chain", "Engineering", "EHS"]
}
for s in SITES:
    names = dept_names_by_type.get(s["site_type"], []) + dept_names_by_type["default"]
    DEPT_MAP[s["site_id"]] = []
    for dn in names:
        DEPARTMENTS.append({
            "dept_id": dept_id, "dept_name": dn,
            "dept_code": f"{s['site_id'][:7]}-{dn[:3].upper().replace(' ','')}",
            "site_id": s["site_id"], "parent_dept_id": None, "dept_head_id": None
        })
        DEPT_MAP[s["site_id"]].append(dept_id)
        dept_id += 1

PRODUCTS = [
    {"product_id": 1, "product_code": "PRD-001", "product_name": "Cardivex 10mg Tablet",       "product_type": "Drug Product", "dosage_form": "Tablet",     "therapeutic_area": "Cardiovascular",    "nda_anda_number": "NDA-201234", "regulatory_status": "Approved",       "is_gmp": True, "is_serialized": True},
    {"product_id": 2, "product_code": "PRD-002", "product_name": "Neurofen 50mg Capsule",       "product_type": "Drug Product", "dosage_form": "Capsule",    "therapeutic_area": "Neurology",         "nda_anda_number": "NDA-201890", "regulatory_status": "Approved",       "is_gmp": True, "is_serialized": True},
    {"product_id": 3, "product_code": "PRD-003", "product_name": "Respiraze 5mg/mL Injectable", "product_type": "Drug Product", "dosage_form": "Injectable", "therapeutic_area": "Respiratory",       "nda_anda_number": "NDA-202100", "regulatory_status": "Approved",       "is_gmp": True, "is_serialized": True},
    {"product_id": 4, "product_code": "PRD-004", "product_name": "Oncovax Biologic 100mg",      "product_type": "Biologic",     "dosage_form": "Injectable", "therapeutic_area": "Oncology",          "nda_anda_number": "BLA-125400", "regulatory_status": "Approved",       "is_gmp": True, "is_serialized": True},
    {"product_id": 5, "product_code": "PRD-005", "product_name": "ImmunoShield Vaccine",        "product_type": "Biologic",     "dosage_form": "Injectable", "therapeutic_area": "Immunology",        "nda_anda_number": "BLA-125600", "regulatory_status": "Investigational","is_gmp": True, "is_serialized": False},
    {"product_id": 6, "product_code": "PRD-006", "product_name": "GlucoBalance 500mg Tablet",   "product_type": "Drug Product", "dosage_form": "Tablet",     "therapeutic_area": "Endocrinology",     "nda_anda_number": "ANDA-090123","regulatory_status": "Approved",       "is_gmp": True, "is_serialized": True},
    {"product_id": 7, "product_code": "PRD-007", "product_name": "AcidRelief 20mg DR Capsule",  "product_type": "Drug Product", "dosage_form": "Capsule",    "therapeutic_area": "Gastroenterology",  "nda_anda_number": "ANDA-078900","regulatory_status": "Approved",       "is_gmp": True, "is_serialized": False},
    {"product_id": 8, "product_code": "API-001", "product_name": "Cardivex API",                "product_type": "Drug Substance","dosage_form": None,         "therapeutic_area": "Cardiovascular",    "nda_anda_number": None,         "regulatory_status": "Approved",       "is_gmp": True, "is_serialized": False},
]
PRODUCT_IDS = [p["product_id"] for p in PRODUCTS]

SUPPLIERS = []
SUP_NAMES = [
    ("Sigma API Solutions", "API", "USA", "High"),       # will have worsening trend
    ("Merck KGaA Chemicals", "API", "Germany", "Low"),
    ("Divi's Laboratories", "API", "India", "Medium"),
    ("Lonza AG", "API", "Switzerland", "Low"),
    ("BASF Pharma", "Excipient", "Germany", "Low"),
    ("Roquette Freres", "Excipient", "France", "Low"),
    ("Colorcon Ltd", "Excipient", "UK", "Medium"),
    ("Huhtamaki Packaging", "Packaging", "Finland", "Low"),
    ("Schott Pharma", "Packaging", "Germany", "Low"),
    ("Berry Plastics", "Packaging", "USA", "Medium"),
    ("Catalent Pharma", "CMO", "USA", "Medium"),
    ("Patheon-Thermo", "CMO", "USA", "Medium"),
    ("Covance CRO", "CRO", "USA", "Low"),
    ("Quintiles IMS", "CRO", "USA", "Low"),
    ("ALS Laboratories", "Service", "Australia", "Medium"),
]
for i, (name, stype, country, risk) in enumerate(SUP_NAMES, 1):
    qual_date = rdate(date(2019,1,1), date(2022,12,31))
    SUPPLIERS.append({
        "supplier_id": i,
        "supplier_code": f"SUP-{i:04d}",
        "supplier_name": name,
        "supplier_type": stype,
        "qualification_status": random.choices(["Approved","Approved","Approved","Conditional"], weights=[7,7,7,1])[0],
        "qualification_date": qual_date,
        "requalification_due_dt": qual_date + timedelta(days=3*365),
        "country": country,
        "regulatory_approvals": "FDA DMF" if stype == "API" else "",
        "risk_rating": risk,
        "is_gmp_critical": stype in ("API", "CMO")
    })

EMPLOYEES = []
EMP_MAP = {}  # site_id → list of employee_ids
FIRST_NAMES = ["James","Sarah","Michael","Emily","Robert","Jessica","David","Jennifer","John","Ashley",
               "Priya","Rahul","Anita","Vikram","Kavya","Ravi","Sunita","Arun","Meera","Kiran",
               "Patrick","Siobhan","Declan","Aoife","Ciaran","Brigid","Liam","Niamh","Eoin","Fiona",
               "Hans","Greta","Klaus","Ingrid","Werner","Heike","Friedrich","Sabine","Thomas","Anna"]
LAST_NAMES  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Moore",
               "Patel","Sharma","Kumar","Singh","Rao","Reddy","Nair","Iyer","Pillai","Menon",
               "Murphy","O'Brien","Kelly","Walsh","Ryan","O'Connor","Byrne","Doyle","Gallagher","Burke",
               "Mueller","Schmidt","Fischer","Weber","Wagner","Becker","Schulz","Hoffmann","Braun","Richter"]
TITLES = ["QA Specialist","QA Manager","Manufacturing Associate","Manufacturing Supervisor",
          "Regulatory Affairs Specialist","QC Analyst","QC Supervisor","Validation Engineer",
          "Compliance Manager","Training Coordinator","Document Control Specialist",
          "Supply Chain Manager","EHS Specialist","Process Engineer","Microbiology Analyst"]

emp_id = 1
for s in SITES:
    EMP_MAP[s["site_id"]] = []
    count = 120 if s["site_type"] == "Manufacturing" else 40
    for _ in range(count):
        dept_id_choice = random.choice(DEPT_MAP[s["site_id"]])
        EMPLOYEES.append({
            "employee_id": emp_id,
            "employee_number": f"EMP-{emp_id:05d}",
            "first_name": random.choice(FIRST_NAMES),
            "last_name":  random.choice(LAST_NAMES),
            "department_id": dept_id_choice,
            "site_id": s["site_id"],
            "job_title": random.choice(TITLES),
            "role_id": None,
            "manager_id": None,
            "hire_date": rdate(date(2015,1,1), date(2023,12,31)),
            "gmp_role": random.choices(["GMP","GMP","Non-GMP"], weights=[6,6,1])[0],
            "is_active": random.choices([True, False], weights=[95,5])[0],
            "employment_type": random.choices(["Full-Time","Contractor","Part-Time"], weights=[80,15,5])[0]
        })
        EMP_MAP[s["site_id"]].append(emp_id)
        emp_id += 1

# ─────────────────────────────────────────
# BATCHES
# ─────────────────────────────────────────
BATCHES = []
batch_id = 1
BATCH_ID_MAP = []  # list of batch_id strings
MFG_SITES = ["SITE-US-01", "SITE-EU-01", "SITE-AP-01"]
MFG_PRODUCTS = [1,2,3,4,6,7,8]

for m in range(36):  # 36 months
    month_date = date(2022, 1, 1) + timedelta(days=30*m)
    # Q4 slightly higher volume
    count = random.randint(55, 70) if month_date.month in (10,11,12) else random.randint(40, 55)
    for _ in range(count):
        site = random.choice(MFG_SITES)
        prod_id = random.choice(MFG_PRODUCTS)
        mfg_date = month_date + timedelta(days=random.randint(0, 28))
        rel_date = mfg_date + timedelta(days=random.randint(14, 45))
        bid = f"BATCH-{batch_id:05d}"
        # SITE-EU-02 has higher rejection (embedded pattern)
        reject_prob = 0.02 if site == "SITE-EU-01" else 0.005
        status = random.choices(
            ["Released", "Rejected", "On Hold"],
            weights=[1 - reject_prob - 0.01, reject_prob, 0.01]
        )[0]
        BATCHES.append({
            "batch_id": bid,
            "product_id": prod_id,
            "batch_number": f"BN-{prod_id:02d}-{mfg_date.strftime('%y%m%d')}-{batch_id%99:02d}",
            "manufacturing_date": mfg_date,
            "release_date": rel_date if status == "Released" else None,
            "expiry_date": rel_date + timedelta(days=730) if status == "Released" else None,
            "batch_size": round(random.uniform(5000, 50000), 0),
            "batch_size_unit": random.choice(["kg","L","units"]),
            "site_id": site,
            "manufacturing_line": f"Line-{random.randint(1,4)}",
            "batch_status": status,
            "disposition_date": rel_date + timedelta(days=random.randint(0, 5)) if status != "In Process" else None
        })
        BATCH_ID_MAP.append(bid)
        batch_id += 1

# ─────────────────────────────────────────
# DOCUMENTS
# ─────────────────────────────────────────
DOC_TEMPLATES = [
    ("SOP", "QA", "SOP for Handling Out of Specification Results", "21 CFR 211.192", "GMP"),
    ("SOP", "QA", "SOP for CAPA Management",                      "21 CFR 820.100", "GMP"),
    ("SOP", "QA", "SOP for Deviation Reporting and Investigation", "21 CFR 211.192","GMP"),
    ("SOP", "QA", "SOP for Batch Record Review",                  "21 CFR 211.186", "GMP"),
    ("SOP", "QA", "SOP for Change Control Management",            "ICH Q10",        "GMP"),
    ("SOP", "QA", "SOP for Supplier Qualification",               "21 CFR 211.84",  "GMP"),
    ("SOP", "Mfg","SOP for Cleanroom Gowning Procedure",          "EU GMP Annex 1", "GMP"),
    ("SOP", "Mfg","SOP for Equipment Cleaning Validation",        "21 CFR 211.67",  "GMP"),
    ("SOP", "Mfg","SOP for Line Clearance",                       "21 CFR 211.130", "GMP"),
    ("SOP", "Mfg","SOP for Temperature Excursion Management",     "21 CFR 211.68",  "GMP"),
    ("SOP", "QC", "SOP for HPLC System Suitability Testing",      "USP <621>",      "GMP"),
    ("SOP", "QC", "SOP for Microbial Limit Testing",              "USP <61>",       "GMP"),
    ("SOP", "QC", "SOP for Stability Sample Management",          "ICH Q1A",        "GMP"),
    ("SOP", "RA", "SOP for Regulatory Submission Management",     "21 CFR 314",     "GMP"),
    ("SOP", "EHS","SOP for Hazardous Material Handling",          "OSHA 29 CFR",    "Non-GxP"),
    ("Policy","QA","GMP Training Policy",                          "21 CFR 211.68",  "GMP"),
    ("Policy","QA","Data Integrity Policy",                        "21 CFR Part 11", "GMP"),
    ("Policy","QA","Document Control Policy",                      "21 CFR Part 11", "GMP"),
    ("WI",   "Mfg","Work Instruction: Tablet Compression Operation","21 CFR 211",   "GMP"),
    ("WI",   "Mfg","Work Instruction: Autoclave Loading/Unloading", "EU GMP",       "GMP"),
]

DOCUMENTS = []
doc_counter = 1
DOC_IDS = []
for site in SITES:
    for dtype, func, title, reg_ref, gxp in DOC_TEMPLATES:
        doc_id = f"DOC-{doc_counter:04d}"
        eff = rdate(date(2020,1,1), date(2023,6,30))
        review_due = eff + timedelta(days=24*30)
        is_overdue = review_due < END_DATE and random.random() < 0.12  # 12% overdue
        DOCUMENTS.append({
            "doc_id": doc_id,
            "doc_number": f"{dtype}-{func[:3].upper()}-{doc_counter:03d}",
            "doc_title": f"{title} - {site['site_name']}",
            "doc_type": dtype,
            "business_function": func,
            "gxp_classification": gxp,
            "current_version": f"{random.randint(1,4)}.{random.randint(0,3)}",
            "status": "Effective",
            "effective_date": eff,
            "next_review_date": review_due if not is_overdue else review_due - timedelta(days=random.randint(30,180)),
            "last_review_date": eff,
            "review_freq_months": 24,
            "owner_dept_id": random.choice(DEPT_MAP[site["site_id"]]),
            "doc_owner_id": random.choice(EMP_MAP[site["site_id"]]),
            "regulatory_ref": reg_ref,
            "is_controlled": True,
            "site_id": site["site_id"],
            "training_required": dtype in ("SOP", "Policy")
        })
        DOC_IDS.append(doc_id)
        doc_counter += 1

# ─────────────────────────────────────────
# CAPAs
# ─────────────────────────────────────────
ROOT_CAUSES = ["Training", "Procedure", "Equipment", "System", "Material", "Human Error", "Communication"]
RC_WEIGHTS   = [25, 20, 15, 10, 12, 13, 5]  # Training and Procedure most common

CAPA_RECORDS = []
CAPA_IDS = []
capa_counter = 1
SOURCE_TYPES = ["Audit", "Deviation", "Complaint", "Inspection", "Self-Identified"]
SEVERITIES = ["Critical", "Major", "Minor"]
SEV_WEIGHTS = [10, 35, 55]

for site in SITES:
    # SITE-EU-02 has more CAPAs (compliance challenge pattern)
    n_capas = random.randint(35, 50) if site["site_id"] != "SITE-EU-02" else random.randint(55, 70)
    for _ in range(n_capas):
        capa_id = f"CAPA-{capa_counter:04d}"
        init_date = rdate()
        sev = random.choices(SEVERITIES, weights=SEV_WEIGHTS)[0]
        # Target close dates per severity
        target_days = {"Critical": 30, "Major": 60, "Minor": 90}[sev]
        target_close = init_date + timedelta(days=target_days)
        # 15% overdue (EU-02 site 25% overdue — embedded pattern)
        overdue_prob = 0.25 if site["site_id"] == "SITE-EU-02" else 0.15
        is_closed = random.random() < 0.75
        if is_closed:
            # Some close late
            close_late = random.random() < overdue_prob
            actual_close = (target_close + timedelta(days=random.randint(5, 30))) if close_late \
                           else (init_date + timedelta(days=random.randint(5, target_days - 5)))
            status = "Closed"
        else:
            actual_close = None
            status = "Overdue" if target_close < date.today() else random.choice(["Open", "In Progress", "Pending Effectiveness"])

        rc = random.choices(ROOT_CAUSES, weights=RC_WEIGHTS)[0]
        reopen = random.choices([0,1,2], weights=[85,12,3])[0]
        eff_req = sev in ("Critical", "Major")

        CAPA_RECORDS.append({
            "capa_id": capa_id,
            "site_id": site["site_id"],
            "department_id": random.choice(DEPT_MAP[site["site_id"]]),
            "source_type": random.choice(SOURCE_TYPES),
            "source_reference_id": None,
            "severity": sev,
            "root_cause_category": rc,
            "root_cause_detail": f"Root cause identified as {rc.lower()} deficiency in {random.choice(['QA','Manufacturing','QC','Regulatory'])}",
            "description": f"CAPA initiated for {sev.lower()} quality event at {site['site_name']}",
            "initiated_by": "Quality System",
            "owner_employee_id": random.choice(EMP_MAP[site["site_id"]]),
            "initiation_date": init_date,
            "target_close_date": target_close,
            "actual_close_date": actual_close,
            "status": status,
            "effectiveness_check_req": eff_req,
            "effectiveness_check_date": (actual_close + timedelta(days=90)) if (is_closed and eff_req) else None,
            "effectiveness_check_result": random.choices(["Pass","Fail","Pending"], weights=[80,10,10])[0] if (is_closed and eff_req) else None,
            "reopen_count": reopen,
            "regulatory_notif_required": sev == "Critical" and random.random() < 0.3
        })
        CAPA_IDS.append(capa_id)
        capa_counter += 1

# ─────────────────────────────────────────
# DEVIATIONS
# ─────────────────────────────────────────
DEV_CATEGORIES = ["Equipment", "Process", "Personnel", "Material", "Environmental", "Analytical"]
DEV_WEIGHTS    = [22, 30, 18, 12, 8, 10]
AREAS = ["Granulation Suite", "Compression Suite", "Coating Suite", "Fill & Finish", "QC Laboratory",
         "Packaging Line 1", "Packaging Line 2", "Warehouse", "Cleanroom A", "Cleanroom B"]

DEVIATIONS = []
dev_counter = 1
for site in SITES:
    batch_subset = [b for b in BATCHES if b["site_id"] == site["site_id"]]
    n_dev = int(len(batch_subset) * random.uniform(0.025, 0.04))
    for _ in range(n_dev):
        dev_id = f"DEV-{dev_counter:04d}"
        det_date = rdate()
        sev = random.choices(SEVERITIES, weights=[5, 30, 65])[0]
        cat = random.choices(DEV_CATEGORIES, weights=DEV_WEIGHTS)[0]
        # Q4 spike — embedded seasonal pattern
        if det_date.month in (10, 11, 12):
            extra = random.choices([True, False], weights=[3, 7])[0]
            if extra and sev == "Minor":
                sev = "Major"

        # Link to batch if manufacturing deviation
        batch_link = None
        if cat in ("Process", "Equipment") and batch_subset:
            batch_link = random.choice(batch_subset)["batch_id"]
        capa_link = random.choice(CAPA_IDS) if sev in ("Critical", "Major") and random.random() < 0.7 else None
        dispo = "None"
        if sev == "Critical": dispo = random.choice(["Hold", "Reject"])
        elif sev == "Major":  dispo = random.choices(["None","Hold","Conditional Release"], weights=[6,3,1])[0]

        DEVIATIONS.append({
            "deviation_id": dev_id,
            "site_id": site["site_id"],
            "department_id": random.choice(DEPT_MAP[site["site_id"]]),
            "batch_id": batch_link,
            "product_id": random.choice(PRODUCT_IDS),
            "deviation_category": cat,
            "deviation_type": random.choices(["Unplanned","Planned"], weights=[85,15])[0],
            "severity": sev,
            "description": f"{sev} {cat.lower()} deviation detected during routine operation",
            "detected_by": random.choice(EMP_MAP[site["site_id"]]),
            "detection_date": det_date,
            "manufacturing_area": random.choice(AREAS),
            "equipment_id": None,
            "shift": random.choices(["Day","Evening","Night"], weights=[50,30,20])[0],
            "gmp_classification": "GMP",
            "investigation_required": sev in ("Critical","Major"),
            "investigation_close_dt": (det_date + timedelta(days=random.randint(5,45))) if sev in ("Critical","Major") else None,
            "root_cause_category": random.choices(ROOT_CAUSES, weights=RC_WEIGHTS)[0],
            "root_cause_description": "Investigation identified procedural gap",
            "capa_id": capa_link,
            "batch_disposition_impact": dispo,
            "status": random.choice(["Closed","Closed","Open","Under Investigation"])
        })
        dev_counter += 1

# ─────────────────────────────────────────
# AUDITS + FINDINGS
# ─────────────────────────────────────────
AUDITS_DATA = []
FINDINGS_DATA = []
audit_counter = 1
finding_counter = 1
AUDIT_TYPES   = ["Internal", "External-Regulatory", "Supplier", "System"]
AUDIT_BODIES  = {"Internal":"Internal QA", "External-Regulatory": random.choice(["FDA","EMA","MHRA"]), "Supplier":"Internal QA", "System":"Internal QA"}
REG_FRAMEWORKS = ["21 CFR 211","21 CFR 820","ICH Q10","EU GMP","ISO 9001"]
PROCESS_AREAS  = ["Document Control","Training Management","Change Control","CAPA System",
                  "Manufacturing","QC Laboratory","Environmental Monitoring","Computer Systems Validation","Supplier Management","Batch Record Review"]
REGULATORY_REFS = ["21 CFR 211.68","21 CFR 211.100","21 CFR 211.192","21 CFR 820.100",
                   "EU GMP Chapter 4","EU GMP Chapter 5","ICH Q10 3.2","21 CFR Part 11.10"]

for site in SITES:
    for year in (2022, 2023, 2024):
        # Internal audits: 3-4 per site per year
        for _ in range(random.randint(3, 4)):
            audit_id = f"AUD-{audit_counter:04d}"
            start = date(year, random.randint(1,11), random.randint(1,28))
            days = random.uniform(1.5, 5.0)
            end = start + timedelta(days=int(days))
            n_findings = random.randint(3, 12)
            crit = random.randint(0, 1) if site["site_id"] == "SITE-EU-02" else 0
            maj  = random.randint(1, 4)
            min_ = random.randint(2, 6)
            obs  = n_findings - crit - maj - min_
            if obs < 0: obs = 0; n_findings = crit + maj + min_

            AUDITS_DATA.append({
                "audit_id": audit_id,
                "audit_type": "Internal",
                "auditing_body": "Internal QA",
                "site_id": site["site_id"],
                "supplier_id": None,
                "audit_scope": f"GMP compliance audit covering {random.choice(PROCESS_AREAS)} and {random.choice(PROCESS_AREAS)}",
                "regulatory_framework": random.choice(REG_FRAMEWORKS),
                "lead_auditor": f"Lead Auditor {random.randint(1,10)}",
                "audit_start_date": start,
                "audit_end_date": end,
                "audit_days": round(days, 1),
                "overall_rating": random.choices(["Satisfactory","Acceptable","Unsatisfactory"], weights=[50,40,10])[0],
                "total_findings": n_findings,
                "critical_findings": crit,
                "major_findings": maj,
                "minor_findings": min_,
                "observations": obs,
                "status": "Closed" if end < date(2024, 10, 1) else "Response Pending",
                "report_issue_date": end + timedelta(days=14),
                "response_due_date": end + timedelta(days=30)
            })

            for fn in range(1, n_findings+1):
                if fn <= crit: cls = "Critical"
                elif fn <= crit+maj: cls = "Major"
                elif fn <= crit+maj+min_: cls = "Minor"
                else: cls = "Observation"
                is_repeat = random.random() < 0.08
                finding_id = f"FIND-{finding_counter:04d}"
                resp_date = end + timedelta(days=random.randint(5, 35))
                FINDINGS_DATA.append({
                    "finding_id": finding_id,
                    "audit_id": audit_id,
                    "finding_number": fn,
                    "classification": cls,
                    "regulatory_ref": random.choice(REGULATORY_REFS),
                    "process_area": random.choice(PROCESS_AREAS),
                    "finding_description": f"{cls} finding in {random.choice(PROCESS_AREAS)} area",
                    "root_cause": random.choices(ROOT_CAUSES, weights=RC_WEIGHTS)[0],
                    "is_repeat_finding": is_repeat,
                    "prior_finding_id": None,
                    "capa_id": random.choice(CAPA_IDS) if cls in ("Critical","Major") else None,
                    "response_date": resp_date,
                    "response_status": random.choices(["Accepted","Submitted","Open"], weights=[70,20,10])[0],
                    "close_date": (resp_date + timedelta(days=random.randint(30,90))) if cls != "Open" else None
                })
                finding_counter += 1
            audit_counter += 1

# Regulatory inspections (FDA/EMA)
REG_INSPECTIONS = []
REG_COMMITMENTS = []
reg_insp_counter = 1
reg_commit_counter = 1
for site in ["SITE-US-01","SITE-EU-01","SITE-AP-01"]:
    for year in (2022, 2023, 2024):
        if random.random() < 0.6:  # not every site every year
            insp_id = f"INSP-{reg_insp_counter:04d}"
            start = date(year, random.randint(2,10), random.randint(1,20))
            end = start + timedelta(days=random.randint(3,7))
            form_483 = random.random() < 0.5
            obs_count = random.randint(1,5) if form_483 else 0
            outcome = random.choices(["NAI","VAI","OAI"], weights=[30,55,15])[0]
            REG_INSPECTIONS.append({
                "inspection_id": insp_id,
                "site_id": site,
                "inspecting_authority": "FDA" if "US" in site else "EMA",
                "inspection_type": random.choices(["Routine","Pre-Approval","Follow-Up"], weights=[60,25,15])[0],
                "inspection_start_date": start,
                "inspection_end_date": end,
                "lead_investigator": f"Investigator {random.randint(1,20)}",
                "form_483_issued": form_483,
                "form_483_observation_count": obs_count,
                "warning_letter_issued": outcome == "OAI" and random.random() < 0.5,
                "import_alert_issued": False,
                "overall_outcome": outcome,
                "response_due_date": end + timedelta(days=15)
            })
            # Create commitments for each 483 observation
            for _ in range(obs_count):
                commit_id = f"RCOM-{reg_commit_counter:04d}"
                commit_date = end + timedelta(days=random.randint(5,15))
                target_resp = commit_date + timedelta(days=random.randint(30,90))
                actual_resp = None
                c_status = "Open"
                if target_resp < date(2024, 10, 1):
                    if random.random() < 0.8:
                        actual_resp = target_resp + timedelta(days=random.randint(-10, 15))
                        c_status = "Accepted"
                    else:
                        c_status = "Overdue"
                REG_COMMITMENTS.append({
                    "commitment_id": commit_id,
                    "inspection_id": insp_id,
                    "commitment_description": f"Response to 483 observation regarding {random.choice(PROCESS_AREAS)}",
                    "regulatory_ref": random.choice(REGULATORY_REFS),
                    "committed_date": commit_date,
                    "committed_by": random.choice(EMP_MAP[site]),
                    "target_response_date": target_resp,
                    "actual_response_date": actual_resp,
                    "status": c_status,
                    "capa_id": random.choice(CAPA_IDS)
                })
                reg_commit_counter += 1
            reg_insp_counter += 1

# ─────────────────────────────────────────
# TRAINING RECORDS
# ─────────────────────────────────────────
TRAINING_RECORDS = []
tr_counter = 1
TRAIN_TYPES = ["Initial","Refresher","Change-Driven","Remedial"]
DELIVER_METHODS = ["eLearning","Classroom","Read-and-Understand","OJT"]

for emp in EMPLOYEES[:300]:  # first 300 employees for manageability
    n_trainings = random.randint(15, 35)
    for _ in range(n_trainings):
        doc_id = random.choice(DOC_IDS)
        assigned = rdate()
        due = assigned + timedelta(days=random.randint(7, 30))
        # Training compliance pattern: EU-02 site lower compliance
        complete_prob = 0.88 if emp["site_id"] == "SITE-EU-02" else 0.97
        is_completed = random.random() < complete_prob
        completion = (assigned + timedelta(days=random.randint(1, (due - assigned).days + 5))) if is_completed else None
        status = "Completed" if is_completed else ("Overdue" if due < date(2024,10,1) else "Assigned")
        score = round(random.uniform(70, 100), 1) if is_completed else None
        passed = (score >= 80) if score else None
        attempt = 1 if passed else (2 if score else 1)

        TRAINING_RECORDS.append({
            "training_record_id": tr_counter,
            "employee_id": emp["employee_id"],
            "doc_id": doc_id,
            "curriculum_id": None,
            "training_type": random.choices(TRAIN_TYPES, weights=[30,40,20,10])[0],
            "delivery_method": random.choices(DELIVER_METHODS, weights=[40,25,25,10])[0],
            "assigned_date": assigned,
            "due_date": due,
            "completion_date": completion,
            "assessment_score": score,
            "assessment_passed": passed,
            "attempt_number": attempt,
            "trainer_id": random.choice(EMP_MAP[emp["site_id"]]),
            "status": status,
            "waiver_reason": None
        })
        tr_counter += 1

# ─────────────────────────────────────────
# CHANGE REQUESTS
# ─────────────────────────────────────────
CHANGE_REQUESTS = []
chg_counter = 1
CHG_CATEGORIES = ["Process","Equipment","Material","Facility","Software","Labeling"]
CHG_TYPES = ["Minor","Major","Critical","Emergency"]
CHG_TYPE_WEIGHTS = [50, 35, 10, 5]
REG_FILING = ["None","CBE-30","CBE-0","PAS","None","None"]

for site in SITES:
    for year in (2022, 2023, 2024):
        n_chg = random.randint(25, 45)
        for _ in range(n_chg):
            chg_id = f"CHG-{chg_counter:04d}"
            init_date = date(year, random.randint(1,12), random.randint(1,28))
            chg_type = random.choices(CHG_TYPES, weights=CHG_TYPE_WEIGHTS)[0]
            days_to_close = {"Minor":45, "Major":90, "Critical":120, "Emergency":15}[chg_type]
            close_date = init_date + timedelta(days=random.randint(days_to_close-10, days_to_close+30))
            reg_impact = random.random() < 0.15
            CHANGE_REQUESTS.append({
                "change_id": chg_id,
                "change_title": f"{chg_type} {random.choice(CHG_CATEGORIES)} change at {site['site_name']}",
                "change_category": random.choice(CHG_CATEGORIES),
                "change_type": chg_type,
                "site_id": site["site_id"],
                "initiating_dept_id": random.choice(DEPT_MAP[site["site_id"]]),
                "requestor_id": random.choice(EMP_MAP[site["site_id"]]),
                "description": f"Change to improve compliance and quality in {site['site_name']}",
                "business_justification": "Quality improvement and regulatory compliance",
                "product_impact": random.random() < 0.4,
                "regulatory_impact": reg_impact,
                "regulatory_filing_required": random.choice(REG_FILING) if reg_impact else "None",
                "safety_impact": random.random() < 0.05,
                "initiation_date": init_date,
                "impact_assess_due_date": init_date + timedelta(days=14),
                "impact_assess_complete_dt": init_date + timedelta(days=random.randint(7, 21)),
                "approval_date": init_date + timedelta(days=random.randint(14, 45)),
                "implementation_date": close_date - timedelta(days=random.randint(5, 15)),
                "close_date": close_date if close_date <= END_DATE else None,
                "status": "Closed" if close_date <= END_DATE else random.choice(["Implementation","Approval"]),
                "approved_by": random.choice(EMP_MAP[site["site_id"]]),
                "linked_capa_id": random.choice(CAPA_IDS) if random.random() < 0.3 else None,
                "linked_deviation_id": None
            })
            chg_counter += 1

# ─────────────────────────────────────────
# SUPPLIER INCOMING INSPECTIONS
# ─────────────────────────────────────────
SUPPLIER_INSPECTIONS = []
si_counter = 1
MATERIALS_SIMPLE = ["Active Ingredient", "Diluent", "Binder", "Coating Agent", "Primary Packaging", "Secondary Packaging"]

for sup in SUPPLIERS[:10]:  # top 10 suppliers
    for _ in range(random.randint(20, 40)):
        recv = rdate()
        insp_date = recv + timedelta(days=random.randint(1, 5))
        # Sigma API Solutions (supplier_id=1) has worsening rejection — embedded trend
        if sup["supplier_id"] == 1:
            months_into_period = (recv - START_DATE).days // 30
            reject_prob = 0.01 + (months_into_period * 0.002)  # worsening over time
        else:
            reject_prob = 0.008 + (0.005 if sup["risk_rating"] == "High" else 0)

        result = random.choices(["Pass","Fail","Conditional Release"], weights=[1-reject_prob-0.005, reject_prob, 0.005])[0]
        SUPPLIER_INSPECTIONS.append({
            "inspection_id": si_counter,
            "supplier_id": sup["supplier_id"],
            "material_id": random.randint(1, 6),
            "po_number": f"PO-{random.randint(100000, 999999)}",
            "lot_number": f"LOT-{random.randint(10000, 99999)}",
            "receipt_date": recv,
            "inspection_date": insp_date,
            "qty_received": round(random.uniform(100, 5000), 1),
            "qty_unit": random.choice(["kg","L","units"]),
            "inspection_result": result,
            "rejection_reason": random.choice(["Out of Spec - Purity","Out of Spec - Particle Size","Failed ID Test","Contamination"]) if result == "Fail" else None,
            "coa_compliant": result != "Fail",
            "inspector_id": random.choice(EMP_MAP["SITE-US-01"]),
            "capa_triggered": random.choice(CAPA_IDS) if result == "Fail" else None
        })
        si_counter += 1

# ─────────────────────────────────────────
# RISK REGISTER
# ─────────────────────────────────────────
RISK_CATEGORIES = ["Process","Product Quality","Regulatory","Patient Safety","Supply Chain","IT/Data Integrity"]
RISK_ITEMS = []
PROCESSES = ["Tablet Compression","Aseptic Fill","API Synthesis","Analytical Testing","Packaging",
             "Change Control","Computer Systems","Cold Chain Distribution","Supplier Management","Environmental Control"]
for i in range(1, 151):
    risk_id = f"RISK-{i:04d}"
    ini_s = random.randint(3, 10)
    ini_o = random.randint(2, 9)
    ini_d = random.randint(2, 9)
    ini_rpn = ini_s * ini_o * ini_d
    res_s = max(1, ini_s - random.randint(0, 3))
    res_o = max(1, ini_o - random.randint(0, 4))
    res_d = max(1, ini_d - random.randint(0, 3))
    res_rpn = res_s * res_o * res_d
    site = random.choice(SITE_IDS)
    last_rev = rdate(date(2022,1,1), date(2024,6,30))
    RISK_ITEMS.append({
        "risk_id": risk_id,
        "risk_title": f"Risk: {random.choice(PROCESSES)} failure at {site}",
        "risk_description": f"Potential failure in {random.choice(PROCESSES)} affecting product quality",
        "risk_category": random.choice(RISK_CATEGORIES),
        "business_process": random.choice(PROCESSES),
        "product_id": random.choice(PRODUCT_IDS),
        "site_id": site,
        "risk_owner_id": random.choice(EMP_MAP[site]),
        "initial_severity": ini_s,
        "initial_occurrence": ini_o,
        "initial_detectability": ini_d,
        "initial_rpn": ini_rpn,
        "risk_controls": "Control measures implemented per ICH Q9",
        "residual_severity": res_s,
        "residual_occurrence": res_o,
        "residual_detectability": res_d,
        "residual_rpn": res_rpn,
        "risk_acceptance_status": "Acceptable" if res_rpn <= 100 else ("ALARP" if res_rpn <= 200 else "Unacceptable"),
        "last_review_date": last_rev,
        "next_review_date": last_rev + timedelta(days=180),
        "status": random.choices(["Active","Closed"], weights=[85,15])[0],
        "icq9_tool_used": random.choices(["FMEA","HACCP","FTA","PHA"], weights=[50,20,15,15])[0],
        "linked_capa_id": random.choice(CAPA_IDS) if res_rpn > 100 and random.random() < 0.6 else None
    })

# ─────────────────────────────────────────
# WRITE ALL CSV FILES
# ─────────────────────────────────────────
print("\n Generating Pharma Compliance Sample Data...")
print("=" * 50)

write_csv("sites.csv", SITES, list(SITES[0].keys()))
write_csv("departments.csv", DEPARTMENTS, list(DEPARTMENTS[0].keys()))
write_csv("employees.csv", EMPLOYEES, list(EMPLOYEES[0].keys()))
write_csv("products.csv", PRODUCTS, list(PRODUCTS[0].keys()))
write_csv("suppliers.csv", SUPPLIERS, list(SUPPLIERS[0].keys()))
write_csv("batch_records.csv", BATCHES, list(BATCHES[0].keys()))
write_csv("documents.csv", DOCUMENTS, list(DOCUMENTS[0].keys()))
write_csv("capa_records.csv", CAPA_RECORDS, list(CAPA_RECORDS[0].keys()))
write_csv("deviation_records.csv", DEVIATIONS, list(DEVIATIONS[0].keys()))
write_csv("audits.csv", AUDITS_DATA, list(AUDITS_DATA[0].keys()))
write_csv("audit_findings.csv", FINDINGS_DATA, list(FINDINGS_DATA[0].keys()))
write_csv("training_records.csv", TRAINING_RECORDS, list(TRAINING_RECORDS[0].keys()))
write_csv("change_requests.csv", CHANGE_REQUESTS, list(CHANGE_REQUESTS[0].keys()))
write_csv("supplier_inspections.csv", SUPPLIER_INSPECTIONS, list(SUPPLIER_INSPECTIONS[0].keys()))
write_csv("risk_register.csv", RISK_ITEMS, list(RISK_ITEMS[0].keys()))
write_csv("regulatory_inspections.csv", REG_INSPECTIONS, list(REG_INSPECTIONS[0].keys()))
write_csv("regulatory_commitments.csv", REG_COMMITMENTS, list(REG_COMMITMENTS[0].keys()))

print("\n All files written to data/csv/")
print("\n Embedded data patterns:")
print("  SITE-EU-02: Higher CAPA count, higher overdue rate, lower training compliance")
print("  Supplier-001 (Sigma API): Worsening rejection rate trend over time")
print("  Q4 months: Higher deviation frequency (year-end pressure pattern)")
print("  15% of findings marked as repeat findings (repeat observation pattern)")
print("  Post-inspection spike: CAPAs increase after regulatory inspections")
