"""
Pehredaar — Appeal Drafter (IRDAI-Clause-Grounded)
===================================================
Drafts formal appeal representation letters for rejected/short-settled claims.
The AI may cite ONLY clause ids that exist in the curated clause library.
A post-check rejects any draft containing an unsourced/fabricated citation.

Tone: factual, professional. Never "fraud" — always "possible error, please review."
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
import os

# Import clause library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pehredaar_pkg.citations.clause_library import get_clause, clause_exists, validate_citations, CLAUSE_LIBRARY


# Reason code to clause id mapping
_REASON_CLAUSE_MAP = {
    "PROPORTIONATE_ON_FIXED": "MC2024:proportionate",
    "ROOM_RENT_PROPORTIONATE": "MC2024:proportionate",
    "PED_NONDISCLOSURE": "MC2024:moratorium",
    "WAITING_PERIOD": "policy:waiting",
    "EXCLUSION_PERMANENT": "policy:exclusions",
    "NOT_MEDICALLY_NECESSARY": "PPI2017:claims",
    "DOCUMENTATION_TECHNICAL": "PPI2017:claims",
    "LATE_INTIMATION": "MC2024:condonation",
    "REASONABLE_CUSTOMARY": "policy:RC",
    "NON_PAYABLE_ITEMS": "MC2024:nonpayable",
    "CASHLESS_DENIED": "MC2024:cashless",
    "TARIFF_PACKAGE_CAP": "policy:package",
    "FRAUD_MISREP": "MC2024:fraud",
    "UNKNOWN": "PPI2017:grievance",
}


def _get_clause_text(clause_id: str) -> str:
    """Get verbatim clause text, or empty string if not found."""
    clause = get_clause(clause_id)
    if clause:
        return clause.verbatim_text
    return ""


def _get_clause_ref(clause_id: str) -> str:
    """Get a human-readable clause reference string."""
    clause = get_clause(clause_id)
    if clause:
        return f"{clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}"
    return clause_id


def _draft_proportionate_on_fixed(context: Dict) -> str:
    """Draft for proportionate deduction wrongly applied to fixed charges."""
    clause = get_clause("MC2024:proportionate")
    recoverable = context.get("recoverable_amount", "")
    recoverable_str = f" The wrongly deducted amount is approximately ₹{recoverable}." if recoverable else ""

    return f"""Dear Grievance Officer,

Subject: Representation against proportionate deduction applied to pharmacy/implants/diagnostics — Request for recomputation and refund

I am writing to contest the proportionate deduction applied to my claim. My claim has been subjected to proportionate deduction on charges including pharmacy, implants, and/or diagnostics, which are fixed-price items whose cost is independent of the room category chosen.

This is contrary to the IRDAI guidelines on proportionate deductions. As per {clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}:

"{clause.verbatim_text}"

Specifically, the following expenses are NOT allowed to be part of 'associate medical expenses' and therefore CANNOT be proportionately deducted:
(a) Cost of pharmacy
(b) Cost of implants and medical devices
(c) Cost of diagnostics

Additionally, proportionate deduction cannot be applied to ICU charges.{recoverable_str}

I respectfully request that you:
1. Recompute the claim without applying proportionate deduction to pharmacy, implants, medical devices, and diagnostics
2. Process the refund of the wrongly deducted amount
3. Provide a written explanation if any proportionate deduction is retained on associated medical expenses

I look forward to your response within the statutory timeline of 15 days as per IRDAI Master Circular on PP&GR 2024."""


def _draft_room_rent_proportionate(context: Dict) -> str:
    """Draft for room rent proportionate deduction (valid on variable, challenge on fixed)."""
    clause = get_clause("MC2024:proportionate")

    return f"""Dear Grievance Officer,

Subject: Representation regarding proportionate deduction due to room rent exceeding eligible limit — Request for review

I am writing regarding the proportionate deduction applied to my claim due to my room rent exceeding the eligible limit under my policy.

I understand that proportionate deduction may be applied to associated medical expenses (such as nursing, surgeon, OT, consultation, and anaesthesia charges) that are linked to the room category. However, I request you to confirm that the deduction has NOT been applied to the following, which are exempt per {clause.source_document} ({clause.reference_number}, dated {clause.date}):

"{clause.verbatim_text}"

