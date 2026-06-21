"""
Pehredaar — Non-Payable Detector (PURE DETERMINISTIC CODE)
============================================================
No model calls. No network. Pure fuzzy matching against the IRDAI non-payable
lists from the Master Circular on Standardization
(IRDAI/HLT/REG/CIR/193/07/2020, dated 22.07.2020).

The IRDAI circular defines four lists of items that hospitals should NOT bill
separately to the patient (or are optional / not covered by standard policies):

  List I  — 68 optional items: NOT covered unless an add-on is purchased.
  List II — 37 items subsumed into ROOM CHARGES (cannot be billed separately).
  List III — 23 items subsumed into PROCEDURE CHARGES (cannot be billed separately).
  List IV — 18 items subsumed into TREATMENT COSTS (cannot be billed separately).

Every flag carries the citation clause id ``MC2024:nonpayable`` which maps to
the clause in the curated clause library
(src/citations/clause_library.py).

Matching uses rapidfuzz with a token-set-ratio threshold of 80 (case-insensitive).
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = None
    process = None


# ============================================================================
# Citation — matches the clause id in src/citations/clause_library.py
# ============================================================================

CITATION = "MC2024:nonpayable"
SOURCE_REFERENCE = "IRDAI/HLT/REG/CIR/193/07/2020"
SOURCE_DATE = "22.07.2020"


# ============================================================================
# IRDAI Non-Payable Lists (verbatim from the Master Circular, 22.07.2020)
# ============================================================================

LIST_I: List[str] = [
    "GLOVES",
    "DIAPER",
    "THERMOMETER",
    "CARRY BAGS",
    "EMAIL/INTERNET CHARGES",
    "FOOD CHARGES (OTHER THAN PATIENT'S DIET)",
    "LAUNDRY CHARGES",
    "TELEPHONE CHARGES",
    "CREPE BANDAGE",
    "TELEVISION CHARGES",
    "SURCHARGES",
    "ATTENDANT CHARGES",
    "CONVEYANCE CHARGES",
    "MORTUARY CHARGES",
    "NEBULIZER KIT",
    "STEAM INHALER",
    "ARMSLING",
    "CERVICAL COLLAR",
    "SPLINT",
    "DIABETIC FOOT WEAR",
    "KNEE BRACES",
    "KNEE IMMOBILIZER/SHOULDER IMMOBILIZER",
    "LUMBO SACRAL BELT",
    "AMBULANCE",
    "PRIVATE NURSES CHARGES",
    "ECG ELECTRODES",
    "NEBULISATION KIT",
    "ANY KIT WITH NO DETAILS MENTIONED",
    "KIDNEY TRAY",
    "MASK",
    "OUNCE GLASS",
    "OXYGEN MASK",
    "PELVIC TRACTION BELT",
    "PAN CAN",
    "TROLLY COVER",
    "UROMETER, URINE JUG",
    "VASOFIX SAFETY",
    "BIRTH CERTIFICATE",
    "CERTIFICATE CHARGES",
    "COURIER CHARGES",
    "MEDICAL CERTIFICATE",
    "MEDICAL RECORDS",
    "PHOTOCOPIES CHARGES",
    "WALKING AIDS CHARGES",
    "OXYGEN CYLINDER (OUTSIDE HOSPITAL)",
    "SPACER",
    "SPIROMETER",
    "BELTS/BRACES",
    "BUDS",
    "COLD PACK/HOT PACK",
    "BEAUTY SERVICES",
    "BABY FOOD",
    "BABY UTILITIES CHARGES",
    "SANITARY PAD",
    "GUEST SERVICES",
    "EXTRA DIET",
    "LEGGINGS",
    "MINERAL WATER",
    "EYELET COLLAR",
    "SLINGS",
    "BLOOD GROUPING AND CROSS MATCHING OF DONORS SAMPLES",
    "SERVICE CHARGES WHERE NURSING CHARGE ALSO CHARGED",
    "SUGAR FREE TABLETS",
    "CREAMS POWDERS LOTIONS",
    "ABDOMINAL BINDER",
    "AMBULANCE COLLAR",
    "AMBULANCE EQUIPMENT",
    "NIMBUS BED OR WATER OR AIR BED CHARGES",
]

LIST_II: List[str] = [
    "DOCUMENTATION CHARGES / ADMINISTRATIVE EXPENSES",
    "DISCHARGE PROCEDURE CHARGES",
    "FILE OPENING CHARGES",
    "INCIDENTAL EXPENSES / MISC. CHARGES",
    "PATIENT IDENTIFICATION BAND / NAME TAG",
    "ADMISSION KIT",
    "IM/IV INJECTION CHARGES",
    "LUXURY TAX",
    "AIR CONDITIONER CHARGES",
    "HOUSE KEEPING CHARGES",
    "ENTRANCE PASS / VISITORS PASS CHARGES",
    "DAILY CHARGES",
    "PULSEOXYMETER CHARGES",
    "BABY CHARGES",
    "HAND WASH",
    "SHOE COVER",
    "CAPS",
    "CRADLE CHARGES",
    "COMB",
    "EAU-DE-COLOGNE / ROOM FRESHNERS",
    "FOOT COVER",
    "GOWN",
    "SLIPPERS",
    "TISSUE PAPER",
    "TOOTH PASTE",
    "TOOTH BRUSH",
    "BED PAN",
    "FACE MASK",
    "FLEXI MASK",
    "HAND HOLDER",
    "SPUTUM CUP",
    "DISINFECTANT LOTIONS",
    "HVAC",
    "CLEAN SHEET",
    "BLANKET/WARMER BLANKET",
    "DIABETIC CHART CHARGES",
    "EXPENSES RELATED TO PRESCRIPTION ON DISCHARGE",
]

LIST_III: List[str] = [
    "GAUZE",
    "GAUZE SOFT",
    "COTTON",
    "COTTON BANDAGE",
    "SURGICAL TAPE",
    "APRON",
    "TOURNIQUET",
    "SURGICAL BLADES/HARMONIC SCALPEL/SHAVER",
    "SURGICAL DRILL",
    "HAIR REMOVAL CREAM",
    "DISPOSABLE RAZORS CHARGES",
    "EYE PAD",
    "EYE SHIELD",
    "CAMERA COVER",
    "DVD/CD CHARGES",
    "WARD AND THEATRE BOOKING CHARGES",
    "ARTHROSCOPY AND ENDOSCOPY INSTRUMENTS",
    "MICROSCOPE COVER",
    "EYE KIT",
    "EYE DRAPE",
    "X-RAY FILM",
    "BOYLES APPARATUS CHARGES",
    "ORTHO BUNDLE, GYNAEC BUNDLE",
]

LIST_IV: List[str] = [
    "ADMISSION/REGISTRATION CHARGES",
    "HOSPITALISATION FOR EVALUATION/DIAGNOSTIC PURPOSE",
    "URINE CONTAINER",
    "BLOOD RESERVATION CHARGES AND ANTE NATAL BOOKING CHARGES",
    "BIPAP MACHINE",
    "CPAP/CAPD EQUIPMENTS",
    "INFUSION PUMP - COST",
    "HYDROGEN PEROXIDE/SPIRIT/DISINFECTANTS",
    "NUTRITION PLANNING CHARGES / DIETICIAN CHARGES / DIET CHARGES",
    "HIV KIT",
    "ANTISEPTIC MOUTHWASH",
    "LOZENGES",
    "MOUTH PAINT",
    "VACCINATION CHARGES",
    "ALCOHOL SWABS",
    "SCRUB SOLUTION/STERILLIUM",
    "GLUCOMETER & STRIPS",
    "URINE BAG",
]


# ============================================================================
# List metadata
# ============================================================================

@dataclass
class ListMeta:
    list_id: str          # "I", "II", "III", "IV"
    description: str
    recommendation: str
    items: List[str]


_LISTS: Dict[str, ListMeta] = {
    "I": ListMeta(
        list_id="I",
        description="Optional items — not covered by standard policy unless add-on purchased",
        recommendation="optional - may not be covered by standard policy",
        items=LIST_I,
    ),
    "II": ListMeta(
        list_id="II",
        description="Subsumed into ROOM CHARGES — cannot be billed separately",
        recommendation="should be subsumed - should not be billed separately",
        items=LIST_II,
    ),
    "III": ListMeta(
        list_id="III",
        description="Subsumed into PROCEDURE CHARGES — cannot be billed separately",
        recommendation="should be subsumed - should not be billed separately",
        items=LIST_III,
    ),
    "IV": ListMeta(
        list_id="IV",
        description="Subsumed into TREATMENT COSTS — cannot be billed separately",
        recommendation="should be subsumed - should not be billed separately",
        items=LIST_IV,
    ),
}


# ============================================================================
# Result dataclasses
# ============================================================================

@dataclass
class NonPayableFlag:
    """A single flagged non-payable line item."""
    item_name: str
    matched_list: str               # "I" | "II" | "III" | "IV"
    list_description: str
    amount: float
    citation: str                   # "MC2024:nonpayable"
    recommendation: str
    matched_term: str               # the canonical list term that matched
    match_score: float              # 0-100 fuzzy score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NonPayableSummary:
    """Summary of non-payable detection across a bill."""
    total_non_payable_amount: float
    count_by_list: Dict[str, int]
    flags: List[NonPayableFlag]
    citation: str
    source_reference: str
    source_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_non_payable_amount": self.total_non_payable_amount,
            "count_by_list": self.count_by_list,
            "flags": [f.to_dict() for f in self.flags],
            "citation": self.citation,
            "source_reference": self.source_reference,
            "source_date": self.source_date,
        }


# ============================================================================
# Detector
# ============================================================================

class NonPayableDetector:
    """
    Detects IRDAI non-payable items in hospital bill line items.

    Usage:
        bill = [
            {"name": "Gloves", "amount": 500},
            {"name": "Documentation Charges", "amount": 1000},
        ]
        summary = NonPayableDetector.detect(bill)
    """

    MATCH_THRESHOLD: float = 80.0

    @staticmethod
    def _normalize(text: str) -> str:
        """Uppercase and collapse whitespace for matching."""
        return " ".join(str(text).upper().strip().split())

    @staticmethod
    def _match_item(
        item_name: str,
    ) -> Optional[Tuple[str, str, float]]:
        """
        Match a single item name against all four lists.

        Returns:
            (list_id, matched_term, score) or None if no match above threshold.
        """
        norm = NonPayableDetector._normalize(item_name)

        best: Optional[Tuple[str, str, float]] = None
        best_score: float = 0.0

        for list_id, meta in _LISTS.items():
            if process is not None:
                result = process.extractOne(
                    norm, meta.items, scorer=fuzz.token_set_ratio
                )
                if result is not None:
                    matched_term, score = result[0], result[1]
                else:
                    continue
            else:
                # Fallback: substring / exact match without rapidfuzz
                matched_term, score = None, 0.0
                for term in meta.items:
                    if norm == term:
                        matched_term, score = term, 100.0
                        break
                    if norm in term or term in norm:
                        s = (
                            min(len(norm), len(term))
                            / max(len(norm), len(term))
                            * 100
                        )
                        if s > score:
                            matched_term, score = term, s
                if matched_term is None:
                    continue

            if score >= NonPayableDetector.MATCH_THRESHOLD and score > best_score:
                best = (list_id, matched_term, float(score))
                best_score = score

        return best

    @staticmethod
    def detect(
        line_items: List[Dict[str, Any]],
    ) -> NonPayableSummary:
        """
        Detect non-payable items in a list of bill line items.

        Args:
            line_items: List of dicts, each with at least 'name' (str) and
                        'amount' (int/float). Extra keys are ignored.

        Returns:
            NonPayableSummary with total amount, per-list counts, and flags.

        Raises:
            TypeError:  If line_items is not a list.
            ValueError: If any item lacks a 'name' key.
        """
        if not isinstance(line_items, list):
            raise TypeError(
                f"line_items must be a list, got {type(line_items).__name__}"
            )

        flags: List[NonPayableFlag] = []
        count_by_list: Dict[str, int] = {"I": 0, "II": 0, "III": 0, "IV": 0}
        total_non_payable: float = 0.0

        for item in line_items:
            if not isinstance(item, dict):
                continue
            if "name" not in item or item["name"] is None:
                raise ValueError(
                    f"Line item missing required 'name' key: {item}"
                )

            name = str(item["name"])
            amount = float(item.get("amount", 0) or 0)

            match = NonPayableDetector._match_item(name)
            if match is None:
                continue

            list_id, matched_term, score = match
            meta = _LISTS[list_id]

            flag = NonPayableFlag(
                item_name=name,
                matched_list=list_id,
                list_description=meta.description,
                amount=amount,
                citation=CITATION,
                recommendation=meta.recommendation,
                matched_term=matched_term,
                match_score=score,
            )
            flags.append(flag)
            count_by_list[list_id] += 1
            total_non_payable += amount

        return NonPayableSummary(
            total_non_payable_amount=total_non_payable,
            count_by_list=count_by_list,
            flags=flags,
            citation=CITATION,
            source_reference=SOURCE_REFERENCE,
            source_date=SOURCE_DATE,
        )

    @staticmethod
    def get_list_items(list_id: str) -> List[str]:
        """Return the items for a given list id (I/II/III/IV)."""
        if list_id not in _LISTS:
            raise ValueError(
                f"Unknown list id '{list_id}'. Valid: I, II, III, IV"
            )
        return list(_LISTS[list_id].items)

    @staticmethod
    def get_list_counts() -> Dict[str, int]:
        """Return the number of items in each list."""
        return {lid: len(meta.items) for lid, meta in _LISTS.items()}


# ============================================================================
# Convenience module-level function
# ============================================================================

def detect_non_payable(
    line_items: List[Dict[str, Any]],
) -> NonPayableSummary:
    """
    Convenience wrapper around NonPayableDetector.detect().

    Args:
        line_items: List of bill line item dicts with 'name' and 'amount'.

    Returns:
        NonPayableSummary with flags, totals, and citation.
    """
    return NonPayableDetector.detect(line_items)