from typing import Dict, Any, List

def get_escalation_route() -> List[Dict[str, Any]]:
    """Returns the statutory escalation route."""
    return [
        {
            "step": 1,
            "authority": "Insurer Grievance Redressal Officer (GRO)",
            "action": "Submit written representation.",
            "deadline": "Insurer must respond in 15 days (PPI2017)."
        },
        {
            "step": 2,
            "authority": "IRDAI Bima Bharosa Portal",
            "action": "File complaint online if unresolved or unsatisfactory.",
            "deadline": "After 15 days of no response or unsatisfactory resolution."
        },
        {
            "step": 3,
            "authority": "Insurance Ombudsman",
            "action": "File complaint for disputes up to ₹50 lakh.",
            "deadline": "File within 1 year of insurer's final reply."
        }
    ]
