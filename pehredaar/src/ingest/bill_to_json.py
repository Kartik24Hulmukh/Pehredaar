from typing import Dict, Any, List

def extract_bill_items(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Simulates extracting line items from a bill image using Bedrock Vision API."""
    # Stubbed fallback response
    return [
        {"canonical_name": "Consultation", "qty": 1, "unit_price": 500, "amount": 500},
        {"canonical_name": "Syringe 5ml", "qty": 2, "unit_price": 10, "amount": 20},
        {"canonical_name": "Paracetamol 500mg", "qty": 10, "unit_price": 2, "amount": 20}
    ]
