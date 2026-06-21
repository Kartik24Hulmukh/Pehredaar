"""
Pehredaar — NPPA / CGHS Price Check Engine (PURE DETERMINISTIC CODE)
=====================================================================
No model calls. No network. Pure lookups + fuzzy matching + arithmetic.

Two regulatory regimes are checked here, and they are NOT equivalent:

1. **NPPA Ceiling Prices** — legally binding maximum retail prices (MRP caps)
   fixed under the Drugs (Prices Control) Order, 2013 (DPCO 2013) by the
   National Pharmaceutical Pricing Authority.  Selling a scheduled medicine
   above the ceiling price is a *legal violation* (overcharging).
   Source: S.O. 1547(E)/1548(E) dated 26.03.2024, effective 01.04.2024.

2. **CGHS Procedure Rates** — Central Government Health Scheme package rates
   for listed procedures.  These are a *reference benchmark*, NOT a legal
   price cap.  A private hospital charging above the CGHS rate is not
   committing a legal violation; the rate is used as a comparison benchmark
   to flag potentially inflated billing.

Every flag carries a citation and an explicit ``legal_status`` so downstream
consumers (Before-You-Sign sheet, ClaimBack appeals) never confuse a binding
NPPA breach with a soft CGHS benchmark deviation.
"""

from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import process, fuzz

# ============================================================================
# NPPA CEILING PRICES — legally binding (DPCO 2013)
# Effective 01.04.2024, S.O. 1547(E)/1548(E) dated 26.03.2024
# Key: lowercase drug name + strength.  Value: ceiling price per unit
# (per tablet / capsule / vial / ml) in INR.
# ============================================================================
NPPA_CEILING_PRICES: Dict[str, float] = {
    "paracetamol_650mg": 2.01,
    "metformin_1000mg": 3.49,
    "omeprazole_20mg": 2.87,
    "amoxicillin_250mg": 2.44,
    "amoxicillin_clavulanic_625mg": 22.46,
    "azithromycin_500mg": 23.57,
    "azithromycin_250mg": 11.65,
    "azithromycin_injection_500mg": 204.72,
    "aspirin_75mg": 0.35,
    "atorvastatin_40mg": 19.30,
    "amlodipine_2.5mg": 1.79,
    "metoprolol_25mg": 4.20,
    "cetirizine_10mg": 1.88,
    "diclofenac_50mg": 2.05,
    "ibuprofen_200mg": 0.71,
    "ciprofloxacin_250mg": 2.20,
    "levofloxacin_750mg": 12.45,
    "metronidazole_200mg": 0.82,
    "doxycycline_100mg": 3.08,
    "cefixime_400mg": 22.10,
    "cefuroxime_500mg": 51.43,
    "pantoprazole_injection_40mg": 50.45,
    "ondansetron_4mg": 5.14,
    "domperidone_10mg": 2.31,
    "glimepiride_2mg": 5.80,
    "telmisartan_20mg": 3.88,
    "enalapril_5mg": 3.70,
    "furosemide_40mg": 0.91,
    "spironolactone_50mg": 4.37,
    "dexamethasone_0.5mg": 0.22,
    "salbutamol_4mg": 0.21,
    "montelukast_4mg": 10.03,
    "isoniazid_300mg": 1.29,
    "rifampicin_600mg": 11.36,
    "pyrazinamide_1000mg": 10.53,
    "ethambutol_600mg": 4.08,
    "insulin_glargine_100iu": 244.14,
    "diazepam_5mg": 1.63,
    "carbamazepine_200mg": 2.40,
    "levetiracetam_250mg": 6.30,
    "tramadol_injection_50mg": 11.78,
    "chloroquine_150mg": 1.17,
    "phenytoin_300mg": 5.48,
    "ferrous_folic_acid": 0.28,
}

