"""
Pehredaar — ClaimBack Rejection Classifier
==========================================
Pure deterministic classifier that maps insurer rejection / short-settlement
letters to a structured reason-code taxonomy and assigns a conservative
winnability score.

No AI / model calls are made.  Classification is performed entirely through
keyword and regex matching against curated patterns derived from the golden
rejection sample set (fixtures/rejection-samples.jsonl) and the taxonomy
(fixtures/rejection-taxonomy.md).

Every clause id emitted in the output is validated against the curated clause
library (src.citations.clause_library) to guarantee **zero fabricated
citations** — if a clause id is not found the field is cleared and a warning
is attached.

Winnability scoring is deliberately conservative:
  * ``red``    — strong insurer position; appeal unlikely to succeed without
                 an explicit qualifying fact (e.g. moratorium crossed).
  * ``amber``  — challengeable; outcome depends on additional evidence.
  * ``green``  — strong appeal case; insurer position is weak or curable.

The scorer may *downgrade* but must **never upgrade** a ``red`` to ``green``
without an explicit, documented override rule present in the input text or
context dict.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Clause-library import — with exec()-harness fallback
# ---------------------------------------------------------------------------
try:
    from pehredaar_pkg.citations.clause_library import clause_exists, CLAUSE_LIBRARY
except ImportError:  # pragma: no cover — exercised by exec-based test harness
    # When loaded via exec() the names may already be in the global scope
    # because clause_library.py was exec'd immediately before this file.
    if "clause_exists" not in globals() or "CLAUSE_LIBRARY" not in globals():
        raise
    # clause_exists and CLAUSE_LIBRARY are already in globals — nothing to do.


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DISCLAIMER = "Informational only, not legal/insurance advice."

# Reason codes that can NEVER be green without an explicit qualifying fact.
_NO_GREEN_WITHOUT_OVERRIDE: frozenset[str] = frozenset({
    "PED_NONDISCLOSURE",
    "WAITING_PERIOD",
    "EXCLUSION_PERMANENT",
    "FRAUD_MISREP",
})

# Fixed-price items whose cost is independent of room category.
# A proportionate deduction applied to any of these is incorrect and gives
# the policyholder a strong refund case (green).
_FIXED_PRICE_KEYWORDS: frozenset[str] = frozenset({
    "pharmacy", "pharmacist", "medicine", "medicines",
    "implant", "implants",
    "consumable", "consumables",
    "diagnostic", "diagnostics",
    "investigation", "lab", "labs",
})

# Moratorium period = 60 months of continuous cover (IRDAI MC2024).
_MORATORIUM_MONTHS = 60


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class RejectionClassifier:
    """
    Deterministic rejection-letter classifier with conservative winnability
    scoring.

    Usage::

        result = RejectionClassifier.classify(letter_text)
        # result = {
        #     "reason_code": "PROPORTIONATE_ON_FIXED",
        #     "secondary":   "ROOM_RENT_PROPORTIONATE",
        #     "winnability": "green",
        #     "clause":      "MC2024:proportionate",
        #     "rationale":   "Fixed-price items must not be ...",
        #     "next_step":   None,
        #     "disclaimer":  "Informational only, not legal/insurance advice.",
        # }

    An optional ``context`` dict may carry override facts::

        result = RejectionClassifier.classify(
            letter_text,
            context={"continuous_cover_months": 72},
        )
    """

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def classify(
        letter_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classify a rejection / short-settlement letter.

        Parameters
        ----------
        letter_text
            Raw text of the insurer's rejection or short-settlement letter.
        context
            Optional dictionary of override facts, e.g.::

                {"continuous_cover_months": 72}

            When ``continuous_cover_months >= 60`` a PED_NONDISCLOSURE
            classification is upgraded from ``red`` to ``green`` because the
            IRDAI moratorium period has been crossed.

        Returns
        -------
        dict
            Keys: ``reason_code``, ``secondary``, ``winnability``, ``clause``,
            ``rationale``, ``next_step``, ``disclaimer``.
        """
        # --- guard: empty / null input -------------------------------- #
        if not letter_text or not letter_text.strip():
            result = RejectionClassifier._unclear_result(
                "Empty or missing letter text — cannot classify."
            )
            result["disclaimer"] = DISCLAIMER
            return result

        text = letter_text.lower()
        ctx = context or {}

        # --- classify via priority-ordered rules ----------------------- #
        result = RejectionClassifier._match_rules(text, ctx)

        # --- conservative winnability guardrails ----------------------- #
        result = RejectionClassifier._enforce_winnability_guard(result, text, ctx)

        # --- zero-fabricated-citation check ---------------------------- #
        result = RejectionClassifier._validate_clause(result)

        # --- always attach disclaimer --------------------------------- #
        result["disclaimer"] = DISCLAIMER

        return result

    # ------------------------------------------------------------------ #
    #  Rule engine                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _match_rules(text: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Try each classification rule in priority order.

        The first rule whose keyword pattern matches wins.  Rules are ordered
        so that more specific / higher-priority reasons are checked before
        broader ones, preventing mis-classification when a letter mentions
        multiple topics.
        """

        # 1 — FRAUD_MISREP (highest priority: most serious allegation) --- #
        if RejectionClassifier._has_any(text, [
            "fraud", "fabricat", "misrep", "repudiat",
        ]):
            return {
                "reason_code": "FRAUD_MISREP",
                "secondary": None,
                "winnability": "red",
                "clause": "MC2024:fraud",
                "rationale": None,
                "next_step": "legal counsel",
            }

        # 2 — PED_NONDISCLOSURE ----------------------------------------- #
        if RejectionClassifier._is_ped_nondisclosure(text):
            moratorium_crossed = RejectionClassifier._moratorium_crossed(text, ctx)
            if moratorium_crossed:
                return {
                    "reason_code": "PED_NONDISCLOSURE",
                    "secondary": None,
                    "winnability": "green",
                    "clause": "MC2024:moratorium",
                    "rationale": "moratorium crossed",
                    "next_step": None,
                }
            return {
                "reason_code": "PED_NONDISCLOSURE",
                "secondary": None,
                "winnability": "red",
                "clause": "MC2024:moratorium",
                "rationale": None,
                "next_step": None,
            }

        # 3 — WAITING_PERIOD -------------------------------------------- #
        if "waiting period" in text or "waiting-period" in text:
            return {
                "reason_code": "WAITING_PERIOD",
                "secondary": None,
                "winnability": "red",
                "clause": "policy:waiting",
                "rationale": None,
                "next_step": None,
            }

        # 4 — EXCLUSION_PERMANENT --------------------------------------- #
        if ("permanent exclusion" in text
                or "permanently excluded" in text
                or ("exclusion" in text and "permanent" in text)):
            return {
                "reason_code": "EXCLUSION_PERMANENT",
                "secondary": None,
                "winnability": "red",
                "clause": "policy:exclusions",
                "rationale": None,
                "next_step": None,
            }

        # 5 & 6 — proportionate deduction family ------------------------ #
        if "proportionate" in text:
            # If the deduction touches fixed-price items it is incorrect.
            if RejectionClassifier._has_any(text, _FIXED_PRICE_KEYWORDS):
                return {
                    "reason_code": "PROPORTIONATE_ON_FIXED",
                    "secondary": "ROOM_RENT_PROPORTIONATE",
                    "winnability": "green",
                    "clause": "MC2024:proportionate",
                    "rationale": (
                        "Fixed-price items (pharmacy/implants/medicines/"
                        "diagnostics) must not be proportionately reduced."
                    ),
                    "next_step": None,
                }
            # Otherwise it is a room-linked variable-charge deduction.
            return {
                "reason_code": "ROOM_RENT_PROPORTIONATE",
                "secondary": None,
                "winnability": "amber",
                "clause": "MC2024:proportionate",
                "rationale": "valid on room-linked variable charges",
                "next_step": None,
            }

        # 7 — LATE_INTIMATION ------------------------------------------- #
        if "intimation" in text and RejectionClassifier._has_any(text, [
            "after", "beyond", "late", "delay", "48 hour", "deadline",
        ]):
            return {
                "reason_code": "LATE_INTIMATION",
                "secondary": None,
                "winnability": "amber",
                "clause": "MC2024:condonation",
                "rationale": None,
                "next_step": None,
            }

        # 8 — NOT_MEDICALLY_NECESSARY ----------------------------------- #
        if ("medically necessary" in text
                or "not warranted" in text
                or "could be opd" in text
                or "could be treated as opd" in text):
            return {
                "reason_code": "NOT_MEDICALLY_NECESSARY",
                "secondary": None,
                "winnability": "amber",
                "clause": "PPI2017:claims",
                "rationale": None,
                "next_step": None,
            }

        # 9 — REASONABLE_CUSTOMARY -------------------------------------- #
        if ("reasonable and customary" in text
                or "reasonable & customary" in text):
            return {
                "reason_code": "REASONABLE_CUSTOMARY",
                "secondary": None,
                "winnability": "amber",
                "clause": "policy:RC",
                "rationale": None,
                "next_step": None,
            }

        # 10 — NON_PAYABLE_ITEMS ---------------------------------------- #
        if ("non-payable" in text
                or "non payable" in text
                or "not payable" in text):
            return {
                "reason_code": "NON_PAYABLE_ITEMS",
                "secondary": None,
                "winnability": "green",
                "clause": "MC2024:nonpayable",
                "rationale": None,
                "next_step": None,
            }

        # 11 — DOCUMENTATION_TECHNICAL ---------------------------------- #
        if ("not legible" in text
                or "illegible" in text
                or ("missing" in text and RejectionClassifier._has_any(text, [
                    "report", "document", "investigation", "summary",
                    "discharge", "bill", "receipt",
                ]))
                or ("insufficient" in text and "document" in text)):
            return {
                "reason_code": "DOCUMENTATION_TECHNICAL",
                "secondary": None,
                "winnability": "green",
                "clause": "PPI2017:claims",
                "rationale": None,
                "next_step": None,
            }

        # 12 — CASHLESS_DENIED ------------------------------------------ #
        if "cashless" in text and RejectionClassifier._has_any(text, [
            "denied", "pre-authorization", "pre-auth", "refused", "rejected",
        ]):
            return {
                "reason_code": "CASHLESS_DENIED",
                "secondary": None,
                "winnability": "green",
                "clause": "MC2024:cashless",
                "rationale": None,
                "next_step": None,
            }

        # 13 — TARIFF_PACKAGE_CAP --------------------------------------- #
        if (re.search(r"package\s+(cap|rate|of)", text)
                or "sub-limit" in text
                or "sublimit" in text
                or "sub limit" in text):
            # A sub-limit is a hard cap that is typically a valid policy
            # term — harder to challenge (red) and the excess is treated
            # as non-payable.
            if ("sub-limit" in text
                    or "sublimit" in text
                    or "sub limit" in text):
                return {
                    "reason_code": "TARIFF_PACKAGE_CAP",
                    "secondary": "NON_PAYABLE_ITEMS",
                    "winnability": "red",
                    "clause": "policy:package",
                    "rationale": None,
                    "next_step": None,
                }
            return {
                "reason_code": "TARIFF_PACKAGE_CAP",
                "secondary": None,
                "winnability": "amber",
                "clause": "policy:package",
                "rationale": None,
                "next_step": None,
            }

        # 14 — fallback: unclear ---------------------------------------- #
        return RejectionClassifier._unclear_result(
            "Reason unclear — request the specific clause the insurer cited."
        )

    # ------------------------------------------------------------------ #
    #  Winnability guardrails                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _enforce_winnability_guard(
        result: Dict[str, Any],
        text: str,
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enforce conservative winnability rules.

        A ``red``-default reason code may never be scored ``green`` unless an
        explicit qualifying fact is present in the text or context.  This is
        a safety net — the rule engine already sets the correct winnability,
        but this method guarantees the invariant even if rules are edited.
        """
        reason = result.get("reason_code", "")
        winnability = result.get("winnability", "amber")

        if reason in _NO_GREEN_WITHOUT_OVERRIDE and winnability == "green":
            # Re-verify the override condition independently.
            if reason == "PED_NONDISCLOSURE":
                if not RejectionClassifier._moratorium_crossed(text, ctx):
                    result["winnability"] = "red"
                    result["rationale"] = (
                        "No moratorium override detected — "
                        "winnability downgraded to red."
                    )
            else:
                result["winnability"] = "red"
                result["rationale"] = (
                    "Conservative guardrail: no qualifying fact for green."
                )

        return result

    # ------------------------------------------------------------------ #
    #  Clause validation                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_clause(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the clause id exists in the curated library.

        If the id is unknown the ``clause`` field is set to ``None`` and a
        warning is appended to ``rationale``.  This is the zero-fabricated-
        citation guardrail.
        """
        clause_id = result.get("clause")
        if clause_id and not clause_exists(clause_id):
            existing_rationale = result.get("rationale") or ""
            warning = f"[Warning: clause id '{clause_id}' not found in library.]"
            result["clause"] = None
            result["rationale"] = (
                f"{existing_rationale} {warning}".strip()
            )
        return result

    # ------------------------------------------------------------------ #
    #  Pattern helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _has_any(text: str, keywords: list[str] | frozenset[str]) -> bool:
        """Return True if *text* contains any of *keywords*."""
        return any(kw in text for kw in keywords)

    @staticmethod
    def _is_ped_nondisclosure(text: str) -> bool:
        """
        Detect PED non-disclosure language.

        Matches patterns like:
          * "pre-existing diabetes not disclosed"
          * "PED not disclosed"
          * "non-disclosure of pre-existing disease"
        """
        has_ped = (
            "pre-existing" in text
            or "pre existing" in text
            or re.search(r"\bped\b", text) is not None
        )
        has_disclosure_issue = "disclos" in text  # matches disclosed/disclosure/non-disclosure
        return has_ped and has_disclosure_issue

    @staticmethod
    def _moratorium_crossed(text: str, ctx: Dict[str, Any]) -> bool:
        """
        Determine whether the IRDAI moratorium period (60 months / 5 years of
        continuous cover) has been crossed, which would upgrade a
        PED_NONDISCLOSURE classification from ``red`` to ``green``.

        Checks (in order):
          1. ``context['continuous_cover_months'] >= 60``
          2. Text mentions "moratorium" + "crossed"/"expired"/"elapsed"
          3. Text mentions "Nth continuous year" where N >= 5
          4. Text mentions "continuous year" or "continuous cover" (general)
        """
        # 1 — explicit context fact
        ccm = ctx.get("continuous_cover_months")
        if ccm is not None and ccm >= _MORATORIUM_MONTHS:
            return True

        # 2 — explicit moratorium language
        if "moratorium" in text and RejectionClassifier._has_any(text, [
            "crossed", "expired", "elapsed", "over",
        ]):
            return True

        # 3 — "Nth continuous year" with N >= 5  (5 years = 60 months)
        year_match = re.search(
            r"(\d+)(?:st|nd|rd|th)?\s+continuous\s+year",
            text,
        )
        if year_match and int(year_match.group(1)) >= 5:
            return True

        # NOTE: a bare "continuous year" / "continuous cover" mention without
        # an explicit year number or month count is intentionally NOT treated
        # as moratorium-crossed — the conservative scorer requires a concrete
        # qualifying fact before upgrading a red reason to green.

        return False

    # ------------------------------------------------------------------ #
    #  Fallback                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _unclear_result(message: str) -> Dict[str, Any]:
        """Build a default UNCLEAR classification."""
        return {
            "reason_code": "UNCLEAR",
            "secondary": None,
            "winnability": "amber",
            "clause": None,
            "rationale": message,
            "next_step": (
                "Request the specific clause the insurer cited in the "
                "rejection letter."
            ),
        }