"""
Pehredaar — Before You Sign Sheet Generator
============================================
Generates a 1-page pre-signature advisory sheet for patients at the discharge
desk. The sheet empowers patients to ask informed questions *before* signing
the final bill, potentially preventing avoidable out-of-pocket costs from
proportionate deductions, non-payable charges, NPPA ceiling breaches, and
CGHS benchmark deviations.

Tone: polite, non-accusatory ("possible error", "please review", never "fraud").
Every citation references a real clause id from the curated clause library —
no fabricated references.

Public API:
    generate_sheet(exposure, flags, context)        -> dict
    generate_desk_script(exposure, flags, context)  -> str
    format_sheet_for_whatsapp(sheet)                -> str
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Clause-library import — with exec()-harness fallback
# ---------------------------------------------------------------------------
try:
    from pehredaar_pkg.citations.clause_library import (
        clause_exists,
        get_clause,
        get_clause_summary,
        CLAUSE_LIBRARY,
    )
except ImportError:  # pragma: no cover — exercised by exec-based test harness
    if "clause_exists" not in globals() or "CLAUSE_LIBRARY" not in globals():
        raise
    # clause_library already in globals from prior exec() — nothing to do.


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADER_TEXT: str = "⚠️ BEFORE YOU SIGN — Review These Flags"

DISCLAIMER: str = (
    "Informational only, not legal or insurance advice. "
    "Estimates based on policy terms and bill data. "
    "Verify with billing desk."
)

# IRDAI proportionate-deduction circular reference (used in desk script)
_IRDAI_PROP_REF: str = "IRDAI/HLT/REG/CIR/151/06/2020"

# IRDAI standardization circular reference (used in desk script for non-payables)
_IRDAI_STD_REF: str = "IRDAI/HLT/REG/CIR/193/07/2020"

# Threshold for detailed vs. simpler desk script
_DETAILED_SCRIPT_THRESHOLD: int = 10_000

# Valid flag types
_VALID_FLAG_TYPES: frozenset[str] = frozenset({
    "proportionate_deduction",
    "non_payable",
    "nppa_breach",
    "cghs_benchmark",
    "duplicate",
    "arithmetic",
})

# Default citations per flag type (used when a flag doesn't carry its own)
_DEFAULT_CITATIONS: Dict[str, str] = {
    "proportionate_deduction": "MC2024:proportionate",
    "non_payable": "MC2024:nonpayable",
    "nppa_breach": "NPPA:DPCO2013",
    "cghs_benchmark": "CGHS:reference",
    "duplicate": "MC2024:nonpayable",
    "arithmetic": "MC2024:nonpayable",
}

# Human-readable labels per flag type
_FLAG_TYPE_LABELS: Dict[str, str] = {
    "proportionate_deduction": "Proportionate Deduction",
    "non_payable": "Non-Payable Item",
    "nppa_breach": "NPPA Price Ceiling Breach",
    "cghs_benchmark": "CGHS Benchmark Deviation",
    "duplicate": "Duplicate Charge",
    "arithmetic": "Arithmetic Error",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _format_rupees(amount: Any) -> str:
    """Format an amount as an Indian-rupee string with thousands separators."""
    amt = _safe_int(amount, 0)
    # Indian numbering: group as 3,2,2,... from right
    negative = amt < 0
    amt_abs = abs(amt)
    s = str(amt_abs)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        # Insert commas every 2 digits from the right of the rest
        parts: List[str] = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    prefix = "-" if negative else ""
    return f"₹{prefix}{grouped}"


def _validate_citation(citation: Optional[str], flag_type: str) -> str:
    """
    Validate a citation id against the clause library.
    If the citation is missing or invalid, fall back to the default for the
    flag type. If no default exists either, return an empty string rather
    than fabricate a reference.
    """
    if citation and clause_exists(citation):
        return citation
    default = _DEFAULT_CITATIONS.get(flag_type, "")
    if default and clause_exists(default):
        return default
    return ""


def _get_citation_display(citation_id: str) -> str:
    """Return a human-readable citation string from the clause library."""
    if not citation_id:
        return "(citation pending)"
    summary = get_clause_summary(citation_id)
    if "error" in summary:
        return citation_id
    ref = summary.get("reference", "")
    date = summary.get("date", "")
    title = summary.get("title", "")
    parts: List[str] = []
    if ref:
        parts.append(ref)
    if date:
        parts.append(f"dated {date}")
    if title:
        parts.append(f"— {title}")
    return " ".join(parts) if parts else citation_id


def _normalize_flag(flag: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw flag dict into a consistent structure with all expected
    keys: type, description, amount, citation, confidence.
    """
    flag_type = str(flag.get("type", "unknown")).strip()
    if flag_type not in _VALID_FLAG_TYPES:
        # Keep it but mark as unknown — don't drop the flag
        pass

    citation = _validate_citation(flag.get("citation"), flag_type)
    amount = _safe_int(flag.get("amount", 0), 0)
    confidence = str(flag.get("confidence", "medium")).strip().lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    description = str(flag.get("description", "")).strip()
    if not description:
        label = _FLAG_TYPE_LABELS.get(flag_type, "Issue detected")
        description = f"{label} — details pending review"

    # Start with the standard keys, then preserve any extra keys from the
    # original flag (e.g. item_name, procedure_name, medicine_name) so the
    # desk-script question builders can reference them.
    normalized: Dict[str, Any] = {
        "type": flag_type,
        "description": description,
        "amount": amount,
        "citation": citation,
        "confidence": confidence,
    }
    _standard_keys = {"type", "description", "amount", "citation", "confidence"}
    for k, v in flag.items():
        if k not in _standard_keys:
            normalized[k] = v

    return normalized


