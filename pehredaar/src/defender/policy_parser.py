from typing import Dict, Any

def parse_policy(document_text: str) -> Dict[str, Any]:
    """Parse policy documents and sub-limits."""
    text = document_text.lower()

    room_cap = None
    if "room rent cap:" in text:
        # Simplistic parsing for demonstration
        try:
            parts = text.split("room rent cap:")[1]
            amount_str = parts.split()[0].replace("₹", "").replace(",", "")
            room_cap = int(amount_str)
        except Exception:
            pass

    return {
        "room_cap_per_day": room_cap,
        "parsed_from": "document"
    }