# ============================================================================
# CGHS PROCEDURE RATES — reference benchmark (NOT a legal cap)
# Key: lowercase procedure name.
# Value: dict of rates.  Two schemas coexist:
#   {"nabh": x, "non_nabh": y}            — NABH-accredited vs non-NABH hospital
#   {"metro": x, "tier_y": y, "tier_z": z} — city-tier based (orthopaedic etc.)
# ============================================================================
CGHS_PROCEDURE_RATES: Dict[str, Dict[str, float]] = {
    "appendicectomy": {"nabh": 19000, "non_nabh": 16150},
    "laparoscopic_cholecystectomy": {"nabh": 33000, "non_nabh": 28050},
    "cholecystectomy": {"nabh": 24000, "non_nabh": 20400},
    "inguinal_hernia_hernioplasty": {"nabh": 32000, "non_nabh": 27200},
    "inguinal_hernia_herniorrhaphy": {"nabh": 26000, "non_nabh": 22100},
    "exploratory_laparotomy": {"nabh": 25000, "non_nabh": 21250},
    "cabg": {"nabh": 146136, "non_nabh": 127075},
    "angioplasty_ptca": {"nabh": 92000, "non_nabh": 78200},
    "double_valve_replacement": {"nabh": 178735, "non_nabh": 155422},
    "single_valve_replacement": {"nabh": 119157, "non_nabh": 103615},
    "coronary_angiography": {"nabh": 13225, "non_nabh": 11240},
    "cardiac_catheterization": {"nabh": 13545, "non_nabh": 11510},
    "permanent_pacemaker_dual": {"nabh": 43000, "non_nabh": 36550},
    "permanent_pacemaker_single": {"nabh": 32000, "non_nabh": 27200},
    "rf_ablation": {"nabh": 96000, "non_nabh": 81600},
    "total_knee_replacement": {"metro": 152000, "tier_y": 136800, "tier_z": 121600},
    "total_hip_replacement": {"metro": 129000, "tier_y": 116100, "tier_z": 103200},
    "discectomy": {"metro": 82000, "tier_y": 73800, "tier_z": 65600},
    "spinal_fixation": {"metro": 152000, "tier_y": 136800, "tier_z": 121600},
    "normal_delivery": {"nabh": 9200, "non_nabh": 8000},
    "caesarean_section": {"nabh": 16158, "non_nabh": 14050},
    "cataract_phaco_iol": {"nabh": 12398, "non_nabh": 10781},
    "tonsillectomy": {"nabh": 5750, "non_nabh": 5000},
    "septoplasty": {"nabh": 6613, "non_nabh": 5750},
    "mri_brain": {"nabh": 3968, "non_nabh": 3450},
    "thyroidectomy_total": {"nabh": 30418, "non_nabh": 26450},
    "radical_mastectomy": {"nabh": 33063, "non_nabh": 28750},
    "simple_mastectomy": {"nabh": 14548, "non_nabh": 12650},
    "fistulectomy_high": {"nabh": 35000, "non_nabh": 29750},
    "fistulectomy_low": {"nabh": 23000, "non_nabh": 19550},
    "hemorrhoidectomy": {"nabh": 30000, "non_nabh": 25500},
    "arthroscopy_diagnostic": {"metro": 35000, "tier_y": 31500, "tier_z": 28000},
    "amputation_below_knee": {"metro": 43000, "tier_y": 38700, "tier_z": 34400},
    "amputation_above_knee": {"metro": 53000, "tier_y": 47700, "tier_z": 42400},
}

# ---------------------------------------------------------------------------
# Citation / legal-status constants
# ---------------------------------------------------------------------------
_NPPA_CITATION = "NPPA:DPCO2013"
_NPPA_LEGAL_STATUS = "legally_binding"
_NPPA_SOURCE_REF = "S.O. 1547(E)/1548(E) dated 26.03.2024, effective 01.04.2024"

_CGHS_CITATION = "CGHS:reference"
_CGHS_LEGAL_STATUS = "reference_benchmark"
_CGHS_NOTE = "CGHS is a reference benchmark, not a legal price cap"