def _compute_breakdown(exposure: int, context: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """
    Compute the out-of-pocket breakdown into room_excess and proportionate_hit.

    room_excess   = (actual_room_rent - room_cap) * days   (capped at >= 0)
    proportionate_hit = exposure - room_excess              (capped at >= 0)

    Falls back gracefully when context is missing or incomplete.
    """
    ctx = context or {}
    room_cap = _safe_int(ctx.get("room_cap"), 0)
    actual_room = _safe_int(ctx.get("actual_room_rent") or ctx.get("actual_room"), 0)
    days = _safe_int(ctx.get("days"), 0)

    room_excess = 0
    if room_cap > 0 and actual_room > 0 and days > 0:
        room_excess = max(0, (actual_room - room_cap) * days)

    proportionate_hit = max(0, exposure - room_excess)

    return {
        "room_excess": room_excess,
        "proportionate_hit": proportionate_hit,
        "total": exposure,
    }


# ---------------------------------------------------------------------------
# Desk Query Script Generation
# ---------------------------------------------------------------------------

def _build_proportionate_question(
    flags: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]],
) -> str:
    """Build the proportionate-deduction question for the desk script."""
    ctx = context or {}
    room_cap = _safe_int(ctx.get("room_cap"), 0)
    actual_room = _safe_int(ctx.get("actual_room_rent") or ctx.get("actual_room"), 0)

    cap_str = _format_rupees(room_cap) if room_cap else "my policy cap"
    room_str = _format_rupees(actual_room) if actual_room else "the assigned room"

    return (
        f"I notice my room rent of {room_str} exceeds my policy cap of {cap_str}. "
        f"Can you confirm whether proportionate deduction has been applied to "
        f"medicines, implants, and diagnostics? "
        f"Per IRDAI guidelines ({_IRDAI_PROP_REF}), these should not be "
        f"proportionately reduced."
    )


def _build_non_payable_question(flags: List[Dict[str, Any]]) -> str:
    """Build the non-payable items question for the desk script."""
    # Collect item names from non_payable flags
    items: List[str] = []
    for f in flags:
        if f.get("type") == "non_payable":
            desc = f.get("description", "")
            # Try to extract item name from description or use item_name field
            item_name = f.get("item_name", "")
            if item_name:
                items.append(str(item_name))
            elif desc:
                items.append(desc)
    if not items:
        items_list = "certain items"
    else:
        # Limit to first 5 items for brevity
        shown = items[:5]
        items_list = ", ".join(shown)
        if len(items) > 5:
            items_list += f", and {len(items) - 5} more"

    return (
        f"I see charges for {items_list}. "
        f"Per IRDAI Master Circular on Standardization ({_IRDAI_STD_REF}), "
        f"these should be subsumed into room/procedure charges. "
        f"Can you review?"
    )


