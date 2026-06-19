from src.defender.before_you_sign import generate_sheet
from src.claimback.draft_appeal import draft_letter
from src.claimback.router import get_escalation_route

def test_generate_sheet():
    res1 = generate_sheet(5000, ["flag1"])
    assert res1["exposure"] == 5000
    assert "Can you please check" in res1["script"]

    res2 = generate_sheet(15000, ["flag2"])
    assert res2["exposure"] == 15000
    assert "noticed my exposure is ₹15000" in res2["script"]

def test_draft_letter():
    res1 = draft_letter("PROPORTIONATE_ON_FIXED", clause_id="MC2024:proportionate")
    assert "IRDAI Master Circular 2024" in res1["draft_letter"]
    assert "proportionate" in res1["draft_letter"]

    res2 = draft_letter("NOT_A_REAL_CODE")
    assert "appealing the recent claim rejection/short settlement" in res2["draft_letter"]

def test_get_escalation_route():
    route = get_escalation_route()
    assert len(route) == 3
    assert route[0]["authority"] == "Insurer Grievance Redressal Officer (GRO)"
    assert "15 days" in route[0]["deadline"]
