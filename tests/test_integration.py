"""
Pehredaar — Integration Tests (End-to-End)
===========================================
Tests the full end-to-end workflows: Defender analysis and ClaimBack analysis.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pehredaar_pkg.defender.proportionate_deduction import ProportionateDeductionCalculator
from pehredaar_pkg.defender.before_you_sign import generate_sheet, format_sheet_for_whatsapp
from pehredaar_pkg.defender.policy_parser import PolicyParser
from pehredaar_pkg.rules.non_payable_detector import NonPayableDetector
from pehredaar_pkg.rules.price_check_engine import check_medicine_price, check_procedure_rate, check_bill
from pehredaar_pkg.claimback.classify import RejectionClassifier
from pehredaar_pkg.claimback.draft_appeal import draft_letter
from pehredaar_pkg.claimback.router import get_escalation_route, get_ombudsman_jurisdiction
from pehredaar_pkg.citations.clause_library import clause_exists, validate_citations, get_all_clause_ids
from pehredaar_pkg.core.pii_redaction import PIIRedactor


def test_end_to_end_defender():
    """Test the full Discharge Defender workflow."""
    # 1. Parse policy
    policy = PolicyParser.parse("Star Health Family Health Optima")
    assert policy.room_cap_type == "pct"

    # 2. Calculate deduction
    deduction = ProportionateDeductionCalculator.calculate({
        "sum_insured": 500000,
        "room_cap_pct_of_si": policy.room_cap_value,
        "actual_room_rent_per_day": 7500,
        "days": 3,
        "variable_charges": {"surgery": 80000, "nursing": 10000},
        "fixed_charges": {"medicines": 5000, "diagnostics": 8000}
    })
    assert deduction["factor"] < 1.0  # Should have deduction
    assert deduction["total_oop"] > 0

    # 3. Non-payable detection
    non_payable = NonPayableDetector.detect([
        {"name": "Gloves", "amount": 500},
        {"name": "Documentation Charges", "amount": 1000},
        {"name": "Surgery", "amount": 80000}
    ])
    assert non_payable.total_non_payable_amount > 0

    # 4. Generate Before You Sign sheet
    flags = [
        {"type": "proportionate_deduction", "description": "Room exceeds cap", "amount": deduction["total_oop"], "citation": "MC2024:proportionate", "confidence": "high"},
        {"type": "non_payable", "description": "Non-payable items found", "amount": non_payable.total_non_payable_amount, "citation": "MC2024:nonpayable", "confidence": "high"}
    ]
    sheet = generate_sheet(int(deduction["total_oop"]), flags)
    assert sheet["total_exposure"]["amount"] > 0
    assert "disclaimer" in sheet

    # 5. WhatsApp format
    whatsapp = format_sheet_for_whatsapp(sheet)
    assert len(whatsapp) > 0


def test_end_to_end_claimback():
    """Test the full ClaimBack workflow."""
    # 1. Classify rejection
    classification = RejectionClassifier.classify(
        "claim deducted as room rent exceeds eligible limit; "
        "proportionate deduction applied on all charges including pharmacy"
    )
    assert classification["reason_code"] == "PROPORTIONATE_ON_FIXED"
    assert classification["winnability"] == "green"

    # 2. Draft appeal
    appeal = draft_letter(classification["reason_code"], {"recoverable_amount": 60000})
    assert "draft_letter" in appeal
    assert appeal["citations_valid"] is True
    assert "IRDAI" in appeal["draft_letter"]

    # 3. Get escalation route
    route = get_escalation_route(classification["reason_code"])
    assert len(route["escalation_steps"]) == 4
    assert route["ombudsman_monetary_limit"] == 3000000

    # 4. Validate all citations used
    cited_ids = [classification["clause"], appeal["clause_id"]]
    for step in route["escalation_steps"]:
        cited_ids.extend(step.get("citations", []))
    validation = validate_citations(cited_ids)
    assert validation["valid"] is True


def test_pii_redaction():
    """Test PII redaction."""
    text = "Patient: Ramesh Kumar, UHID: 123456, Phone: +919876543210, Policy: ABC123456789"
    result = PIIRedactor.redact_text(text)
    assert "Ramesh" not in result["redacted_text"]
    assert "9876543210" not in result["redacted_text"]
    assert len(result["redactions"]) > 0


def test_nppa_price_check():
    """Test NPPA ceiling price check."""
    result = check_medicine_price("Paracetamol", "650mg", 10, 5.0, 2)
    assert result["matched"] is True
    assert result["is_breach"] is True
    assert result["ceiling_price"] == 2.01


def test_cghs_price_check():
    """Test CGHS procedure rate check."""
    result = check_procedure_rate("Appendicectomy", 25000, "metro", True)
    assert result["matched"] is True
    assert result["cghs_rate"] == 19000
    assert result["difference"] == 6000


def test_citation_library_integrity():
    """Test that the citation library has all required clauses."""
    clause_ids = get_all_clause_ids()
    # Must have all the key clauses
    required = [
        "MC2024:proportionate", "MC2024:moratorium", "MC2024:fraud",
        "MC2024:cashless", "MC2024:nonpayable", "MC2024:condonation",
        "PPI2017:claims", "PPI2017:grievance",
        "OMB2017:filing", "OMB2017:award",
        "NPPA:DPCO2013", "CGHS:reference"
    ]
    for cid in required:
        assert clause_exists(cid), f"Required clause '{cid}' not in library"

    # Validate that no fabricated citations pass
    validation = validate_citations(["FAKE:clause", "MC2024:proportionate"])
    assert validation["valid"] is False
    assert "FAKE:clause" in validation["invalid_ids"]