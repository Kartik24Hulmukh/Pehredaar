from typing import List, Dict, Any

def get_non_payable_flags(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag non-payable items based on the IRDAI list."""
    non_payable_keywords = ["glove", "syringe", "admin", "registration", "documentation"]
    flags = []

    for item in items:
        name = item.get("canonical_name", "").lower()
        if any(kw in name for kw in non_payable_keywords):
            flags.append({
                "item": item["canonical_name"],
                "reason": "Found in IRDAI non-payable list.",
                "clause": "MC2024:nonpayable"
            })

    return flags