def _build_nppa_question(flags: List[Dict[str, Any]]) -> str:
    """Build the NPPA ceiling breach question for the desk script."""
    medicines: List[str] = []
    for f in flags:
        if f.get("type") == "nppa_breach":
            item_name = f.get("item_name") or f.get("medicine_name", "")
            if item_name:
                medicines.append(str(item_name))
            else:
                desc = f.get("description", "")
                if desc:
                    medicines.append(desc)
    if not medicines:
        med_str = "a medicine"
    else:
        shown = medicines[:5]
        med_str = ", ".join(shown)
        if len(medicines) > 5:
            med_str += f", and {len(medicines) - 5} more"

    return (
        f"I believe the MRP charged for {med_str} exceeds the NPPA ceiling price. "
        f"Can you verify?"
    )


def _build_cghs_question(flags: List[Dict[str, Any]]) -> str:
    """Build the CGHS benchmark deviation question for the desk script."""
    procedures: List[str] = []
    for f in flags:
        if f.get("type") == "cghs_benchmark":
            proc_name = f.get("procedure_name") or f.get("item_name", "")
            if proc_name:
                procedures.append(str(proc_name))
            else:
                desc = f.get("description", "")
                if desc:
                    procedures.append(desc)
    if not procedures:
        proc_str = "a procedure"
    else:
        shown = procedures[:5]
        proc_str = ", ".join(shown)
        if len(procedures) > 5:
            proc_str += f", and {len(procedures) - 5} more"

    return (
        f"The charge for {proc_str} is significantly above the CGHS benchmark rate. "
        f"Can you provide a justification?"
    )


def _build_duplicate_question(flags: List[Dict[str, Any]]) -> str:
    """Build the duplicate charge question for the desk script."""
    items: List[str] = []
    for f in flags:
        if f.get("type") == "duplicate":
            item_name = f.get("item_name", "")
            desc = f.get("description", "")
            if item_name:
                items.append(str(item_name))
            elif desc:
                items.append(desc)
    if items:
        shown = items[:5]
        items_str = ", ".join(shown)
        if len(items) > 5:
            items_str += f", and {len(items) - 5} more"
        return (
            f"I notice possible duplicate charges for {items_str}. "
            f"Can you please review and confirm these are not billed twice?"
        )
    return (
        "I notice some charges may have been billed more than once. "
        "Can you please review for possible duplicate entries?"
    )


def _build_arithmetic_question(flags: List[Dict[str, Any]]) -> str:
    """Build the arithmetic error question for the desk script."""
    details: List[str] = []
    for f in flags:
        if f.get("type") == "arithmetic":
            desc = f.get("description", "")
            if desc:
                details.append(desc)
    if details:
        detail_str = "; ".join(details[:3])
        return (
            f"I'd like to request a recalculation of the bill total. "
            f"I notice a possible arithmetic discrepancy: {detail_str}. "
            f"Can you please verify the totals?"
        )
    return (
        "I'd like to request a recalculation of the bill total to verify "
        "all arithmetic is correct. Can you please review the subtotals?"
    )


