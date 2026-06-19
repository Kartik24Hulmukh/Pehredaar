from typing import Dict, Any

def handle_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates the BSP messaging webhook flow."""
    message = payload.get("message", "").lower()
    phone = payload.get("from_phone", "")

    response_text = "Welcome to Pehredaar via WhatsApp!"
    if "bill" in message:
        response_text = "Please upload your bill photo for us to extract details."
    elif "policy" in message:
        response_text = "Please tell us your policy details or upload the schedule."

    return {
        "status": "success",
        "to_phone": phone,
        "reply": response_text
    }