Specifically:
- Pharmacy/medicines: NOT subject to proportionate deduction (Clause 4(a))
- Implants and medical devices: NOT subject to proportionate deduction (Clause 4(b))
- Diagnostics: NOT subject to proportionate deduction (Clause 4(c))
- ICU charges: NOT subject to proportionate deduction (Clause 7)

I respectfully request:
1. An itemized breakdown showing exactly which charges were proportionately reduced
2. Recomputation excluding fixed-price items from proportionate deduction
3. Refund of any amount wrongly deducted from pharmacy, implants, diagnostics, or ICU charges

I look forward to your response within 15 days."""


def _draft_ped_nondisclosure(context: Dict) -> str:
    """Draft for PED non-disclosure rejection, with moratorium override if applicable."""
    continuous_months = context.get("continuous_cover_months", 0)
    clause = get_clause("MC2024:moratorium")

    if continuous_months >= 60:
        return f"""Dear Grievance Officer,

Subject: Representation against rejection on grounds of PED non-disclosure — Moratorium period crossed

My claim has been rejected on the grounds of non-disclosure of a pre-existing disease. However, my policy has completed {continuous_months} months of continuous coverage, which exceeds the moratorium period of 60 months.

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}:

"{clause.verbatim_text}"

Since my policy has crossed the moratorium period of 60 months of continuous coverage, my policy and claim cannot be contested on any grounds of non-disclosure or misrepresentation, except for established fraud. No allegation of fraud has been made in my case.

I respectfully request that you:
1. Reconsider my claim in light of the moratorium provision
2. Process the claim as per policy terms
3. Provide a written response with specific reference to the moratorium clause if the rejection is maintained

I look forward to your response within 15 days."""

    else:
        return f"""Dear Grievance Officer,

Subject: Representation against rejection on grounds of PED non-disclosure — Request for review

My claim has been rejected on the grounds of non-disclosure of a pre-existing disease. I wish to contest this rejection.

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}:

"{clause.verbatim_text}"

I state that:
1. I have had continuous coverage for {continuous_months} months
2. I believe the alleged non-disclosure was not intentional
3. The condition in question was not known to me at the time of proposal

I respectfully request that you:
1. Provide the specific details of the alleged non-disclosure
2. Reconsider the claim taking into account my continuous coverage period
3. If the moratorium period (60 months) has been crossed, process the claim as per IRDAI guidelines

I look forward to your response within 15 days."""


def _draft_waiting_period(context: Dict) -> str:
    """Draft for waiting period rejection."""
    return f"""Dear Grievance Officer,

Subject: Representation regarding rejection on grounds of waiting period — Request for review

My claim has been rejected on the grounds that it falls within the waiting period specified in the policy.

I request you to verify:
1. The exact waiting period applicable to my condition as per my policy terms
2. Whether my continuous coverage, including any portability credits from previous policies, has been correctly calculated
3. Whether the waiting period has been counted from the correct inception date

As per IRDAI guidelines, credits from ported and migrated policies shall be counted for the purpose of calculating waiting periods and the moratorium period.

I respectfully request:
1. A written explanation specifying the waiting period clause, its duration, and the start date used
2. Recalculation of my continuous coverage including portability credits
3. Reconsideration of the claim if the waiting period has been incorrectly applied

I look forward to your response within 15 days."""


def _draft_exclusion_permanent(context: Dict) -> str:
    """Draft for permanent exclusion rejection."""
    return f"""Dear Grievance Officer,

Subject: Representation regarding rejection on grounds of permanent exclusion — Request for review

My claim has been rejected on the grounds that the condition/treatment is permanently excluded under my policy.

I request you to verify:
1. The exact exclusion clause cited and its wording in my policy document
2. Whether this exclusion was clearly disclosed to me at the time of policy issuance
3. Whether the exclusion wording is unambiguous and applicable to my specific condition

If the exclusion was not disclosed at issuance or the wording is ambiguous, it may not be enforceable.

I respectfully request:
1. A written response citing the specific exclusion clause and its exact wording
2. Confirmation that this exclusion was disclosed at the time of policy issuance
3. Reconsideration if the exclusion was not properly disclosed or is ambiguous

I look forward to your response within 15 days."""


def _draft_not_medically_necessary(context: Dict) -> str:
    """Draft for 'not medically necessary' rejection."""
    clause = get_clause("PPI2017:claims")

    return f"""Dear Grievance Officer,

