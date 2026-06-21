"""
Pehredaar — Test Suite (P4 + P6: Before You Sign + Appeal Drafter + Router)
==========================================================================
Tests the production implementations of the Before You Sign sheet generator,
appeal drafter, and escalation router.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.defender.before_you_sign import generate_sheet, generate_desk_script, format_sheet_for_whatsapp
from src.claimback.draft_appeal import draft_letter
from src.claimback.router import get_escalation_route, get_ombudsman_jurisdiction, calculate_deadline


def test_generate_sheet():
    """Test the Before You Sign sheet generator."""
    # Test with high exposure (detailed script)
    res1 = generate_sheet(5000, [
        {"type": "proportionate_deduction", "description": "Room exceeds cap", "amount": 5000, "citation": "MC2024:proportionate", "confidence": "high"}
    ])
    assert res1["total_exposure"]["amount"] == 5000
    assert "desk_query_script" in res1
    assert "disclaimer" in res1
    assert "BEFORE YOU SIGN" in res1.get("header", "") or "before you sign" in str(res1).lower()

    # Test with high exposure (>10000 → detailed script)
    res2 = generate_sheet(15000, [
        {"type": "proportionate_deduction", "description": "Room ₹8000 exceeds cap ₹5000", "amount": 15000, "citation": "MC2024:proportionate", "confidence": "high"}
    ])
    assert res2["total_exposure"]["amount"] == 15000
    assert "IRDAI" in res2["desk_query_script"] or "proportionate" in res2["desk_query_script"].lower()

    # Test with context
    res3 = generate_sheet(46875, [
        {"type": "proportionate_deduction", "description": "Room ₹8000 exceeds cap ₹5000", "amount": 46875, "citation": "MC2024:proportionate", "confidence": "high"}
    ], {"policy_name": "Star Health Optima", "room_cap": 5000, "actual_room": 8000, "days": 3, "bill_total": 134000})
    assert res3["total_exposure"]["amount"] == 46875
    assert "disclaimer" in res3


def test_format_sheet_for_whatsapp():
    """Test WhatsApp formatting."""
    sheet = generate_sheet(46875, [
        {"type": "proportionate_deduction", "description": "Test flag", "amount": 46875, "citation": "MC2024:proportionate", "confidence": "high"}
    ])
    whatsapp = format_sheet_for_whatsapp(sheet)
    assert isinstance(whatsapp, str)
    assert len(whatsapp) > 0


def test_draft_letter():
    """Test the appeal drafter."""
    # Test PROPORTIONATE_ON_FIXED
    res1 = draft_letter("PROPORTIONATE_ON_FIXED")
    assert "draft_letter" in res1
    assert "IRDAI" in res1["draft_letter"]
    assert "proportionate" in res1["draft_letter"].lower()
    assert res1["citations_valid"] is True
    assert "not legal" in res1["disclaimer"].lower()

    # Test with context (moratorium crossed)
    res2 = draft_letter("PED_NONDISCLOSURE", {"continuous_cover_months": 72})
    assert "moratorium" in res2["draft_letter"].lower()
    assert "60 months" in res2["draft_letter"]
    assert res2["clause_id"] == "MC2024:moratorium"

    # Test unknown reason code
    res3 = draft_letter("NOT_A_REAL_CODE")
    assert "draft_letter" in res3
    assert "disclaimer" in res3


def test_get_escalation_route():
    """Test the escalation router."""
    route = get_escalation_route()
    assert "escalation_steps" in route
    assert len(route["escalation_steps"]) == 4  # GRO → Bima Bharosa → Ombudsman → Consumer Commission
    assert route["escalation_steps"][0]["authority"] == "Insurer Grievance Redressal Officer (GRO)"
    assert "15 days" in route["escalation_steps"][0]["deadline"]
    assert route["escalation_steps"][2]["authority"] == "Insurance Ombudsman"
    assert "30 lakh" in route["escalation_steps"][2]["monetary_limit"]
    assert route["ombudsman_monetary_limit"] == 3000000


def test_escalation_with_high_claim():
    """Test escalation route with claim exceeding Ombudsman limit."""
    route = get_escalation_route(claim_amount=3500000)
    # Should note that claim exceeds Ombudsman limit
    notes_text = " ".join(route["notes"])
    assert "exceeds" in notes_text.lower() or "30 lakh" in notes_text


def test_ombudsman_jurisdiction():
    """Test Ombudsman jurisdiction lookup."""
    result = get_ombudsman_jurisdiction("Mumbai")
    assert result["ombudsman_center"] == "Mumbai"

    result2 = get_ombudsman_jurisdiction("Delhi")
    assert result2["ombudsman_center"] == "New Delhi"


def test_calculate_deadline():
    """Test deadline calculation."""
    result = calculate_deadline("2025-06-15")
    assert "ombudsman_filing_deadline" in result
    assert "days_remaining" in result
    assert "status" in result