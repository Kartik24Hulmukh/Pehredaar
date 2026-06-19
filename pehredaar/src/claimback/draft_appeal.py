from typing import Dict, Any

def draft_letter(rejection_reason: str) -> Dict[str, Any]:
    """Drafts an appeal representation based on the rejection classification."""

    # Generic draft templates mapped to simplified codes
    templates = {
        "PROPORTIONATE_ON_FIXED": "Dear Grievance Officer,\nI noticed proportionate deduction was applied to fixed-price items like medicines and implants. As per IRDAI Master Circular (MC2024:proportionate), such items must not be proportionately reduced. Kindly recompute and refund the wrongly deducted amount.",
        "PED_NONDISCLOSURE": "Dear Grievance Officer,\nMy claim was rejected for PED non-disclosure. However, my policy has crossed the moratorium period of 60 months (MC2024:moratorium). As per IRDAI guidelines, the claim cannot be contested on these grounds. Please reconsider.",
        "DOCUMENTATION_TECHNICAL": "Dear Grievance Officer,\nI am submitting the required missing documentation. Please review and process the claim.",
        "UNKNOWN": "Dear Grievance Officer,\nI am appealing the recent claim rejection/short settlement. Please provide the exact clause in writing so I can respond appropriately."
    }

    # Matching simple logic
    draft = templates.get(rejection_reason, templates["UNKNOWN"])

    return {
        "draft_letter": draft,
        "disclaimer": "Informational only, not legal or insurance advice."
    }
