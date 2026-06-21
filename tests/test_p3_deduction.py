"""
Pehredaar — Golden Fixture Tests (P3: Deduction Calculator)
============================================================
Tests the proportionate deduction calculator against all 12 hand-computed
golden scenarios. The calculator must match EVERY expected value EXACTLY.
"""

import json
import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES_DIR = os.environ.get("PEHREDAAR_FIXTURES_DIR", os.path.join(_REPO_ROOT, "fixtures"))
sys.path.insert(0, _REPO_ROOT)

from pehredaar_pkg.defender.proportionate_deduction import ProportionateDeductionCalculator


def load_golden_scenarios():
    """Load the golden deduction scenarios."""
    fixture_path = os.path.join(_FIXTURES_DIR, "deduction-scenarios.json")
    with open(fixture_path, "r") as f:
        data = json.load(f)
    return data["scenarios"]


def test_all_golden_scenarios():
    """Test that the calculator matches all 12 golden scenarios exactly."""
    scenarios = load_golden_scenarios()
    assert len(scenarios) == 12, f"Expected 12 scenarios, got {len(scenarios)}"

    for scenario in scenarios:
        sid = scenario["id"]
        inputs = scenario["inputs"]
        expected = scenario["expected"]

        result = ProportionateDeductionCalculator.calculate(inputs)

        for key, exp_val in expected.items():
            assert key in result, f"{sid}: missing key '{key}'"
            got_val = result[key]
            if isinstance(exp_val, float):
                assert abs(got_val - exp_val) < 0.001, f"{sid}: {key} expected {exp_val}, got {got_val}"
            else:
                assert got_val == exp_val, f"{sid}: {key} expected {exp_val}, got {got_val}"


def test_s1_classic():
    """Test S1: classic 8k vs 5k room cap."""
    result = ProportionateDeductionCalculator.calculate({
        "sum_insured": 500000, "room_cap_per_day": 5000, "actual_room_rent_per_day": 8000, "days": 3,
        "variable_charges": {"surgery": 80000, "doctor_visit": 15000, "nursing": 6000},
        "fixed_charges": {"medicines": 4000, "diagnostics": 5000}
    })
    assert result["factor"] == 0.625
    assert result["proportionate_hit"] == 37875
    assert result["total_oop"] == 46875


def test_s2_within_cap():
    """Test S2: within cap, no deduction."""
    result = ProportionateDeductionCalculator.calculate({
        "sum_insured": 500000, "room_cap_per_day": 5000, "actual_room_rent_per_day": 4500, "days": 4,
        "variable_charges": {"surgery": 60000, "nursing": 8000},
        "fixed_charges": {"medicines": 7000}
    })
    assert result["factor"] == 1.0
    assert result["proportionate_hit"] == 0
    assert result["total_oop"] == 0


def test_s7_wrongly_applied_to_fixed():
    """Test S7: wrongly applied to fixed charges."""
    result = ProportionateDeductionCalculator.calculate({
        "sum_insured": 500000, "room_cap_per_day": 5000, "actual_room_rent_per_day": 10000, "days": 2,
        "variable_charges": {"surgeon": 80000},
        "fixed_charges": {"implants": 100000, "medicines": 20000}
    })
    assert result["factor"] == 0.5
    assert result["fixed_eligible"] == 120000  # Fixed NOT cut
    assert result["insurer_wrong_eligible_if_fixed_also_cut"] == 110000  # If wrongly cut
    assert result["recoverable_vs_wrong"] == 60000  # Recoverable amount


def test_s10_disease_sublimit():
    """Test S10: disease sub-limit overrides."""
    result = ProportionateDeductionCalculator.calculate({
        "sum_insured": 500000, "room_cap_per_day": 5000, "actual_room_rent_per_day": 5000, "days": 1,
        "disease_sublimit": {"name": "cataract", "cap": 40000},
        "variable_charges": {"cataract_surgery": 60000},
        "fixed_charges": {"lens_implant": 15000}
    })
    assert result["disease_cap_applied"] == 40000
    assert result["surgery_eligible"] == 40000
    assert result["surgery_excess"] == 20000
    assert result["total_eligible"] == 45000
    assert result["total_oop"] == 35000