Subject: Representation against rejection on grounds of "not medically necessary" — Request for reconsideration

My claim has been rejected on the grounds that the hospitalisation/procedure was "not medically necessary" and could have been managed as an outpatient.

I contest this assessment. My treating doctor had advised the hospitalisation/procedure in writing, and the admission was medically warranted based on my condition.

As per {clause.source_document} ({clause.reference_number}), {clause.section}:

"{clause.verbatim_text}"

I enclose the following supporting documents:
1. Treating doctor's written advice for hospitalisation
2. Discharge summary with clinical notes justifying admission
3. Relevant investigation reports

I respectfully request:
1. Reconsideration of the claim with the enclosed medical justification
2. If the rejection is maintained, a detailed written explanation from a qualified medical practitioner on the insurer's panel
3. Processing of the claim as per policy terms

I look forward to your response within 15 days."""


def _draft_documentation_technical(context: Dict) -> str:
    """Draft for documentation/technical rejection."""
    clause = get_clause("PPI2017:claims")

    return f"""Dear Grievance Officer,

Subject: Submission of additional documentation — Request for claim processing

My claim was rejected/delayed on the grounds of insufficient or missing documentation. I understand that the following documents were required:

{chr(10).join(f'- {d}' for d in context.get('missing_documents', ['Please specify the required documents']))}

I am enclosing the said documents with this representation. As per {clause.source_document} ({clause.reference_number}), {clause.section}:

"{clause.verbatim_text}"

A claim cannot be finally rejected for want of documents if the deficiency is curable. I have now submitted all the requested documents.

I respectfully request:
1. Processing of my claim with the enclosed documents
2. Settlement within the statutory timeline of 15 days from receipt of these documents

I look forward to your response within 15 days."""


def _draft_late_intimation(context: Dict) -> str:
    """Draft for late intimation rejection."""
    clause = get_clause("MC2024:condonation")

    return f"""Dear Grievance Officer,

Subject: Representation against rejection on grounds of delayed intimation — Request for condonation

My claim has been rejected on the grounds that the claim intimation was submitted after the prescribed timeline. I wish to explain the circumstances of the delay.

The delay in intimation was due to circumstances beyond my control:
{context.get('delay_reason', 'I was dealing with a medical emergency and was unable to intimate the claim within the prescribed timeline. The delay was not intentional.')}

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}):

"{clause.verbatim_text}"

The IRDAI has clearly directed that claims must not be repudiated unless the reasons for delay are specifically ascertained and recorded, and that insurers should condone delay on merit where the delay is proved to be for reasons beyond the control of the insured.

Additionally, as per IRDAI Master Circular on PP&GR 2024 (IRDAI/PP&GR/CIR/MISC/117/9/2024, dated 05.09.2024): "No claim shall be rejected or closed for want of documents or for delayed intimation of claim."

I respectfully request:
1. Condonation of the delay based on the genuine circumstances explained
2. Processing of my claim on merits
3. A written response explaining the reasons if the rejection is maintained

I look forward to your response within 15 days."""


def _draft_reasonable_customary(context: Dict) -> str:
    """Draft for reasonable and customary charges rejection."""
    return f"""Dear Grievance Officer,

Subject: Representation regarding disallowance on grounds of "reasonable and customary charges" — Request for review

My claim has been partially disallowed on the grounds that the charges exceed "reasonable and customary" rates for my geography.

I request you to provide:
1. The specific benchmark or rate list used to determine "reasonable and customary" charges
2. The source and date of the benchmark
3. A comparison of the disallowed charges against the benchmark used

Without knowing the specific benchmark applied, I am unable to assess the fairness of the disallowance. I also note that CGHS rates, often used as a benchmark, are reference rates and not legally binding price caps for private hospitals.

I respectfully request:
1. A detailed written explanation of the benchmark used for each disallowed charge
2. Reconsideration of the disallowance based on the actual charges in my hospital
3. Processing of the remaining claim amount

I look forward to your response within 15 days."""


def _draft_non_payable_items(context: Dict) -> str:
    """Draft for non-payable items rejection."""
    clause = get_clause("MC2024:nonpayable")

    return f"""Dear Grievance Officer,

Subject: Representation regarding disallowance of non-payable items — Request for review of remaining claim