_FUZZY_THRESHOLD = 80  # rapidfuzz WRatio score out of 100

# Valid city tiers for tier-based CGHS procedures
_VALID_TIERS = ("metro", "tier_y", "tier_z")


# ============================================================================
# Internal helpers
# ============================================================================
def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation that hurts matching."""
    if not text:
        return ""
    return " ".join(str(text).lower().strip().split())


def _fuzzy_lookup(
    query: str,
    choices: Dict[str, Any],
    threshold: int = _FUZZY_THRESHOLD,
) -> Tuple[Optional[str], float]:
    """
    Fuzzy-match *query* against the keys of *choices* using rapidfuzz WRatio.

    Underscores in keys are treated as spaces so that
    ``paracetamol_650mg`` matches ``paracetamol 650mg``.

    Returns ``(best_key, score)`` or ``(None, 0.0)`` when nothing meets the
    threshold.
    """
    if not query or not choices:
        return None, 0.0
    # Build a mapping from human-readable label → original key
    label_to_key = {k.replace("_", " "): k for k in choices}
    # fuzz.ratio (Levenshtein-based) is used instead of WRatio because WRatio
    # is too lenient with partial token overlap — e.g. "vitamin c 500mg" scored
    # 85.5 against "azithromycin injection 500mg" under WRatio (false positive).
    # fuzz.ratio correctly rejects that at 66.7 while still matching real drugs
    # at 97-100 even with minor spacing variants ("azithromycin 500 mg" → 97.3).
    result = process.extractOne(
        query,
        list(label_to_key.keys()),
        scorer=fuzz.ratio,
        score_cutoff=threshold,
    )
    if result is None:
        return None, 0.0
    label, score, _ = result
    return label_to_key[label], float(score)


def _resolve_cghs_rate(
    rate_entry: Dict[str, float],
    city_tier: str,
    nabh: bool,
) -> Tuple[float, str]:
    """
    Pick the correct CGHS rate from a rate-entry dict.

    Two schemas are supported:
      * ``{"nabh": …, "non_nabh": …}`` — selection by accreditation
      * ``{"metro": …, "tier_y": …, "tier_z": …}`` — selection by city tier

    Returns ``(rate, basis)`` where *basis* describes which key was used.
    """
    if "nabh" in rate_entry or "non_nabh" in rate_entry:
        key = "nabh" if nabh else "non_nabh"
        return float(rate_entry.get(key, rate_entry.get("non_nabh", rate_entry.get("nabh", 0.0)))), key

    # Tier-based schema
    tier = city_tier if city_tier in rate_entry else "metro"
    if tier not in rate_entry:
        # Last-resort fallback: take the first available rate
        first_key = next(iter(rate_entry))
        return float(rate_entry[first_key]), first_key
    return float(rate_entry[tier]), tier


# ============================================================================
# Public API
# ============================================================================
def check_medicine_price(
    item_name: str,
    strength: str,
    pack_size: int,
    mrp_charged: float,
    qty: int,
) -> Dict[str, Any]:
    """
    Check a bill medicine line item against the NPPA ceiling price table.

    NPPA ceiling prices are **legally binding** under DPCO 2013.  Charging
    above the ceiling is overcharging — a statutory violation.

    Args:
        item_name: Drug name as printed on the bill (e.g. ``"Paracetamol"``).
        strength:  Strength/dosage as printed (e.g. ``"650mg"``).
        pack_size: Number of units per pack (tablets per strip, vials per box).
        mrp_charged: MRP charged **per unit** in INR.
        qty:       Number of packs billed.

    Returns:
        Dict with keys (match case)::

            matched, matched_drug, ceiling_price, mrp_charged, overcharge,
            total_ceiling_price, total_mrp_charged, is_breach, match_score,
            citation, legal_status, source_ref

        Dict with keys (no match)::

            matched, note
    """
    # --- guard against malformed / empty input -------------------------------
    if not item_name or not str(item_name).strip():
        return {"matched": False, "note": "Drug not in NPPA scheduled list - cannot verify ceiling"}
    if not strength or not str(strength).strip():
        return {"matched": False, "note": "Drug not in NPPA scheduled list - cannot verify ceiling"}

    try:
        pack_size_i = int(pack_size or 0)
        qty_i = int(qty or 0)
        mrp = float(mrp_charged or 0.0)
    except (TypeError, ValueError):
        return {"matched": False, "note": "Drug not in NPPA scheduled list - cannot verify ceiling"}

    # --- fuzzy lookup --------------------------------------------------------
    query = _normalise(f"{item_name} {strength}")
    matched_key, score = _fuzzy_lookup(query, NPPA_CEILING_PRICES)

    if matched_key is None:
        return {"matched": False, "note": "Drug not in NPPA scheduled list - cannot verify ceiling"}

    ceiling_per_unit = float(NPPA_CEILING_PRICES[matched_key])
    total_ceiling_price = ceiling_per_unit * qty_i * pack_size_i
    total_mrp_charged = mrp * qty_i * pack_size_i
    is_breach = mrp > ceiling_per_unit
    overcharge_per_unit = mrp - ceiling_per_unit if is_breach else 0.0
    total_overcharge = total_mrp_charged - total_ceiling_price if is_breach else 0.0

    return {
        "matched": True,
        "matched_drug": matched_key,
        "ceiling_price": round(ceiling_per_unit, 2),
        "mrp_charged": round(mrp, 2),
        "overcharge": round(overcharge_per_unit, 2),
        "total_ceiling_price": round(total_ceiling_price, 2),
        "total_mrp_charged": round(total_mrp_charged, 2),
        "total_overcharge": round(total_overcharge, 2),
        "is_breach": is_breach,
        "match_score": round(score, 2),
        "citation": _NPPA_CITATION,
        "legal_status": _NPPA_LEGAL_STATUS,
        "source_ref": _NPPA_SOURCE_REF,
    }


def check_procedure_rate(
    procedure_name: str,
    amount_charged: float,
    city_tier: str = "metro",
    nabh: bool = True,
) -> Dict[str, Any]:
    """
    Check a bill procedure line item against the CGHS rate table.

    CGHS rates are a **reference benchmark**, NOT a legal price cap.  A charge
    above the CGHS rate is flagged as *above benchmark* for review — it is not
    a statutory violation.

    Args:
        procedure_name: Procedure name as printed on the bill.
        amount_charged: Total amount charged for the procedure in INR.
        city_tier:      ``"metro"``, ``"tier_y"``, or ``"tier_z"`` — used for
                        tier-based procedures (orthopaedic etc.).
        nabh:           ``True`` if the hospital is NABH-accredited (selects
                        the higher NABH rate for nabh/non_nabh procedures).

    Returns:
        Dict with keys (match case)::

            matched, matched_procedure, cghs_rate, amount_charged, difference,
            pct_above, is_above_benchmark, rate_basis, match_score, citation,
            legal_status, note

        Dict with keys (no match)::

            matched, note
    """
    if not procedure_name or not str(procedure_name).strip():
        return {"matched": False, "note": "Procedure not in CGHS list"}

    try:
        amount = float(amount_charged or 0.0)
    except (TypeError, ValueError):
        return {"matched": False, "note": "Procedure not in CGHS list"}

    query = _normalise(procedure_name)
    matched_key, score = _fuzzy_lookup(query, CGHS_PROCEDURE_RATES)

    if matched_key is None:
        return {"matched": False, "note": "Procedure not in CGHS list"}

    rate_entry = CGHS_PROCEDURE_RATES[matched_key]
    cghs_rate, rate_basis = _resolve_cghs_rate(rate_entry, city_tier, nabh)

    difference = amount - cghs_rate
    is_above = amount > cghs_rate
    pct_above = (difference / cghs_rate * 100.0) if cghs_rate > 0 else 0.0

    return {
        "matched": True,
        "matched_procedure": matched_key,
        "cghs_rate": round(cghs_rate, 2),
        "amount_charged": round(amount, 2),
        "difference": round(difference, 2),
        "pct_above": round(pct_above, 2),
        "is_above_benchmark": is_above,
        "rate_basis": rate_basis,
        "match_score": round(score, 2),
        "citation": _CGHS_CITATION,
        "legal_status": _CGHS_LEGAL_STATUS,
        "note": _CGHS_NOTE,
    }


def check_bill(
    line_items: List[Dict[str, Any]],
    city_tier: str = "metro",
    nabh: bool = True,
) -> Dict[str, Any]:
    """
    Run medicine and procedure price checks across every line item in a bill.

    Each line item dict must carry a ``"type"`` field:

      * ``"medicine"`` — requires keys ``item_name``, ``strength``,
        ``pack_size``, ``mrp_charged``, ``qty``.
      * ``"procedure"`` — requires keys ``procedure_name``, ``amount_charged``.

    Unknown types are returned as an error entry so the caller can see them.

    Args:
        line_items: List of line-item dicts (see above).
        city_tier:  City tier for tier-based CGHS procedures.
        nabh:       NABH accreditation flag for nabh/non_nabh procedures.

    Returns:
        Dict with keys::

            medicine_checks   — list of per-item NPPA results
            procedure_checks  — list of per-item CGHS results
            errors            — list of malformed/unrecognised items
            summary           — aggregate counts and total overcharge
    """
    medicine_checks: List[Dict[str, Any]] = []
    procedure_checks: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    if not line_items:
        return {
            "medicine_checks": [],
            "procedure_checks": [],
            "errors": [],
            "summary": {
                "total_items": 0,
                "nppa_breaches": 0,
                "cghs_above_benchmark": 0,
                "total_nppa_overcharge": 0.0,
                "total_cghs_difference": 0.0,
            },
        }

    for idx, item in enumerate(line_items):
        if not isinstance(item, dict):
            errors.append({"index": idx, "error": "Line item is not a dict"})
            continue

        item_type = str(item.get("type", "")).lower().strip()

        if item_type == "medicine":
            result = check_medicine_price(
                item_name=item.get("item_name", ""),
                strength=item.get("strength", ""),
                pack_size=item.get("pack_size", 0),
                mrp_charged=item.get("mrp_charged", 0.0),
                qty=item.get("qty", 0),
            )
            result["line_index"] = idx
            medicine_checks.append(result)

        elif item_type == "procedure":
            result = check_procedure_rate(
                procedure_name=item.get("procedure_name", ""),
                amount_charged=item.get("amount_charged", 0.0),
                city_tier=city_tier,
                nabh=nabh,
            )
            result["line_index"] = idx
            procedure_checks.append(result)

        else:
            errors.append({
                "index": idx,
                "error": f"Unknown or missing 'type' field: '{item_type}'",
            })

    # --- aggregate summary ---------------------------------------------------
    nppa_breaches = sum(1 for m in medicine_checks if m.get("is_breach"))
    cghs_above = sum(1 for p in procedure_checks if p.get("is_above_benchmark"))
    total_nppa_overcharge = sum(
        m.get("total_overcharge", 0.0) for m in medicine_checks if m.get("is_breach")
    )
    total_cghs_difference = sum(
        p.get("difference", 0.0) for p in procedure_checks if p.get("is_above_benchmark")
    )

    return {
        "medicine_checks": medicine_checks,
        "procedure_checks": procedure_checks,
        "errors": errors,
        "summary": {
            "total_items": len(line_items),
            "nppa_breaches": nppa_breaches,
            "cghs_above_benchmark": cghs_above,
            "total_nppa_overcharge": round(total_nppa_overcharge, 2),
            "total_cghs_difference": round(total_cghs_difference, 2),
        },
    }