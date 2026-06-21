"""
Pehredaar — Golden Fixture Tests (P5: Rejection Classifier)
=============================================================
Tests the rejection classifier against all 15 golden rejection samples.
The classifier must match reason_code, winnability, and clause for each.
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pehredaar_pkg.claimback.classify import RejectionClassifier


def load_golden_samples():
    """Load the golden rejection samples."""
    fixture_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "rejection-samples.jsonl")
    samples = []
    with open(fixture_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def test_all_golden_samples():
    """Test that the classifier matches all 15 golden samples."""
    samples = load_golden_samples()
    assert len(samples) == 15, f"Expected 15 samples, got {len(samples)}"

    for sample in samples:
        result = RejectionClassifier.classify(sample["raw_text"])
        expected = sample["expected"]

        assert result["reason_code"] == expected["reason_code"], \
            f"{sample['id']}: reason_code expected {expected['reason_code']}, got {result['reason_code']}"
        assert result["winnability"] == expected["winnability"], \
            f"{sample['id']}: winnability expected {expected['winnability']}, got {result['winnability']}"
        assert result["clause"] == expected["clause"], \
            f"{sample['id']}: clause expected {expected['clause']}, got {result['clause']}"


def test_r01_proportionate_on_fixed():
    """Test R01: proportionate deduction on fixed items (green)."""
    result = RejectionClassifier.classify(
        "claim deducted as room rent exceeds eligible limit of Rs 5000; "
        "proportionate deduction applied on all charges including pharmacy"
    )
    assert result["reason_code"] == "PROPORTIONATE_ON_FIXED"
    assert result["winnability"] == "green"
    assert result["clause"] == "MC2024:proportionate"


def test_r02_ped_nondisclosure_red():
    """Test R02: PED non-disclosure without moratorium (red)."""
    result = RejectionClassifier.classify("rejected: pre-existing diabetes not disclosed at proposal")
    assert result["reason_code"] == "PED_NONDISCLOSURE"
    assert result["winnability"] == "red"
    assert result["clause"] == "MC2024:moratorium"


def test_r13_ped_moratorium_crossed():
    """Test R13: PED non-disclosure with moratorium crossed (green)."""
    result = RejectionClassifier.classify("PED not disclosed; however policy in 6th continuous year")
    assert result["reason_code"] == "PED_NONDISCLOSURE"
    assert result["winnability"] == "green"
    assert result["clause"] == "MC2024:moratorium"


def test_r14_fraud():
    """Test R14: fraud/misrepresentation (red)."""
    result = RejectionClassifier.classify("alleged fabricated bills, claim repudiated for fraud")
    assert result["reason_code"] == "FRAUD_MISREP"
    assert result["winnability"] == "red"
    assert result["clause"] == "MC2024:fraud"


def test_winnability_guardrail():
    """Test that the conservative scorer never upgrades red to green without qualifying fact."""
    # PED without moratorium info should be red
    result = RejectionClassifier.classify("pre-existing disease not disclosed")
    assert result["winnability"] == "red"

    # Waiting period should be red
    result = RejectionClassifier.classify("claim within waiting period")
    assert result["winnability"] == "red"

    # Permanent exclusion should be red
    result = RejectionClassifier.classify("permanent exclusion: cosmetic procedure")
    assert result["winnability"] == "red"

    # Fraud should be red
    result = RejectionClassifier.classify("claim repudiated for fraud")
    assert result["winnability"] == "red"


def test_disclaimer_always_present():
    """Test that the disclaimer is always attached."""
    result = RejectionClassifier.classify("some rejection text")
    assert "disclaimer" in result
    assert "not legal" in result["disclaimer"].lower() or "not insurance" in result["disclaimer"].lower()


def test_no_fabricated_citations():
    """Test that all clause ids are valid (in the clause library)."""
    from pehredaar_pkg.citations.clause_library import clause_exists
    samples = load_golden_samples()
    for sample in samples:
        result = RejectionClassifier.classify(sample["raw_text"])
        assert clause_exists(result["clause"]), \
            f"{sample['id']}: clause '{result['clause']}' does not exist in the library"