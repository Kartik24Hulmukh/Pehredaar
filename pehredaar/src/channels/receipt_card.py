from typing import Dict, Any

def generate_receipt_card(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates the shareable anonymized card data."""
    # Data is anonymized before generation
    saved_amount = data.get("exposure", 0)
    flags_count = len(data.get("flags", []))

    card_text = f"Protected ₹{saved_amount} from incorrect hospital billing deductions today! Found {flags_count} actionable flags. Powered by Pehredaar."

    return {
        "image_url": "https://pehredaar.mock/card_gen.png",
        "card_text": card_text,
        "anonymized": True
    }
