import os
from typing import Dict, Any

def get_citation_text(clause_id: str) -> str:
    """Reads the verified text from the citations library."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Convert clause_id like "MC2024:proportionate" to "MC2024_proportionate.txt"
    file_name = f"{clause_id.replace(':', '_')}.txt"
    file_path = os.path.join(base_dir, "src", "citations", file_name)

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    return ""

def draft_letter(rejection_reason: str, clause_id: str = "UNKNOWN") -> Dict[str, Any]:
    """Drafts an appeal representation based on the rejection classification and citations."""

    citation_text = get_citation_text(clause_id)

    # Generic draft templates mapped to simplified codes
    templates = {
        "PROPORTIONATE_ON_FIXED": "Dear Grievance Officer,\nI noticed proportionate deduction was applied to fixed-price items like medicines and implants. As per the regulatory guidelines:\n\n\"{citation}\"\n\nKindly recompute and refund the wrongly deducted amount.",
        "PED_NONDISCLOSURE": "Dear Grievance Officer,\nMy claim was rejected for PED non-disclosure. However, my policy has crossed the moratorium period of 60 months. As per the regulatory guidelines:\n\n\"{citation}\"\n\nTherefore, the claim cannot be contested on these grounds. Please reconsider.",
        "DOCUMENTATION_TECHNICAL": "Dear Grievance Officer,\nI am submitting the required missing documentation. As per the regulatory guidelines:\n\n\"{citation}\"\n\nPlease review and process the claim.",
        "UNKNOWN": "Dear Grievance Officer,\nI am appealing the recent claim rejection/short settlement. Please provide the exact clause in writing so I can respond appropriately."
    }

    draft_template = templates.get(rejection_reason, templates["UNKNOWN"])
    draft = draft_template.replace("{citation}", citation_text) if citation_text else draft_template

    return {
        "draft_letter": draft,
        "disclaimer": "Informational only, not legal or insurance advice."
    }
