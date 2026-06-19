from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from src.defender.proportionate_deduction import ProportionateDeductionCalculator
from src.defender.before_you_sign import generate_sheet
from src.claimback.classify import RejectionClassifier
from src.claimback.draft_appeal import draft_letter
from src.claimback.router import get_escalation_route

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

@app.get("/")
def read_root():
    return {"message": "Hello from pehredaar!"}

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
        draft = draft_letter(data.rejection_reason)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