def generate_desk_script(
    exposure: int,
    flags: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a polite, ready-to-read desk query script as a plain string.

    The script is tailored to the specific flags present and the exposure
    level. Tone is always non-accusatory — uses 'possible error', 'please
    review', and never 'fraud'.

    Args:
        exposure: Total rupee out-of-pocket exposure.
        flags:    List of flag dicts from the rule engines.
        context:  Optional dict with policy_name, room_cap, actual_room_rent,
                  days, bill_total.

    Returns:
        A multi-line string the patient can read aloud at the billing desk.
    """
    ctx = context or {}
    normalized = [_normalize_flag(f) for f in (flags or [])]
    flag_types = {f["type"] for f in normalized}

    lines: List[str] = []

    # --- Opening greeting ---
    policy_name = ctx.get("policy_name", "")
    policy_intro = f" under my {policy_name} policy" if policy_name else ""
    lines.append(
        f"Hello, before I sign the final bill, I'd like to clarify a few "
        f"items{policy_intro}. My estimated out-of-pocket exposure is "
        f"{_format_rupees(exposure)}, and I'd appreciate your help reviewing "
        f"the following."
    )
    lines.append("")

    # --- High-exposure detailed script ---
    if exposure > _DETAILED_SCRIPT_THRESHOLD:
        lines.append(
            "Since the amount is significant, I'd like to go through each "
            "point carefully:"
        )
        lines.append("")

        # Proportionate deduction question
        if "proportionate_deduction" in flag_types:
            lines.append("• " + _build_proportionate_question(normalized, ctx))
            lines.append("")

        # Non-payable items question
        if "non_payable" in flag_types:
            lines.append("• " + _build_non_payable_question(normalized))
            lines.append("")

        # NPPA breach question
        if "nppa_breach" in flag_types:
            lines.append("• " + _build_nppa_question(normalized))
            lines.append("")

        # CGHS benchmark question
        if "cghs_benchmark" in flag_types:
            lines.append("• " + _build_cghs_question(normalized))
            lines.append("")

        # Duplicate charge question
        if "duplicate" in flag_types:
            lines.append("• " + _build_duplicate_question(normalized))
            lines.append("")

        # Arithmetic error question
        if "arithmetic" in flag_types:
            lines.append("• " + _build_arithmetic_question(normalized))
            lines.append("")

        # If no specific flag types matched, add a general verification request
        if not flag_types:
            lines.append(
                "• Can you please walk me through the proportionate deduction "
                f"calculation? I want to ensure that fixed items like medicines, "
                f"implants, and diagnostics were not proportionately reduced, "
                f"as per IRDAI guidelines ({_IRDAI_PROP_REF})."
            )
            lines.append("")
            lines.append(
                "• Can you also confirm that all non-payable items have been "
                f"subsumed into room and procedure charges per IRDAI "
                f"standardization ({_IRDAI_STD_REF})?"
            )
            lines.append("")

    # --- Low-exposure simpler script ---
    else:
        lines.append(
            "I'd like to verify a couple of calculations before signing:"
        )
        lines.append("")

        if "proportionate_deduction" in flag_types:
            lines.append("• " + _build_proportionate_question(normalized, ctx))
            lines.append("")

        if "non_payable" in flag_types:
            lines.append("• " + _build_non_payable_question(normalized))
            lines.append("")

        if "nppa_breach" in flag_types:
            lines.append("• " + _build_nppa_question(normalized))
            lines.append("")

        if "cghs_benchmark" in flag_types:
            lines.append("• " + _build_cghs_question(normalized))
            lines.append("")

        if "duplicate" in flag_types:
            lines.append("• " + _build_duplicate_question(normalized))
            lines.append("")

        if "arithmetic" in flag_types:
            lines.append("• " + _build_arithmetic_question(normalized))
            lines.append("")

        if not flag_types:
            lines.append(
                "• Can you please verify the total calculation and confirm "
                "all charges are correct?"
            )
            lines.append("")

    # --- Closing ---
    lines.append(
        "Thank you for your patience. I'm not disputing the charges — I just "
        "want to make sure everything is accurate before I sign. Could you "
        "also provide written confirmation for any corrections made?"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sheet Generation
# ---------------------------------------------------------------------------

def _build_top_flags(
    flags: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Sort flags by financial impact (amount descending) and return the top
    *limit* entries with enriched display fields.
    """
    normalized = [_normalize_flag(f) for f in (flags or [])]
    # Sort by amount descending, then by confidence (high > medium > low)
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    sorted_flags = sorted(
        normalized,
        key=lambda f: (-f["amount"], confidence_order.get(f["confidence"], 1)),
    )
    top = sorted_flags[:limit]

    result: List[Dict[str, Any]] = []
    for f in top:
        citation_display = _get_citation_display(f["citation"])
        result.append({
            "type": f["type"],
            "type_label": _FLAG_TYPE_LABELS.get(f["type"], f["type"]),
            "description": f["description"],
            "amount": f["amount"],
            "amount_display": _format_rupees(f["amount"]),
            "citation": f["citation"],
            "citation_display": citation_display,
            "confidence": f["confidence"],
        })
    return result


def _build_what_to_ask_in_writing(
    flags: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]],
) -> List[str]:
    """
    Build the list of things to get written confirmation for, tailored to
    the flags present.
    """
    ctx = context or {}
    normalized = [_normalize_flag(f) for f in (flags or [])]
    flag_types = {f["type"] for f in normalized}

    items: List[str] = []

    if "proportionate_deduction" in flag_types:
        items.append(
            "Written confirmation that proportionate deduction was NOT applied "
            "to medicines, implants, consumables, and diagnostics (fixed items "
            f"per {_IRDAI_PROP_REF})"
        )
        items.append(
            "Itemized breakdown of the proportionate deduction calculation "
            "(factor, variable charges, fixed charges)"
        )

    if "non_payable" in flag_types:
        items.append(
            "Written confirmation that non-payable/optional items have been "
            f"subsumed into room and procedure charges per {_IRDAI_STD_REF}"
        )

    if "nppa_breach" in flag_types:
        items.append(
            "Written confirmation of the MRP and NPPA ceiling price for each "
            "flagged medicine"
        )

    if "cghs_benchmark" in flag_types:
        items.append(
            "Written justification for any procedure charge significantly "
            "above the CGHS benchmark rate"
        )

    if "duplicate" in flag_types:
        items.append(
            "Written confirmation that no line item has been charged more "
            "than once"
        )

    if "arithmetic" in flag_types:
        items.append(
            "A revised, recalculated bill total with corrected arithmetic"
        )

    # Always include the room cap confirmation if context has room info
    room_cap = _safe_int(ctx.get("room_cap"), 0)
    if room_cap > 0:
        items.append(
            f"Written confirmation of the room category assigned and that it "
            f"is at or under your policy cap of {_format_rupees(room_cap)}/day"
        )

    # Fallback if no flags at all
    if not items:
        items.append(
            "Written confirmation of the final bill total and that all "
            "charges have been verified"
        )

    return items


