"""
Pehredaar — Receipt of Justice Card Generator
===============================================
Generates a shareable, anonymized outcome card for the growth loop.
The card summarizes what Pehredaar protected/recovered — no PII, just the impact.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json


def generate_defender_card(
    exposure_avoided: float,
    policy_name: str = None,
    room_cap: float = None,
    actual_room: float = None,
    days: int = None,
    bill_total: float = None,
) -> Dict[str, Any]:
    """
    Generate a Receipt of Justice card for a Discharge Defender case.

    Args:
        exposure_avoided: The rupee amount protected (deduction avoided)
        policy_name: Optional policy name (anonymized)
        room_cap: Optional room cap
        actual_room: Optional actual room rent
        days: Optional number of days
        bill_total: Optional total bill

    Returns:
        Dict with card content for sharing.
    """
    headline = f"₹{exposure_avoided:,.0f} protected before signing"

    details = []
    if room_cap and actual_room:
        details.append(f"Room ₹{actual_room:,.0f}/day vs policy cap ₹{room_cap:,.0f}/day")
    if days:
        details.append(f"Hospital stay: {days} days")
    if bill_total:
        pct = (exposure_avoided / bill_total * 100) if bill_total > 0 else 0
        details.append(f"Bill: ₹{bill_total:,.0f} → Saved {pct:.1f}%")

    return {
        "card_type": "defender",
        "headline": headline,
        "subheadline": "Pehredaar caught a proportionate deduction before the signature",
        "details": details,
        "impact": f"₹{exposure_avoided:,.0f}",
        "timestamp": datetime.now().isoformat(),
        "anonymous": True,
        "share_text": (
            f"🛡️ Pehredaar stopped ₹{exposure_avoided:,.0f} from being taken at the discharge desk. "
            f"It caught the proportionate deduction trap BEFORE I signed. "
            f"Check yours — it's free. #Pehredaar #HealthInsurance"
        ),
        "disclaimer": "Anonymized outcome. Actual results may vary. Informational tool, not legal advice."
    }


def generate_claimback_card(
    claim_amount: float,
    reason_code: str,
    winnability: str,
    reversed: bool = False,
    recovered_amount: float = None,
) -> Dict[str, Any]:
    """
    Generate a Receipt of Justice card for a ClaimBack case.

    Args:
        claim_amount: The original claim amount
        reason_code: The rejection reason code
        winnability: The winnability score (green/amber/red)
        reversed: Whether the claim was reversed (user-reported)
        recovered_amount: Amount recovered (if reversed)

    Returns:
        Dict with card content for sharing.
    """
    if reversed and recovered_amount:
        headline = f"₹{recovered_amount:,.0f} recovered from rejected claim"
        subheadline = f"Pehredaar drafted an IRDAI-grounded appeal → claim reversed"
        impact = f"₹{recovered_amount:,.0f}"
    else:
        headline = f"₹{claim_amount:,.0f} claim — appeal drafted"
        winnability_emoji = {"green": "✅", "amber": "⚠️", "red": "🔴"}.get(winnability, "⚠️")
        subheadline = f"Rejection classified as {reason_code} → winnability: {winnability_emoji} {winnability}"
        impact = f"₹{claim_amount:,.0f}"

    return {
        "card_type": "claimback",
        "headline": headline,
        "subheadline": subheadline,
        "details": [
            f"Claim amount: ₹{claim_amount:,.0f}",
            f"Rejection reason: {reason_code}",
            f"Winnability: {winnability}",
        ],
        "impact": impact,
        "reversed": reversed,
        "timestamp": datetime.now().isoformat(),
        "anonymous": True,
        "share_text": (
            f"🛡️ Pehredaar helped me fight a rejected health insurance claim. "
            f"{'Claim reversed — ₹' + f'{recovered_amount:,.0f}' + ' recovered!' if reversed else 'Appeal drafted with exact IRDAI clauses.'} "
            f"Don't accept rejections without checking. #Pehredaar #ClaimBack"
        ),
        "disclaimer": "Anonymized outcome. Actual results may vary. Informational tool, not legal advice."
    }


def format_card_for_whatsapp(card: Dict[str, Any]) -> str:
    """Format a Receipt of Justice card as a WhatsApp-friendly message."""
    lines = [
        "🛡️ PEHREDAAR — Receipt of Justice",
        "",
        f"💰 {card['headline']}",
        f"📋 {card['subheadline']}",
        "",
    ]

    if card.get("details"):
        for detail in card["details"]:
            lines.append(f"  • {detail}")

    lines.extend([
        "",
        f"📊 Impact: {card['impact']}",
        "",
        card["share_text"],
        "",
        f"⚠️ {card['disclaimer']}",
    ])

    return "\n".join(lines)