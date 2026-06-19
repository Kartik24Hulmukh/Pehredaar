from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List

from src.defender.proportionate_deduction import ProportionateDeductionCalculator
from src.defender.before_you_sign import generate_sheet
from src.defender.policy_parser import parse_policy
from src.claimback.classify import RejectionClassifier
from src.claimback.draft_appeal import draft_letter
from src.claimback.router import get_escalation_route
from src.rules.non_payable import get_non_payable_flags
from src.rules.nppa_cghs_rules import check_cghs_benchmarks
from src.ingest.pii_redact import redact_pii
from src.ingest.bill_to_json import extract_bill_items
from src.channels.whatsapp import handle_webhook
from src.channels.receipt_card import generate_receipt_card

app = FastAPI(title="Pehredaar API", description="Discharge Defender & ClaimBack Endpoints")

class ProportionateDeductionInput(BaseModel):
    inputs: Dict[str, Any]

class BeforeYouSignInput(BaseModel):
    exposure: int
    flags: List[str]

class RejectionClassifyInput(BaseModel):
    letter_text: str

class DraftAppealInput(BaseModel):
    rejection_reason: str
    clause_id: str = "UNKNOWN"

class BillItemsInput(BaseModel):
    items: List[Dict[str, Any]]

class PolicyInput(BaseModel):
    document_text: str

class WebhookPayload(BaseModel):
    payload: Dict[str, Any]

@app.get("/")
def read_root():
    return {"message": "Hello from pehredaar!"}

@app.post("/ingest/bill")
def ingest_bill(data: Dict[str, Any]):
    # Expecting raw text or image representation
    text = data.get("text", "")
    redacted_text = redact_pii(text)
    items = extract_bill_items(b"mock_bytes")
    return {"success": True, "redacted_text": redacted_text, "items": items}

@app.post("/rules/evaluate")
def evaluate_rules(data: BillItemsInput):
    non_payable = get_non_payable_flags(data.items)
    cghs = check_cghs_benchmarks(data.items)
    return {"success": True, "flags": non_payable + cghs}

@app.post("/defender/policy")
def evaluate_policy(data: PolicyInput):
    parsed = parse_policy(data.document_text)
    return {"success": True, "parsed_policy": parsed}

@app.post("/defender/calculate")
def calculate_deduction(data: ProportionateDeductionInput):
    try:
        result = ProportionateDeductionCalculator.calculate(data.inputs)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/defender/before-you-sign")
def before_you_sign(data: BeforeYouSignInput):
    try:
        result = generate_sheet(data.exposure, data.flags)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/claimback/classify")
def classify_rejection(data: RejectionClassifyInput):
    try:
        result = RejectionClassifier.classify(data.letter_text)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/claimback/draft-appeal")
def draft_appeal_endpoint(data: DraftAppealInput):
    try:
        draft = draft_letter(data.rejection_reason, data.clause_id)
        route = get_escalation_route()
        return {
            "success": True,
            "result": {
                "appeal": draft,
                "escalation_route": route
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/channels/webhook")
def channels_webhook(data: WebhookPayload):
    res = handle_webhook(data.payload)
    return {"success": True, "result": res}

@app.post("/channels/receipt")
def channels_receipt(data: BeforeYouSignInput):
    res = generate_receipt_card({"exposure": data.exposure, "flags": data.flags})
    return {"success": True, "result": res}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