def _build_your_options(context: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build the 'YOUR OPTIONS' section with the four standard options.
    """
    ctx = context or {}
    room_cap = _safe_int(ctx.get("room_cap"), 0)
    cap_str = _format_rupees(room_cap) if room_cap else "your policy cap"

    return [
        {
            "label": "a",
            "text": f"Ask for a room at/under your policy cap ({cap_str}/day) "
                    f"to avoid proportionate deduction entirely",
        },
        {
            "label": "b",
            "text": "Get written confirmation that no proportionate deduction "
                    "has been applied to fixed items (medicines, implants, "
                    "diagnostics)",
        },
        {
            "label": "c",
            "text": "Ask for an itemized breakdown of the proportionate "
                    "deduction calculation — factor, variable charges, and "
                    "fixed charges shown separately",
        },
        {
            "label": "d",
            "text": "Proceed knowingly — sign the bill understanding the "
                    "estimated out-of-pocket exposure",
        },
    ]


def generate_sheet(
    exposure: int,
    flags: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive 'Before You Sign' advisory sheet.

    Args:
        exposure: Total rupee out-of-pocket exposure from proportionate
                  deduction (and other rule engine outputs).
        flags:    List of flag dicts from the rule engines. Each flag should
                  have keys: type, description, amount, citation, confidence.
                  Extra keys (item_name, procedure_name, etc.) are preserved
                  for script generation.
        context:  Optional dict with:
                    - policy_name: str
                    - room_category: str
                    - actual_room_rent: int (per day)
                    - room_cap: int (per day)
                    - days: int
                    - bill_total: int

    Returns:
        A structured dict with all sheet sections:
        header, total_exposure, top_flags, desk_query_script,
        what_to_ask_in_writing, your_options, disclaimer.
    """
    ctx = context or {}
    exposure_int = _safe_int(exposure, 0)

    # --- Compute breakdown ---
    breakdown = _compute_breakdown(exposure_int, ctx)

    # --- Top flags ---
    top_flags = _build_top_flags(flags, limit=5)

    # --- Desk query script ---
    desk_script = generate_desk_script(exposure_int, flags, ctx)

    # --- What to ask in writing ---
    written_items = _build_what_to_ask_in_writing(flags, ctx)

    # --- Your options ---
    options = _build_your_options(ctx)

    # --- Build context summary for the sheet ---
    policy_name = ctx.get("policy_name", "Not specified")
    room_category = ctx.get("room_category", "Not specified")
    actual_room = _safe_int(
        ctx.get("actual_room_rent") or ctx.get("actual_room"), 0
    )
    room_cap = _safe_int(ctx.get("room_cap"), 0)
    days = _safe_int(ctx.get("days"), 0)
    bill_total = _safe_int(ctx.get("bill_total"), 0)

    context_summary = {
        "policy_name": policy_name,
        "room_category": room_category,
        "actual_room_rent": actual_room,
        "actual_room_rent_display": _format_rupees(actual_room),
        "room_cap": room_cap,
        "room_cap_display": _format_rupees(room_cap),
        "days": days,
        "bill_total": bill_total,
        "bill_total_display": _format_rupees(bill_total),
    }

    sheet: Dict[str, Any] = {
        "header": HEADER_TEXT,
        "total_exposure": {
            "amount": exposure_int,
            "amount_display": _format_rupees(exposure_int),
            "breakdown": {
                "room_excess": breakdown["room_excess"],
                "room_excess_display": _format_rupees(breakdown["room_excess"]),
                "proportionate_hit": breakdown["proportionate_hit"],
                "proportionate_hit_display": _format_rupees(
                    breakdown["proportionate_hit"]
                ),
                "total": breakdown["total"],
                "total_display": _format_rupees(breakdown["total"]),
            },
        },
        "context": context_summary,
        "top_flags": top_flags,
        "desk_query_script": desk_script,
        "what_to_ask_in_writing": written_items,
        "your_options": options,
        "disclaimer": DISCLAIMER,
    }

    return sheet


# ---------------------------------------------------------------------------
# WhatsApp Formatting
# ---------------------------------------------------------------------------

def format_sheet_for_whatsapp(sheet: Dict[str, Any]) -> str:
    """
    Format the sheet as a WhatsApp-friendly text message.

    Uses emojis (⚠️, 💰, 📋, ✅) and line breaks for readability on mobile.
    Keeps the message concise but complete — all sections are included.

    Args:
        sheet: The dict returned by generate_sheet().

    Returns:
        A WhatsApp-formatted string.
    """
    if not sheet or not isinstance(sheet, dict):
        return "⚠️ *Before You Sign*\n\nNo sheet data available."

    lines: List[str] = []

    # --- Header ---
    lines.append(sheet.get("header", HEADER_TEXT))
    lines.append("")

    # --- Total Exposure ---
    total = sheet.get("total_exposure", {})
    amount_display = total.get("amount_display", "")
    breakdown = total.get("breakdown", {})

    lines.append(f"💰 *Total Out-of-Pocket Exposure: {amount_display}*")
    if breakdown:
        room_ex = breakdown.get("room_excess_display", "")
        prop_hit = breakdown.get("proportionate_hit_display", "")
        if room_ex:
            lines.append(f"   • Room excess: {room_ex}")
        if prop_hit:
            lines.append(f"   • Proportionate hit: {prop_hit}")
    lines.append("")

    # --- Context summary (compact) ---
    ctx = sheet.get("context", {})
    if ctx:
        policy = ctx.get("policy_name", "")
        if policy and policy != "Not specified":
            lines.append(f"📋 Policy: {policy}")
        room_cap = ctx.get("room_cap_display", "")
        actual_room = ctx.get("actual_room_rent_display", "")
        days = ctx.get("days", 0)
        if room_cap and room_cap != "₹0":
            lines.append(f"📋 Room cap: {room_cap}/day")
        if actual_room and actual_room != "₹0":
            lines.append(f"📋 Actual room: {actual_room}/day × {days} days")
        bill_total = ctx.get("bill_total_display", "")
        if bill_total and bill_total != "₹0":
            lines.append(f"📋 Bill total: {bill_total}")
        lines.append("")

    # --- Top Flags ---
    top_flags = sheet.get("top_flags", [])
    if top_flags:
        lines.append("📋 *Top Flags:*")
        for i, f in enumerate(top_flags, 1):
            type_label = f.get("type_label", f.get("type", ""))
            amount_str = f.get("amount_display", "")
            desc = f.get("description", "")
            confidence = f.get("confidence", "")
            lines.append(f"   {i}. *{type_label}* — {amount_str}")
            lines.append(f"      {desc}")
            if confidence:
                lines.append(f"      Confidence: {confidence}")
        lines.append("")

    # --- Desk Query Script ---
    script = sheet.get("desk_query_script", "")
    if script:
        lines.append("✅ *What to say at the billing desk:*")
        lines.append(script)
        lines.append("")

    # --- What to Ask in Writing ---
    written = sheet.get("what_to_ask_in_writing", [])
    if written:
        lines.append("✅ *Get written confirmation for:*")
        for i, item in enumerate(written, 1):
            lines.append(f"   {i}. {item}")
        lines.append("")

    # --- Your Options ---
    options = sheet.get("your_options", [])
    if options:
        lines.append("✅ *Your options:*")
        for opt in options:
            label = opt.get("label", "")
            text = opt.get("text", "")
            lines.append(f"   ({label}) {text}")
        lines.append("")

    # --- Disclaimer ---
    lines.append(f"⚠️ {DISCLAIMER}")

    return "\n".join(lines)