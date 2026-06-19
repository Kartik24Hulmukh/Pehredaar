from typing import Dict, Any, List

def generate_sheet(exposure: int, flags: List[str]) -> Dict[str, Any]:
    """Generates a Before You Sign sheet output."""
    script = "Hi, I noticed the proportionate deduction is very high. Can you please check if it's correctly calculated?"

    # Adding a rule: if there's high exposure or specific flags, provide more detailed script
    if exposure > 10000:
        script = f"Hi, I noticed my exposure is ₹{exposure}. Could you confirm that items like medicines and consumables were NOT subjected to proportionate deduction as per IRDAI rules?"

    return {
        "exposure": exposure,
        "flags": flags,
        "script": script,
        "disclaimer": "Informational only, not legal or insurance advice."
    }