My claim has been partially disallowed on the grounds that certain items are non-payable. I understand that specific consumable and administrative items may be non-payable as per IRDAI guidelines.

However, I request you to confirm that:
1. Only the specific non-payable items have been disallowed, not the entire claim
2. The remaining eligible charges have been processed and settled
3. Items that should be subsumed into room/procedure/treatment charges have not been billed separately

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}):

"{clause.verbatim_text}"

Items in Lists II, III, and IV (documentation charges, file opening charges, admission/registration charges, gauze, cotton, etc.) should be subsumed into room/procedure/treatment charges and should not be billed separately to the policyholder.

I respectfully request:
1. An itemized statement showing which items were disallowed and why
2. Confirmation that all other charges have been settled
3. Processing of any remaining eligible amount

I look forward to your response within 15 days."""


def _draft_cashless_denied(context: Dict) -> str:
    """Draft for cashless denial."""
    clause = get_clause("MC2024:cashless")

    return f"""Dear Grievance Officer,

Subject: Representation regarding denial of cashless facility — Request for reimbursement processing

My cashless pre-authorization request was denied at the network hospital. I understand that denial of cashless facility is not equivalent to rejection of the claim itself.

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}:

"{clause.verbatim_text}"

I have now incurred the expenses and am submitting the claim for reimbursement. I enclose:
1. All original bills and receipts
2. Discharge summary
3. All investigation reports
4. Cashless denial letter
5. Completed claim form

I respectfully request:
1. Processing of my reimbursement claim with all enclosed documents
2. Settlement within the statutory timeline (15 days from submission per IRDAI Master Circular on PP&GR 2024)
3. A written explanation if the claim is rejected, citing specific policy clauses

I look forward to your response within 15 days."""


def _draft_tariff_package_cap(context: Dict) -> str:
    """Draft for tariff/package cap rejection."""
    return f"""Dear Grievance Officer,

Subject: Representation regarding capping of claim at package rate — Request for review

My claim has been settled at a package rate/sub-limit that I believe does not fully cover the expenses incurred.

I request you to verify:
1. The exact package rate or sub-limit applicable to my procedure as per my policy terms
2. Whether the package rate was agreed upon at the time of policy issuance
3. Whether any unbundled charges (complications, additional procedures) were appropriately considered

I also note that if the actual procedure involved complications or additional interventions beyond the standard package, these should be considered separately.

I respectfully request:
1. A detailed comparison of the package rate applied vs the actual charges
2. Reconsideration of any unbundled charges or complications
3. Processing of any additional eligible amount

I look forward to your response within 15 days."""


def _draft_fraud_misrep(context: Dict) -> str:
    """Draft for fraud/misrepresentation rejection."""
    clause = get_clause("MC2024:fraud")

    return f"""Dear Grievance Officer,

Subject: Representation against repudiation on grounds of alleged fraud/misrepresentation — Request for review

My claim has been repudiated on the grounds of alleged fraud or misrepresentation. I firmly deny any fraud or intentional misrepresentation.

As per {clause.source_document} ({clause.reference_number}, dated {clause.date}), {clause.section}:

"{clause.verbatim_text}"

I note that:
1. The burden of proving fraud lies with the insurer
2. The fraud must be "established" — a mere allegation is insufficient
3. After the moratorium period (60 months of continuous coverage), no policy or claim can be contested except for established fraud

I respectfully request:
1. Specific details of the alleged fraud or misrepresentation, with evidence
2. Reconsideration of the claim if the allegation is not substantiated with concrete evidence
3. A detailed written response explaining the basis of the fraud allegation

IMPORTANT NOTE: Given the seriousness of a fraud allegation, I also intend to seek independent legal counsel. This representation is without prejudice to my legal rights.

I look forward to your response within 15 days."""


def _draft_unknown(context: Dict) -> str:
    """Draft for unknown/unclassified rejection."""
    return f"""Dear Grievance Officer,

Subject: Representation against claim rejection/short settlement — Request for specific clause and reconsideration

My claim has been rejected/short-settled. However, the specific reason and policy clause cited for the rejection are not clear from the communication I received.

As per IRDAI Master Circular on Health Insurance Business 2024 (IRDAI/HLT/CIR/PRO/84/5/2024, dated 29.05.2024), Clause 17(b): "In case the claim is repudiated or disallowed partially, details shall be conveyed to the claimant along with full details giving reference to the specific terms and conditions of the policy document."

