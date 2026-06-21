"""
Pehredaar — Policy Parser (PURE DETERMINISTIC CODE)
====================================================
No model calls. No network. Pure lookup + structured-dict parsing.

Accepts either:
  (a) a policy name → fuzzy-matched against a curated lookup table of ~20 common
      Indian health insurance plans, or
  (b) an uploaded policy schedule (structured dict) → normalized to the canonical
      schema.

Returns a policy record matching the canonical schema from SPEC.md §6:

    policy record:
      plan_name, insurer, room_cap_type (abs|pct|none), room_cap_value,
      icu_cap, copay_pct, deductible, sublimits[], non_payable_policy,
      source (lookup|uploaded), source_date

All plan data is based on realistic, publicly-known plan features as of 2024-06.
Sub-limits and co-pay options vary by variant and sum-insured band; the values
here represent the commonly-sold variant and are labeled source='lookup'.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover — rapidfuzz is a project dependency
    fuzz = None
    process = None


# ============================================================================
# Canonical schema — matches SPEC.md §6 exactly
# ============================================================================

@dataclass
class PolicyRecord:
    """Canonical policy record (SPEC.md §6)."""
    plan_name: str
    insurer: str
    room_cap_type: str          # "abs" | "pct" | "none"
    room_cap_value: Optional[float]   # ₹/day if abs, % of SI if pct, None if none
    icu_cap: Optional[float]          # ₹/day or None
    copay_pct: float                  # 0 if no co-pay
    deductible: float                 # 0 if no deductible
    sublimits: List[Dict[str, Any]]   # disease-wise sub-limits
    non_payable_policy: str           # how the policy handles non-payables
    source: str                       # "lookup" | "uploaded"
    source_date: str                  # YYYY-MM

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Curated lookup table — 20 common Indian health insurance plans
# Data reflects commonly-sold variants as of 2024-06.
# ============================================================================

_LOOKUP_DATE = "2024-06"

_POLICY_LOOKUP: Dict[str, Dict[str, Any]] = {
    "star health family health optima": {
        "plan_name": "Star Health Family Health Optima",
        "insurer": "Star Health and Allied Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": None,                # no separate ICU cap
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "star health comprehensive": {
        "plan_name": "Star Health Comprehensive",
        "insurer": "Star Health and Allied Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 2.0,          # 2% of sum insured per day
        "icu_cap": 4.0,                 # 4% of sum insured per day (pct)
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
            {"disease": "hernia", "limit": 50000, "unit": "per surgery"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "hdfc ergo optima secure": {
        "plan_name": "HDFC Ergo Optima Secure",
        "insurer": "HDFC ERGO General Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,         # no room rent sub-limit
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 50000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; no separate non-payable add-on",
    },
    "icici lombard elevate": {
        "plan_name": "ICICI Lombard Elevate",
        "insurer": "ICICI Lombard General Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 60000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "niva bupa reassure 2.0": {
        "plan_name": "Niva Bupa ReAssure 2.0",
        "insurer": "Niva Bupa Health Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "care health care supreme": {
        "plan_name": "Care Health Care Supreme",
        "insurer": "Care Health Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 20.0,              # 20% co-pay if chosen (optional variant)
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "aditya birla activ one": {
        "plan_name": "Aditya Birla Activ One",
        "insurer": "Aditya Birla Health Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "bajaj allianz health guard": {
        "plan_name": "Bajaj Allianz Health Guard",
        "insurer": "Bajaj Allianz General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "tata aig medicare": {
        "plan_name": "Tata AIG Medicare",
        "insurer": "Tata AIG General Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 50000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "manipalcigna prohealth": {
        "plan_name": "ManipalCigna ProHealth",
        "insurer": "ManipalCigna Health Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 20.0,              # co-pay options available
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "acko platinum plan": {
        "plan_name": "Acko Platinum Plan",
        "insurer": "Acko General Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "digit health care plus": {
        "plan_name": "Digit Health Care Plus",
        "insurer": "Go Digit General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "go digit health insurance": {
        "plan_name": "Go Digit Health Insurance",
        "insurer": "Go Digit General Insurance",
        "room_cap_type": "none",
        "room_cap_value": None,
        "icu_cap": None,
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "m star health super surplus": {
        "plan_name": "M Star Health Super Surplus",
        "insurer": "Star Health and Allied Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "royal sundaram lifeline": {
        "plan_name": "Royal Sundaram Lifeline",
        "insurer": "Royal Sundaram General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "sbi general arogya": {
        "plan_name": "SBI General Arogya",
        "insurer": "SBI General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "universal sompo health care": {
        "plan_name": "Universal Sompo Health Care",
        "insurer": "Universal Sompo General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "liberty health connect": {
        "plan_name": "Liberty Health Connect",
        "insurer": "Liberty General Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": True,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "new india assurance mediclaim": {
        "plan_name": "New India Assurance Mediclaim",
        "insurer": "New India Assurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
            {"disease": "knee replacement", "limit": 150000, "unit": "per surgery"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
    "oriental insurance happy family": {
        "plan_name": "Oriental Insurance Happy Family",
        "insurer": "Oriental Insurance",
        "room_cap_type": "pct",
        "room_cap_value": 1.0,          # 1% of sum insured per day
        "icu_cap": 2.0,                 # 2% of sum insured per day
        "copay_pct": 0.0,
        "deductible": 0.0,
        "sublimits": [
            {"disease": "cataract", "limit": 40000, "unit": "per eye"},
        ],
        "restoration": False,
        "non_payable_policy": "IRDAI non-payable lists apply; optional items not covered unless add-on",
    },
}


# ============================================================================
# Parser
# ============================================================================

class PolicyParser:
    """
    Policy lookup + parsing system.

    Usage:
        record = PolicyParser.parse("Star Health Family Health Optima")
        record = PolicyParser.parse(uploaded_schedule_dict)
    """

    # Minimum fuzzy-match score for a lookup hit (0-100)
    MATCH_THRESHOLD: int = 80

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Lowercase, collapse whitespace, strip common suffixes for matching."""
        n = name.lower().strip()
        # Remove common plan-type suffixes that users may or may not include
        for suffix in (" plan", " policy", " insurance", " health insurance"):
            if n.endswith(suffix):
                n = n[: -len(suffix)].strip()
        return " ".join(n.split())

    @staticmethod
    def _fuzzy_lookup(plan_name: str) -> Optional[str]:
        """
        Fuzzy-match a user-provided plan name against the lookup keys.
        Returns the matched canonical key or None.
        """
        if process is None:
            # Fallback: exact or substring match without rapidfuzz
            norm = PolicyParser._normalize_name(plan_name)
            for key in _POLICY_LOOKUP:
                if norm == key or norm in key or key in norm:
                    return key
            return None

        norm = PolicyParser._normalize_name(plan_name)
        keys = list(_POLICY_LOOKUP.keys())
        result = process.extractOne(
            norm, keys, scorer=fuzz.token_set_ratio
        )
        if result is not None and result[1] >= PolicyParser.MATCH_THRESHOLD:
            return result[0]
        return None

    @staticmethod
    def _record_from_lookup(key: str) -> PolicyRecord:
        """Build a PolicyRecord from a lookup-table entry."""
        entry = _POLICY_LOOKUP[key]
        return PolicyRecord(
            plan_name=entry["plan_name"],
            insurer=entry["insurer"],
            room_cap_type=entry["room_cap_type"],
            room_cap_value=entry["room_cap_value"],
            icu_cap=entry["icu_cap"],
            copay_pct=entry["copay_pct"],
            deductible=entry["deductible"],
            sublimits=list(entry.get("sublimits", [])),
            non_payable_policy=entry["non_payable_policy"],
            source="lookup",
            source_date=_LOOKUP_DATE,
        )

    @staticmethod
    def _record_from_upload(schedule: Dict[str, Any]) -> PolicyRecord:
        """
        Normalize an uploaded policy schedule (structured dict) to the canonical
        schema. Accepts a variety of key naming conventions.
        """
        def _get(*keys: str, default: Any = None) -> Any:
            for k in keys:
                if k in schedule and schedule[k] is not None:
                    return schedule[k]
            return default

        plan_name = _get("plan_name", "planName", "policy_name", "name",
                         default="Uploaded Policy")
        insurer = _get("insurer", "insurance_company", "company",
                       default="Unknown")

        # Room cap — accept abs/pct/none or legacy "no_room_limit" flag
        room_cap_type = _get("room_cap_type", "roomCapType",
                             default="none")
        if isinstance(room_cap_type, str):
            room_cap_type = room_cap_type.lower().strip()
        if room_cap_type not in ("abs", "pct", "none"):
            # If a numeric cap value is given but type is ambiguous, infer
            room_cap_value = _get("room_cap_value", "roomCapValue",
                                  "room_cap_per_day", default=None)
            if room_cap_value is not None:
                room_cap_type = "abs"
            else:
                room_cap_type = "none"

        room_cap_value = _get("room_cap_value", "roomCapValue",
                              "room_cap_per_day", "room_cap_pct_of_si",
                              default=None)
        if room_cap_type == "none":
            room_cap_value = None

        icu_cap = _get("icu_cap", "icuCap", "icu_cap_per_day",
                       "icu_cap_pct_of_si", default=None)

        copay_pct = float(_get("copay_pct", "copayPct", "copay",
                               default=0) or 0)
        deductible = float(_get("deductible", default=0) or 0)

        # Sub-limits — accept list of dicts or dict of disease→limit
        sublimits_raw = _get("sublimits", "sub_limits", "disease_sublimits",
                             "subLimits", default=[])
        sublimits: List[Dict[str, Any]] = []
        if isinstance(sublimits_raw, dict):
            for disease, limit in sublimits_raw.items():
                sublimits.append({
                    "disease": disease,
                    "limit": limit,
                    "unit": "per episode",
                })
        elif isinstance(sublimits_raw, list):
            for sub in sublimits_raw:
                if isinstance(sub, dict):
                    sublimits.append({
                        "disease": sub.get("disease", sub.get("name", "unknown")),
                        "limit": sub.get("limit", sub.get("amount", 0)),
                        "unit": sub.get("unit", "per episode"),
                    })

        non_payable_policy = _get(
            "non_payable_policy", "nonPayablePolicy",
            default="IRDAI non-payable lists apply; optional items not covered unless add-on",
        )

        source_date = _get("source_date", "sourceDate",
                           default=datetime.now().astimezone().strftime("%Y-%m"))

        return PolicyRecord(
            plan_name=plan_name,
            insurer=insurer,
            room_cap_type=room_cap_type,
            room_cap_value=room_cap_value,
            icu_cap=icu_cap,
            copay_pct=copay_pct,
            deductible=deductible,
            sublimits=sublimits,
            non_payable_policy=non_payable_policy,
            source="uploaded",
            source_date=source_date,
        )

    @staticmethod
    def parse(policy_input: Union[str, Dict[str, Any]]) -> PolicyRecord:
        """
        Parse a policy into a canonical PolicyRecord.

        Args:
            policy_input: Either a plan name (str) for lookup, or an uploaded
                          policy schedule (dict) for normalization.

        Returns:
            PolicyRecord matching the SPEC.md §6 canonical schema.

        Raises:
            ValueError: If a string plan name cannot be matched to any known
                        plan and no schedule dict is provided.
            TypeError:  If the input is neither a str nor a dict.
        """
        if isinstance(policy_input, dict):
            return PolicyParser._record_from_upload(policy_input)

        if isinstance(policy_input, str):
            key = PolicyParser._fuzzy_lookup(policy_input)
            if key is None:
                raise ValueError(
                    f"Policy '{policy_input}' not found in lookup table. "
                    f"Known plans: {', '.join(p['plan_name'] for p in _POLICY_LOOKUP.values())}"
                )
            return PolicyParser._record_from_lookup(key)

        raise TypeError(
            f"policy_input must be str or dict, got {type(policy_input).__name__}"
        )

    @staticmethod
    def list_known_plans() -> List[str]:
        """Return the list of plan names available in the lookup table."""
        return [entry["plan_name"] for entry in _POLICY_LOOKUP.values()]

    @staticmethod
    def get_plan_count() -> int:
        """Return the number of plans in the lookup table."""
        return len(_POLICY_LOOKUP)


# ============================================================================
# Convenience module-level function
# ============================================================================

def parse_policy(policy_input: Union[str, Dict[str, Any]]) -> PolicyRecord:
    """
    Convenience wrapper around PolicyParser.parse().

    Args:
        policy_input: Plan name (str) or uploaded schedule (dict).

    Returns:
        PolicyRecord matching the SPEC.md §6 canonical schema.
    """
    return PolicyParser.parse(policy_input)