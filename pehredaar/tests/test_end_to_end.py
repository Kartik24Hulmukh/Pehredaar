from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pii_redact():
    res = client.post("/ingest/bill", json={"text": "My Aadhaar is 1234 5678 9012 and phone is 9876543210."})
    assert res.status_code == 200
    data = res.json()
    assert "[REDACTED_AADHAAR]" in data["redacted_text"]
    assert "[REDACTED_PHONE]" in data["redacted_text"]
    assert "9876543210" not in data["redacted_text"]

def test_rules_engine():
    items = [
        {"canonical_name": "Syringe 5ml", "unit_price": 50},
        {"canonical_name": "Consultation", "unit_price": 1000}
    ]
    res = client.post("/rules/evaluate", json={"items": items})
    assert res.status_code == 200
    flags = res.json()["flags"]
    assert len(flags) > 0
    # Expected non_payable flag for Syringe
    assert any("Found in IRDAI non-payable list" in f["reason"] for f in flags)
    # Expected cghs flag for Consultation
    assert any("Exceeds CGHS benchmark" in f["reason"] for f in flags)

def test_policy_parser():
    res = client.post("/defender/policy", json={"document_text": "Room rent cap: ₹5,000 per day."})
    assert res.status_code == 200
    assert res.json()["parsed_policy"]["room_cap_per_day"] == 5000

def test_appeal_drafter():
    res = client.post("/claimback/draft-appeal", json={"rejection_reason": "PROPORTIONATE_ON_FIXED", "clause_id": "MC2024:proportionate"})
    assert res.status_code == 200
    appeal_text = res.json()["result"]["appeal"]["draft_letter"]
    assert "IRDAI Master Circular 2024" in appeal_text
    assert "proportionate deduction" in appeal_text

def test_api_endpoints():
    res1 = client.post("/channels/webhook", json={"payload": {"message": "bill please", "from_phone": "123"}})
    assert res1.status_code == 200
    assert "upload your bill" in res1.json()["result"]["reply"]

    res2 = client.post("/channels/receipt", json={"exposure": 50000, "flags": ["A"]})
    assert res2.status_code == 200
    assert "50000" in res2.json()["result"]["card_text"]
