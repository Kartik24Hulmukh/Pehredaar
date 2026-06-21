"""
Pehredaar — Main FastAPI Application
======================================
End-to-end API for Discharge Defender + ClaimBack.

Endpoints:
  GET  /                          — Health check
  GET  /health                    — Detailed health status
  GET  /policies                  — List available policy plans
  POST /defender/calculate        — Calculate proportionate deduction
  POST /defender/analyze          — Full bill analysis (deduction + non-payable + price check)
  POST /defender/before-you-sign  — Generate Before You Sign sheet
  POST /claimback/classify        — Classify a rejection letter
  POST /claimback/draft-appeal    — Draft an appeal letter
  GET  /claimback/escalation      — Get escalation route
  GET  /claimback/ombudsman       — Get Ombudsman jurisdiction
  POST /claimback/analyze         — Full claimback analysis (classify + draft + route)
  POST /ingest/bill               — Upload and parse a bill (image/PDF)
  GET  /citations                 — List all clause library citations
  POST /citations/validate        — Validate citation ids
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import sys
import tempfile
import json

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.defender.proportionate_deduction import ProportionateDeductionCalculator
from src.defender.before_you_sign import generate_sheet, generate_desk_script, format_sheet_for_whatsapp
from src.defender.policy_parser import PolicyParser, PolicyRecord
from src.rules.non_payable_detector import NonPayableDetector
from src.rules.price_check_engine import check_medicine_price, check_procedure_rate, check_bill
from src.claimback.classify import RejectionClassifier
from src.claimback.draft_appeal import draft_letter
from src.claimback.router import get_escalation_route, get_ombudsman_jurisdiction, calculate_deadline
from src.citations.clause_library import get_all_clause_ids, get_clause_summary, validate_citations, CLAUSE_LIBRARY
from src.core.pii_redaction import PIIRedactor
from src.ingest.bill_to_json import BillIngestion
from src.channels.receipt_of_justice import generate_defender_card, generate_claimback_card, format_card_for_whatsapp

app = FastAPI(
    title="Pehredaar API",
    description="Discharge Defender & ClaimBack — Protecting Indian patients' money at the discharge desk and after claim rejection.",
    version="1.0.0",
    contact={"name": "Pehredaar", "url": "https://github.com/KairoPhantom/Pehredaar"}
)

# Serve web interface
web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
if os.path.isdir(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")


# ============================================================================
# Models
# ============================================================================

class ProportionateDeductionInput(BaseModel):
    inputs: Dict[str, Any] = Field(..., description="Calculation inputs: sum_insured, room_cap_per_day, actual_room_rent_per_day, days, variable_charges, fixed_charges, etc.")


class BillAnalysisInput(BaseModel):
    policy_name: Optional[str] = Field(None, description="Policy plan name for lookup")
    policy: Optional[Dict[str, Any]] = Field(None, description="Or direct policy dict")
    bill: Dict[str, Any] = Field(..., description="Bill JSON: room_rent_per_day, days, line_items [{name, amount, category}]")
    city_tier: str = Field("metro", description="City tier for CGHS rates: metro, tier_y, tier_z")
    nabh: bool = Field(True, description="Whether hospital is NABH accredited")


class BeforeYouSignInput(BaseModel):
    exposure: int = Field(..., description="Total out-of-pocket exposure in ₹")
    flags: List[Dict[str, Any]] = Field(default_factory=list, description="List of flag dicts")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context: policy_name, room_cap, actual_room, days, bill_total")


class RejectionClassifyInput(BaseModel):
    letter_text: str = Field(..., description="The rejection/short-settlement letter text")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context: continuous_cover_months, etc.")


class DraftAppealInput(BaseModel):
    rejection_reason: str = Field(..., description="Reason code from classifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional: continuous_cover_months, recoverable_amount, claim_number, policy_number, insurer_name")


class EscalationInput(BaseModel):
    reason_code: Optional[str] = Field(None, description="Rejection reason code")
    claim_amount: Optional[float] = Field(None, description="Claim amount in ₹")


class OmbudsmanInput(BaseModel):
    city: str = Field(..., description="City name")


class DeadlineInput(BaseModel):
    insurer_reply_date: str = Field(..., description="Date of insurer's final reply (YYYY-MM-DD or DD/MM/YYYY)")


class CitationValidateInput(BaseModel):
    citation_ids: List[str] = Field(..., description="List of clause ids to validate")


class FullClaimBackInput(BaseModel):
    letter_text: str = Field(..., description="Rejection/short-settlement letter text")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional: continuous_cover_months, claim_amount, claim_number, policy_number, insurer_name")


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
def read_root():
    return {
        "service": "Pehredaar",
        "version": "1.0.0",
        "status": "operational",
        "modules": ["Discharge Defender", "ClaimBack", "Bill Ingestion", "Citation Library"],
        "endpoints": [
            "/defender/calculate", "/defender/analyze", "/defender/before-you-sign",
            "/claimback/classify", "/claimback/draft-appeal", "/claimback/analyze",
            "/claimback/escalation", "/claimback/ombudsman",
            "/ingest/bill", "/citations", "/citations/validate"
        ],
        "web_interface": "/app"
    }


@app.get("/app", response_class=HTMLResponse)
def web_interface():
    """Serve the Pehredaar web interface."""
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Web interface not found</h1>", status_code=404)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "modules": {
            "proportionate_deduction": "operational",
            "before_you_sign": "operational",
            "policy_parser": "operational",
            "non_payable_detector": "operational",
            "price_check_engine": "operational",
            "rejection_classifier": "operational",
            "appeal_drafter": "operational",
            "escalation_router": "operational",
            "pii_redaction": "operational",
            "bill_ingestion": "operational",
            "citation_library": f"{len(CLAUSE_LIBRARY)} clauses loaded"
        }
    }


@app.get("/policies")
def list_policies():
    """List all available policy plans in the lookup table."""
    try:
        plans = PolicyParser.list_plans()
        return {"success": True, "plans": plans, "count": len(plans)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/defender/calculate")
def calculate_deduction(data: ProportionateDeductionInput):
    """Calculate proportionate deduction exposure (pure deterministic math)."""
    try:
        result = ProportionateDeductionCalculator.calculate(data.inputs)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/defender/analyze")
def analyze_bill(data: BillAnalysisInput):
    """
    Full bill analysis: proportionate deduction + non-payable detection + price checks.
    """
    try:
        results = {}

        # 1. Parse policy
        if data.policy_name:
            policy = PolicyParser.parse(data.policy_name)
            policy_dict = {
                "sum_insured": data.bill.get("sum_insured", 500000),
                "room_cap_type": policy.room_cap_type,
                "room_cap_value": policy.room_cap_value,
                "icu_cap": policy.icu_cap,
                "copay_pct": policy.copay_pct,
                "disease_sublimits": policy.sublimits if policy.sublimits else None,
                "no_room_limit": policy.room_cap_type == "none",
            }
        elif data.policy:
            policy_dict = data.policy
        else:
            policy_dict = {"sum_insured": data.bill.get("sum_insured", 500000), "no_room_limit": True}

        # 2. Calculate proportionate deduction
        deduction_result = ProportionateDeductionCalculator.calculate_from_policy_and_bill(policy_dict, data.bill)
        results["proportionate_deduction"] = deduction_result

        # 3. Non-payable detection
        line_items = data.bill.get("line_items", [])
        non_payable_result = NonPayableDetector.detect(line_items)
        results["non_payable"] = {
            "total_non_payable_amount": non_payable_result.total_non_payable_amount,
            "count_by_list": non_payable_result.count_by_list,
            "flags": [f.__dict__ if hasattr(f, '__dict__') else f for f in non_payable_result.flags]
        }

        # 4. Price checks (NPPA + CGHS)
        price_results = check_bill(line_items, city_tier=data.city_tier, nabh=data.nabh)
        results["price_checks"] = price_results

        # 5. Generate flags for Before You Sign sheet
        flags = []
        if deduction_result.get("total_oop", 0) > 0:
            flags.append({
                "type": "proportionate_deduction",
                "description": f"Room rent exceeds policy cap. Estimated out-of-pocket: ₹{deduction_result['total_oop']:,.0f}",
                "amount": deduction_result["total_oop"],
                "citation": "MC2024:proportionate",
                "confidence": "high"
            })

        for f in non_payable_result.flags:
            flag_dict = f.__dict__ if hasattr(f, '__dict__') else f
            flags.append({
                "type": "non_payable",
                "description": f"{flag_dict.get('item_name', 'Item')} — {flag_dict.get('recommendation', 'non-payable')}",
                "amount": flag_dict.get("amount", 0),
                "citation": "MC2024:nonpayable",
                "confidence": "high"
            })

        for pr in price_results.get("medicine_results", []):
            if pr.get("is_breach"):
                flags.append({
                    "type": "nppa_breach",
                    "description": f"{pr.get('matched_drug', 'Medicine')} charged above NPPA ceiling price",
                    "amount": pr.get("overcharge", 0),
                    "citation": "NPPA:DPCO2013",
                    "confidence": "high"
                })

        for pr in price_results.get("procedure_results", []):
            if pr.get("matched") and pr.get("difference", 0) > 0:
                flags.append({
                    "type": "cghs_benchmark",
                    "description": f"{pr.get('matched_procedure', 'Procedure')} above CGHS benchmark (reference only)",
                    "amount": pr.get("difference", 0),
                    "citation": "CGHS:reference",
                    "confidence": "medium"
                })

        # 6. Generate Before You Sign sheet
        sheet = generate_sheet(
            exposure=int(deduction_result.get("total_oop", 0)),
            flags=flags,
            context={
                "policy_name": data.policy_name or "Your Policy",
                "room_cap": policy_dict.get("room_cap_value"),
                "actual_room": data.bill.get("room_rent_per_day", 0),
                "days": data.bill.get("days", 0),
                "bill_total": deduction_result.get("total_bill", 0)
            }
        )
        results["before_you_sign"] = sheet
        results["whatsapp_summary"] = format_sheet_for_whatsapp(sheet)

        return {"success": True, "result": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/defender/before-you-sign")
def before_you_sign(data: BeforeYouSignInput):
    """Generate a Before You Sign sheet."""
    try:
        result = generate_sheet(data.exposure, data.flags, data.context)
        whatsapp = format_sheet_for_whatsapp(result)
        return {"success": True, "result": result, "whatsapp_summary": whatsapp}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/claimback/classify")
def classify_rejection(data: RejectionClassifyInput):
    """Classify a rejection letter into the taxonomy."""
    try:
        result = RejectionClassifier.classify(data.letter_text, data.context)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/claimback/draft-appeal")
def draft_appeal_endpoint(data: DraftAppealInput):
    """Draft an appeal letter grounded in IRDAI clauses."""
    try:
        draft = draft_letter(data.rejection_reason, data.context)
        route = get_escalation_route(data.rejection_reason, data.context.get("claim_amount") if data.context else None)
        return {
            "success": True,
            "result": {
                "appeal": draft,
                "escalation_route": route
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/claimback/analyze")
def full_claimback_analysis(data: FullClaimBackInput):
    """
    Full ClaimBack analysis: classify rejection + draft appeal + escalation route.
    """
    try:
        # 1. Classify the rejection
        classification = RejectionClassifier.classify(data.letter_text, data.context)

        # 2. Draft the appeal letter
        appeal = draft_letter(classification["reason_code"], data.context)

        # 3. Get escalation route
        claim_amount = data.context.get("claim_amount") if data.context else None
        route = get_escalation_route(classification["reason_code"], claim_amount)

        return {
            "success": True,
            "result": {
                "classification": classification,
                "appeal": appeal,
                "escalation_route": route
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/claimback/escalation")
def escalation_route(reason_code: str = None, claim_amount: float = None):
    """Get the statutory escalation route."""
    try:
        route = get_escalation_route(reason_code, claim_amount)
        return {"success": True, "result": route}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/claimback/ombudsman")
def ombudsman_jurisdiction(city: str):
    """Get Insurance Ombudsman jurisdiction for a city."""
    try:
        result = get_ombudsman_jurisdiction(city)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/claimback/deadline")
def claimback_deadline(insurer_reply_date: str):
    """Calculate Ombudsman filing deadline."""
    try:
        result = calculate_deadline(insurer_reply_date)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ingest/bill")
async def ingest_bill(file: UploadFile = File(...)):
    """Upload and parse a hospital bill (image or PDF)."""
    try:
        # Save to temp file
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Ingest and parse
        result = BillIngestion.ingest_bill(tmp_path)

        # Clean up
        os.unlink(tmp_path)

        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/citations")
def list_citations():
    """List all clause library citations."""
    try:
        citations = [get_clause_summary(cid) for cid in get_all_clause_ids()]
        return {"success": True, "citations": citations, "count": len(citations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/citations/validate")
def validate_citation_ids(data: CitationValidateInput):
    """Validate that citation ids exist in the clause library (0-fabrication guardrail)."""
    try:
        result = validate_citations(data.citation_ids)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Receipt of Justice Card Endpoints
# ============================================================================

class DefenderCardInput(BaseModel):
    exposure_avoided: float = Field(..., description="Rupee amount protected")
    policy_name: Optional[str] = Field(None)
    room_cap: Optional[float] = Field(None)
    actual_room: Optional[float] = Field(None)
    days: Optional[int] = Field(None)
    bill_total: Optional[float] = Field(None)


class ClaimBackCardInput(BaseModel):
    claim_amount: float = Field(..., description="Original claim amount")
    reason_code: str = Field(..., description="Rejection reason code")
    winnability: str = Field(..., description="Winnability score")
    reversed: bool = Field(False, description="Whether claim was reversed")
    recovered_amount: Optional[float] = Field(None, description="Amount recovered if reversed")


@app.post("/card/defender")
def defender_card(data: DefenderCardInput):
    """Generate a Receipt of Justice card for a Discharge Defender case."""
    try:
        card = generate_defender_card(
            exposure_avoided=data.exposure_avoided,
            policy_name=data.policy_name,
            room_cap=data.room_cap,
            actual_room=data.actual_room,
            days=data.days,
            bill_total=data.bill_total
        )
        return {"success": True, "card": card, "whatsapp": format_card_for_whatsapp(card)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/card/claimback")
def claimback_card(data: ClaimBackCardInput):
    """Generate a Receipt of Justice card for a ClaimBack case."""
    try:
        card = generate_claimback_card(
            claim_amount=data.claim_amount,
            reason_code=data.reason_code,
            winnability=data.winnability,
            reversed=data.reversed,
            recovered_amount=data.recovered_amount
        )
        return {"success": True, "card": card, "whatsapp": format_card_for_whatsapp(card)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)