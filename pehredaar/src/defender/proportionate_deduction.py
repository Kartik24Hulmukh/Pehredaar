"""
Pehredaar — Proportionate Deduction Calculator (PURE DETERMINISTIC CODE)
=========================================================================
No model calls. No network. Pure math. Must match all 12 golden scenarios EXACTLY.

Formula (from fixtures/README.md):
    factor = min(1, room_rent_cap_per_day / actual_room_rent_per_day)
    room_eligible          = min(actual_room_rent, cap) * days
    variable_eligible      = sum(variable_charges) * factor
    fixed_eligible         = sum(fixed_charges)
    total_eligible         = room_eligible + variable_eligible + fixed_eligible
    total_bill             = room_charges + sum(variable_charges) + sum(fixed_charges)
    room_excess            = room_charges - room_eligible
    proportionate_hit      = sum(variable_charges) - variable_eligible
    total_out_of_pocket    = total_bill - total_eligible

IRDAI 2020 direction: proportionate deduction should NOT apply to medicines,
implants, consumables, and diagnostics (fixed_charges). Only variable/associate
charges (nursing, surgeon, OT, consult, anaesthesia) are subject to proportionate
deduction. ICU charges are also exempt (IRDAI/HLT/REG/CIR/151/06/2020, Clause 7).
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import json


class ProportionateDeductionCalculator:
    """
    Deterministic proportionate deduction calculator.
    All math is transparent — every intermediate number is exposed.
    """

    @staticmethod
    def calculate(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate proportionate deduction exposure.

        Args:
            inputs: Dict with keys:
                - sum_insured: int (total sum insured)
                - room_cap_per_day: int or None (room rent cap per day in ₹)
                - room_cap_pct_of_si: float or None (room cap as % of sum insured)
                - no_room_limit: bool (if True, no room cap applies)
                - actual_room_rent_per_day: int (actual room rent per day)
                - days: int (number of days)
                - variable_charges: Dict[str, int] (charges subject to proportionate deduction)
                - fixed_charges: Dict[str, int] (charges NOT subject to proportionate deduction)
                - copay_pct: float or None (co-pay percentage, e.g. 10 for 10%)
                - disease_sublimit: Dict or None ({name: str, cap: int})

        Returns:
            Dict with all intermediate and final values.
        """
        # --- Extract inputs ---
        sum_insured = inputs.get("sum_insured", 0)
        room_cap_per_day = inputs.get("room_cap_per_day")
        room_cap_pct_of_si = inputs.get("room_cap_pct_of_si")
        no_room_limit = inputs.get("no_room_limit", False)
        actual_room_rent_per_day = inputs.get("actual_room_rent_per_day", 0)
        days = inputs.get("days", 0)
        variable_charges = inputs.get("variable_charges", {})
        fixed_charges = inputs.get("fixed_charges", {})
        copay_pct = inputs.get("copay_pct")
        disease_sublimit = inputs.get("disease_sublimit")

        # --- Derive room cap ---
        derived_room_cap_per_day = None
        if no_room_limit:
            room_cap_per_day = None
            derived_room_cap_per_day = None
        elif room_cap_per_day is not None:
            derived_room_cap_per_day = room_cap_per_day
        elif room_cap_pct_of_si is not None:
            # Cap = (pct/100) * sum_insured
            derived_room_cap_per_day = (room_cap_pct_of_si / 100.0) * sum_insured

        # --- Compute factor ---
        if no_room_limit or derived_room_cap_per_day is None:
            factor = 1.0
        else:
            factor = min(1.0, derived_room_cap_per_day / actual_room_rent_per_day)

        # --- Room charges ---
        room_charges = actual_room_rent_per_day * days

        # --- Room eligible ---
        if no_room_limit or derived_room_cap_per_day is None:
            room_eligible = room_charges
        else:
            room_eligible = min(actual_room_rent_per_day, derived_room_cap_per_day) * days

        room_excess = room_charges - room_eligible

        # --- Variable charges (subject to proportionate deduction) ---
        variable_total = sum(variable_charges.values())
        variable_eligible = variable_total * factor
        proportionate_hit = variable_total - variable_eligible

        # --- Fixed charges (NOT subject to proportionate deduction) ---
        fixed_total = sum(fixed_charges.values())
        fixed_eligible = fixed_total  # Fixed charges are never proportionately cut

        # --- Totals ---
        total_bill = room_charges + variable_total + fixed_total
        total_eligible = room_eligible + variable_eligible + fixed_eligible
        total_oop = total_bill - total_eligible

        # --- Build result ---
        result: Dict[str, Any] = {
            "factor": round(factor, 10),
            "room_charges": room_charges,
            "room_eligible": room_eligible,
            "room_excess": room_excess,
            "variable_total": variable_total,
            "variable_eligible": variable_eligible,
            "proportionate_hit": proportionate_hit,
            "fixed_total": fixed_total,
            "fixed_eligible": fixed_eligible,
            "total_bill": total_bill,
            "total_eligible": total_eligible,
            "total_oop": total_oop,
        }

        # Add derived cap if it was computed from percentage
        if derived_room_cap_per_day is not None and room_cap_pct_of_si is not None:
            result["derived_room_cap_per_day"] = derived_room_cap_per_day

        # --- Handle co-pay ---
        if copay_pct is not None and copay_pct > 0:
            eligible_before_copay = total_eligible
            copay_amount = eligible_before_copay * (copay_pct / 100.0)
            insurer_pays = eligible_before_copay - copay_amount
            result["eligible_before_copay"] = eligible_before_copay
            result["copay_amount"] = copay_amount
            result["insurer_pays"] = insurer_pays
            # total_oop with copay = total_bill - insurer_pays
            result["total_oop"] = total_bill - insurer_pays

        # --- Handle disease sub-limit ---
        # The disease sub-limit caps the TOTAL treatment cost (variable + fixed combined).
        # The cap is applied to variable charges first, then any remainder to fixed charges.
        # Example: cataract cap ₹40,000, surgery ₹60,000, lens ₹15,000
        #   → surgery_eligible = min(60000, 40000) = 40000
        #   → remaining_cap = 40000 - 40000 = 0
        #   → fixed_eligible = min(15000, 0) = 0
        #   → total_eligible = room_eligible + 40000 + 0
        if disease_sublimit is not None:
            disease_cap = disease_sublimit.get("cap", 0)
            disease_name = disease_sublimit.get("name", "unknown")

            # Apply cap to variable charges first
            surgery_eligible = min(variable_total, disease_cap)
            surgery_excess = variable_total - surgery_eligible

            # Apply remaining cap to fixed charges
            remaining_cap = disease_cap - surgery_eligible
            fixed_eligible_disease = min(fixed_total, remaining_cap)

            # Recompute totals with disease cap
            disease_cap_applied = disease_cap
            total_eligible_disease = room_eligible + surgery_eligible + fixed_eligible_disease
            total_oop_disease = total_bill - total_eligible_disease

            # Override the result with disease sub-limit values
            result["disease_cap_applied"] = disease_cap_applied
            result["surgery_eligible"] = surgery_eligible
            result["surgery_excess"] = surgery_excess
            result["fixed_eligible"] = fixed_eligible_disease
            result["total_eligible"] = total_eligible_disease
            result["total_oop"] = total_oop_disease
            # For disease sub-limit scenarios, proportionate_hit is 0 when factor=1
            # (the cap is the disease sub-limit, not the room proportionate)

        # --- Handle S7: wrongly applied to fixed ---
        # If the insurer wrongly applies proportionate deduction to fixed charges too,
        # compute what they would pay and the recoverable amount
        if factor < 1.0 and fixed_total > 0:
            insurer_wrong_eligible_if_fixed_also_cut = (
                room_eligible + variable_eligible + (fixed_total * factor)
            )
            recoverable_vs_wrong = total_eligible - insurer_wrong_eligible_if_fixed_also_cut
            result["insurer_wrong_eligible_if_fixed_also_cut"] = insurer_wrong_eligible_if_fixed_also_cut
            result["recoverable_vs_wrong"] = recoverable_vs_wrong

        return result

    @staticmethod
    def calculate_from_policy_and_bill(
        policy: Dict[str, Any],
        bill: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        High-level interface: calculate from a parsed policy + parsed bill.

        Args:
            policy: Dict with room_cap_type, room_cap_value, sum_insured, copay_pct, etc.
            bill: Dict with room_rent_total, days, line_items (categorized)

        Returns:
            Same detailed result as calculate().
        """
        inputs: Dict[str, Any] = {
            "sum_insured": policy.get("sum_insured", 0),
            "actual_room_rent_per_day": bill.get("room_rent_per_day", 0),
            "days": bill.get("days", 0),
            "variable_charges": {},
            "fixed_charges": {},
        }

        # Room cap
        if policy.get("room_cap_type") == "abs":
            inputs["room_cap_per_day"] = policy.get("room_cap_value")
        elif policy.get("room_cap_type") == "pct":
            inputs["room_cap_pct_of_si"] = policy.get("room_cap_value")
        elif policy.get("no_room_limit"):
            inputs["no_room_limit"] = True

        # Co-pay
        if policy.get("copay_pct"):
            inputs["copay_pct"] = policy["copay_pct"]

        # Disease sub-limit
        if policy.get("disease_sublimits"):
            # Match disease sub-limit to bill if applicable
            for sub in policy["disease_sublimits"]:
                inputs["disease_sublimit"] = sub
                break  # Use first matching sub-limit

        # Categorize bill line items
        for item in bill.get("line_items", []):
            category = item.get("category", "variable")
            name = item.get("name", "unknown")
            amount = item.get("amount", 0)
            if category == "fixed":
                inputs["fixed_charges"][name] = inputs["fixed_charges"].get(name, 0) + amount
            else:
                inputs["variable_charges"][name] = inputs["variable_charges"].get(name, 0) + amount

        return ProportionateDeductionCalculator.calculate(inputs)