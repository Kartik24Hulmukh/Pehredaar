"""
Pehredaar — Escalation Router
==============================
Returns the statutory escalation route for claim disputes with REAL IRDAI/Ombudsman
section references, deadlines, and monetary limits.

Key correction: Insurance Ombudsman monetary limit is ₹30 LAKH (not ₹50 lakh)
per Insurance Ombudsman Rules 2017, Rule 17(3)(ii).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.citations.clause_library import get_clause, clause_exists


# Ombudsman centers by city (major Indian cities)
OMBUDSMAN_CENTERS: Dict[str, Dict[str, str]] = {
    "delhi": {"center": "New Delhi", "address": "Insurance Ombudsman, New Delhi", "states": "Delhi, NCR"},
    "mumbai": {"center": "Mumbai", "address": "Insurance Ombudsman, Mumbai", "states": "Mahashtra, Goa"},
    "chennai": {"center": "Chennai", "address": "Insurance Ombudsman, Chennai", "states": "Tamil Nadu, Puducherry"},
    "kolkata": {"center": "Kolkata", "address": "Insurance Ombudsman, Kolkata", "states": "West Bengal, Sikkim, Andaman"},
    "bangalore": {"center": "Bengaluru", "address": "Insurance Ombudsman, Bengaluru", "states": "Karnataka"},
    "bengaluru": {"center": "Bengaluru", "address": "Insurance Ombudsman, Bengaluru", "states": "Karnataka"},
    "hyderabad": {"center": "Hyderabad", "address": "Insurance Ombudsman, Hyderabad", "states": "Telangana, Andhra Pradesh"},
    "pune": {"center": "Pune", "address": "Insurance Ombudsman, Pune", "states": "Maharashtra (selected districts)"},
    "ahmedabad": {"center": "Ahmedabad", "address": "Insurance Ombudsman, Ahmedabad", "states": "Gujarat"},
    "jaipur": {"center": "Jaipur", "address": "Insurance Ombudsman, Jaipur", "states": "Rajasthan"},
    "lucknow": {"center": "Lucknow", "address": "Insurance Ombudsman, Lucknow", "states": "Uttar Pradesh"},
    "chandigarh": {"center": "Chandigarh", "address": "Insurance Ombudsman, Chandigarh", "states": "Punjab, Haryana, Himachal, J&K, Ladakh"},
    "bhopal": {"center": "Bhopal", "address": "Insurance Ombudsman, Bhopal", "states": "Madhya Pradesh, Chhattisgarh"},
    "patna": {"center": "Patna", "address": "Insurance Ombudsman, Patna", "states": "Bihar"},
    "bhubaneswar": {"center": "Bhubaneswar", "address": "Insurance Ombudsman, Bhubaneswar", "states": "Odisha"},
    "guwahati": {"center": "Guwahati", "address": "Insurance Ombudsman, Guwahati", "states": "Assam and Northeast"},
    "kochi": {"center": "Kochi", "address": "Insurance Ombudsman, Kochi", "states": "Kerala, Lakshadweep"},
    "ernakulam": {"center": "Kochi", "address": "Insurance Ombudsman, Kochi", "states": "Kerala, Lakshadweep"},
}

# Ombudsman monetary limit (₹30 LAKH — NOT ₹50 lakh)
OMBUDSMAN_MONETARY_LIMIT = 3000000


def get_escalation_route(
    reason_code: Optional[str] = None,
    claim_amount: Optional[float] = None
) -> Dict[str, Any]:
    """
    Return the statutory escalation route for a claim dispute.

    Args:
        reason_code: Optional rejection reason code for tailored advice
        claim_amount: Optional claim amount to check against Ombudsman limit

    Returns:
        Dict with escalation steps, deadlines, citations, and notes.
    """
    steps = [
        {
            "step": 1,
            "authority": "Insurer Grievance Redressal Officer (GRO)",
            "action": "Submit a written representation to the Grievance Redressal Officer of the insurer.",
            "deadline": "Insurer must respond within 15 days of submission.",
            "deadline_source": "IRDAI Master Circular on PP&GR 2024 (IRDAI/PP&GR/CIR/MISC/117/9/2024, dated 05.09.2024), Para 3(iii).6; IRDAI (Protection of Policyholders' Interests) Regulations 2017, Section 16",
            "citations": ["PPI2017:grievance", "MC2024:ppgr_noreject"],
            "key_points": [
                "Submit in writing with all supporting documents",
                "Insurer must communicate action taken + Insurance Ombudsman contact details",
                "GRO is available at the corporate office of every insurer",
                "If no response within 1 month, proceed to Step 2"
            ]
        },
        {
            "step": 2,
            "authority": "IRDAI Bima Bharosa Portal",
            "action": "File a complaint online at the IRDAI Bima Bharosa portal (formerly IGMS).",
            "url": "https://bimabharosa.irdai.gov.in",
            "when": "If the insurer does not respond within 15 days, or the response is unsatisfactory.",
            "citations": ["PPI2017:grievance"],
            "key_points": [
                "Online complaint registration system maintained by IRDAI",
                "Free service for policyholders",
                "IRDAI forwards the complaint to the insurer for resolution",
                "Can also be used to track complaint status"
            ]
        },
        {
            "step": 3,
            "authority": "Insurance Ombudsman",
            "action": "File a written complaint to the Insurance Ombudsman with territorial jurisdiction over your location.",
            "monetary_limit": f"₹{OMBUDSMAN_MONETARY_LIMIT // 100000} lakh (₹30,00,000)",
            "monetary_limit_source": "Insurance Ombudsman Rules 2017, Rule 17(3)(ii): 'not award compensation exceeding rupees thirty lakhs'",
            "deadline": "File within 1 year of the insurer's final reply.",
            "deadline_source": "Insurance Ombudsman Rules 2017, Rule 14(3)(b)",
            "citations": ["OMB2017:filing", "OMB2017:award"],
            "key_points": [
                f"Monetary limit: ₹{OMBUDSMAN_MONETARY_LIMIT // 100000} lakh (including relevant expenses)",
                "Must first make written representation to insurer (Step 1) before approaching Ombudsman",
                "Ombudsman must pass award within 3 months of receiving all requirements (Rule 17(4))",
                "Award is BINDING on insurers (Rule 17(8))",
                "Insurer must comply within 30 days of award (Rule 17(6))",
                "Ombudsman empowered to condone delay in filing (Rule 14(4))",
                "Cannot approach Ombudsman if matter is already before a court/consumer forum",
                "Complaint must be in writing, signed, with supporting documents"
            ]
        },
        {
            "step": 4,
            "authority": "Consumer Commission / Civil Court",
            "action": "File a complaint with the Consumer Disputes Redressal Commission or a civil court.",
            "when": "Last resort, if Ombudsman award is unsatisfactory or claim exceeds Ombudsman monetary limit.",
            "citations": [],
            "key_points": [
                "Cannot approach both Ombudsman and Consumer Commission simultaneously",
                "Consumer commission has higher monetary limits",
                "May require legal representation",
                "Time limits apply under the Consumer Protection Act 2019"
            ]
        }
    ]

    # Add notes based on claim amount
    notes = []
    if claim_amount is not None:
        if claim_amount > OMBUDSMAN_MONETARY_LIMIT:
            notes.append(
                f"⚠️ Your claim amount (₹{claim_amount:,.0f}) exceeds the Insurance Ombudsman's "
                f"monetary limit of ₹{OMBUDSMAN_MONETARY_LIMIT // 100000} lakh. The Ombudsman can "
                f"only award up to ₹{OMBUDSMAN_MONETARY_LIMIT // 100000} lakh. For the excess amount, "
                f"you may need to approach the Consumer Commission (Step 4)."
            )
        else:
            notes.append(
                f"✅ Your claim amount (₹{claim_amount:,.0f}) is within the Insurance Ombudsman's "
                f"monetary limit of ₹{OMBUDSMAN_MONETARY_LIMIT // 100000} lakh. You can approach "
                f"the Ombudsman directly (after Step 1)."
            )

    # Add reason-specific notes
    if reason_code:
        reason_notes = {
            "FRAUD_MISREP": "⚠️ Fraud allegations are serious. The insurer must prove 'established fraud.' Consider seeking independent legal counsel before filing the representation.",
            "PED_NONDISCLOSURE": "💡 Check if your policy has crossed 60 months of continuous coverage (moratorium period). If so, the claim cannot be contested except for established fraud.",
            "CASHLESS_DENIED": "💡 Denial of cashless facility is NOT a claim rejection. You can still file a reimbursement claim with all documents.",
            "LATE_INTIMATION": "💡 IRDAI has directed that claims cannot be rejected solely for delayed intimation if the delay was for genuine reasons beyond your control.",
            "DOCUMENTATION_TECHNICAL": "💡 A claim cannot be finally rejected for want of documents if the deficiency is curable. Submit the missing documents and request processing.",
        }
        if reason_code in reason_notes:
            notes.append(reason_notes[reason_code])

    notes.append(
        "📋 Always keep copies of all correspondence and documents. "
        "Send communications via registered post or email with acknowledgment."
    )

    return {
        "escalation_steps": steps,
        "ombudsman_monetary_limit": OMBUDSMAN_MONETARY_LIMIT,
        "notes": notes,
        "disclaimer": "Informational only, not legal or insurance advice. Please consult a licensed insurance advisor or the Insurance Ombudsman for professional guidance."
    }


def get_ombudsman_jurisdiction(city: str) -> Dict[str, Any]:
    """
    Get the Insurance Ombudsman center for a given city.

    Args:
        city: City name (case-insensitive)

    Returns:
        Dict with center details or a note to contact IRDAI.
    """
    city_lower = city.lower().strip()

    # Direct lookup
    if city_lower in OMBUDSMAN_CENTERS:
        center = OMBUDSMAN_CENTERS[city_lower]
        return {
            "city": city,
            "ombudsman_center": center["center"],
            "address": center["address"],
            "jurisdiction": center["states"],
            "note": "File your complaint at this Ombudsman center. Check the IRDAI website for exact address and contact details.",
            "url": "https://irdai.gov.in"
        }

    # Try partial match
    for key, center in OMBUDSMAN_CENTERS.items():
        if key in city_lower or city_lower in key:
            return {
                "city": city,
                "ombudsman_center": center["center"],
                "address": center["address"],
                "jurisdiction": center["states"],
                "note": "File your complaint at this Ombudsman center. Check the IRDAI website for exact address and contact details.",
                "url": "https://irdai.gov.in"
            }

    return {
        "city": city,
        "ombudsman_center": "Unknown",
        "note": f"Could not determine the Ombudsman center for {city}. Please visit https://irdai.gov.in to find the Ombudsman with jurisdiction over your location.",
        "url": "https://irdai.gov.in"
    }


def calculate_deadline(insurer_reply_date: str) -> Dict[str, Any]:
    """
    Calculate the Ombudsman filing deadline (1 year from insurer's final reply).

    Args:
        insurer_reply_date: Date string in 'YYYY-MM-DD' or 'DD/MM/YYYY' format

    Returns:
        Dict with deadline date, days remaining, and status.
    """
    # Parse date
    date = None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
        try:
            date = datetime.strptime(insurer_reply_date, fmt)
            break
        except ValueError:
            continue

    if date is None:
        return {
            "error": f"Could not parse date '{insurer_reply_date}'. Use YYYY-MM-DD or DD/MM/YYYY format."
        }

    deadline = date + timedelta(days=365)
    now = datetime.now()
    days_remaining = (deadline - now).days

    if days_remaining > 0:
        status = "within_deadline"
        status_message = f"You have {days_remaining} days remaining to file with the Ombudsman."
    else:
        status = "deadline_passed"
        status_message = f"The 1-year deadline has passed ({abs(days_remaining)} days ago). You may still file — the Ombudsman has the power to condone delay (Rule 14(4))."

    return {
        "insurer_reply_date": date.strftime("%d %B %Y"),
        "ombudsman_filing_deadline": deadline.strftime("%d %B %Y"),
        "days_remaining": days_remaining,
        "status": status,
        "status_message": status_message,
        "note": "The Ombudsman may condone delay if you can show sufficient cause (Insurance Ombudsman Rules 2017, Rule 14(4))."
    }