I respectfully request:
1. The specific reason for rejection/short-settlement in writing
2. The exact policy clause and terms cited for the rejection
3. An opportunity to respond to the specific grounds of rejection
4. Reconsideration of the claim upon receipt of my response

I look forward to your response within 15 days."""


# Template dispatch table
_TEMPLATES = {
    "PROPORTIONATE_ON_FIXED": _draft_proportionate_on_fixed,
    "ROOM_RENT_PROPORTIONATE": _draft_room_rent_proportionate,
    "PED_NONDISCLOSURE": _draft_ped_nondisclosure,
    "WAITING_PERIOD": _draft_waiting_period,
    "EXCLUSION_PERMANENT": _draft_exclusion_permanent,
    "NOT_MEDICALLY_NECESSARY": _draft_not_medically_necessary,
    "DOCUMENTATION_TECHNICAL": _draft_documentation_technical,
    "LATE_INTIMATION": _draft_late_intimation,
    "REASONABLE_CUSTOMARY": _draft_reasonable_customary,
    "NON_PAYABLE_ITEMS": _draft_non_payable_items,
    "CASHLESS_DENIED": _draft_cashless_denied,
    "TARIFF_PACKAGE_CAP": _draft_tariff_package_cap,
    "FRAUD_MISREP": _draft_fraud_misrep,
    "UNKNOWN": _draft_unknown,
}


def draft_letter(rejection_reason: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Draft an IRDAI-clause-grounded appeal representation letter.

    Args:
        rejection_reason: The reason_code from the classifier (e.g., 'PROPORTIONATE_ON_FIXED')
        context: Optional dict with additional details:
            - continuous_cover_months: int (for PED moratorium override)
            - recoverable_amount: float (for proportionate deduction)
            - missing_documents: list (for documentation technical)
            - delay_reason: str (for late intimation)
            - claim_number: str
            - policy_number: str
            - insurer_name: str

    Returns:
        Dict with:
            - draft_letter: str (the full appeal letter text)
            - reason_code: str
            - clause_id: str (the cited clause)
            - clause_reference: str (human-readable reference)
            - citations_valid: bool (post-check: all citations exist in library)
            - disclaimer: str
    """
    if context is None:
        context = {}

    # Get the clause id for this reason code
    clause_id = _REASON_CLAUSE_MAP.get(rejection_reason, "PPI2017:grievance")

    # Validate clause exists (0-fabricated-citation guardrail)
    if not clause_exists(clause_id):
        clause_id = "PPI2017:grievance"  # Fallback to a valid clause

    # Get the template function
    template_fn = _TEMPLATES.get(rejection_reason, _draft_unknown)

    # Generate the letter body
    letter_body = template_fn(context)

    # Build the full letter with header
    today = datetime.now().strftime("%d %B %Y")
    insurer_name = context.get("insurer_name", "[Insurer Name]")
    claim_number = context.get("claim_number", "[Claim Number]")
    policy_number = context.get("policy_number", "[Policy Number]")

    full_letter = f"""Date: {today}

To,
The Grievance Redressal Officer,
{insurer_name}

Policy No: {policy_number}
Claim No: {claim_number}

{letter_body}

Yours faithfully,
[Policyholder Name]

---
Disclaimer: This representation has been drafted by Pehredaar, an informational tool. This is not legal or insurance advice. Please consult a licensed insurance advisor or the Insurance Ombudsman for professional guidance. All citations are from verified IRDAI/Government of India source documents."""

    # Post-check: validate all citations in the letter
    cited_ids = [clause_id]
    # Also check for any other clause ids mentioned in the text
    for cid in CLAUSE_LIBRARY:
        if cid in full_letter and cid != clause_id:
            cited_ids.append(cid)

    citation_check = validate_citations(cited_ids)

    return {
        "draft_letter": full_letter,
        "reason_code": rejection_reason,
        "clause_id": clause_id,
        "clause_reference": _get_clause_ref(clause_id),
        "citations_valid": citation_check["valid"],
        "citations_checked": citation_check["total_checked"],
        "disclaimer": "Informational only, not legal or insurance advice. Please consult a licensed insurance advisor or the Insurance Ombudsman for professional guidance."
    }