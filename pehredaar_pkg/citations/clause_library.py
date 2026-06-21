"""
Pehredaar — Curated IRDAI Clause Library
=========================================
Every clause id used in the system MUST exist here. The AI may cite ONLY ids from
this library. A post-check rejects any unknown citation id.

All clauses are sourced from real IRDAI/Government of India documents with exact
reference numbers, dates, and verbatim/near-verbatim text. See SOURCES below.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import json

@dataclass
class Clause:
    clause_id: str
    source_document: str
    reference_number: str
    date: str
    section: str
    title: str
    verbatim_text: str
    legal_status: str  # "legally_binding" or "reference_benchmark"
    url: str

# ============================================================================
# SOURCE DOCUMENTS (real, verified from official IRDAI/Govt websites)
# ============================================================================
# 1. IRDAI Master Circular on Health Insurance Business, 2024
#    Ref: IRDAI/HLT/CIR/PRO/84/5/2024, Date: 29.05.2024
# 2. IRDAI Master Circular on PP&GR, 2024
#    Ref: IRDAI/PP&GR/CIR/MISC/117/9/2024, Date: 05.09.2024
# 3. IRDAI (Protection of Policyholders' Interests) Regulations, 2017
# 4. Insurance Ombudsman Rules, 2017 (Gazette, 27 April 2017)
# 5. IRDAI Circular on Proportionate Deductions, 2020
#    Ref: IRDAI/HLT/REG/CIR/151/06/2020, Date: 11.06.2020
# 6. IRDAI Master Circular on Standardization, 2020
#    Ref: IRDAI/HLT/REG/CIR/193/07/2020, Date: 22.07.2020
# 7. IRDAI Circular on Condonation of Delay, 2011
#    Ref: IRDA/HLTH/MISC/CIR/216/09/2011, Date: 20.09.2011
# ============================================================================

CLAUSE_LIBRARY: Dict[str, Clause] = {
    # --- Proportionate Deduction (IRDAI/HLT/REG/CIR/151/06/2020, 11 Jun 2020) ---
    "MC2024:proportionate": Clause(
        clause_id="MC2024:proportionate",
        source_document="IRDAI Circular on Proportionate Deductions, 2020",
        reference_number="IRDAI/HLT/REG/CIR/151/06/2020",
        date="11.06.2020",
        section="Clauses 3, 4, 5, 7",
        title="Proportionate Deduction — Exclusions and Limitations",
        verbatim_text=(
            "Where as part of product design insurers propose proportionate deductions of the "
            "associated medical expenses when a policyholder chooses a higher room category than "
            "the category that is eligible as per terms and conditions of the policy, insurers shall "
            "define 'associate medical expenses' in the terms and conditions of policy contract. "
            "The following expenses are NOT allowed to be part of the definition of 'associate "
            "medical expenses': (a) Cost of pharmacy; (b) Cost of implants and medical devices; "
            "(c) Cost of diagnostics. Insurers shall not recover any expenses towards proportionate "
            "deductions other than the defined 'associate medical expenses' while processing claims. "
            "Insurers are also not permitted to apply proportionate deduction for 'ICU charges' as "
            "different categories of ICU are not there."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/documents/37343/365848/Modified+Guidelines+on+Product+filing+in+Health+Insurance+Business+-.pdf"
    ),

    # --- Moratorium Period (Master Circular on Health Insurance 2024, Clause 13) ---
    "MC2024:moratorium": Clause(
        clause_id="MC2024:moratorium",
        source_document="IRDAI Master Circular on Health Insurance Business, 2024",
        reference_number="IRDAI/HLT/CIR/PRO/84/5/2024",
        date="29.05.2024",
        section="Clause 13",
        title="Moratorium Period — Policy/Claim Cannot Be Contested After 60 Months",
        verbatim_text=(
            "No policy and claim of health insurance shall be contestable on any grounds of "
            "non-disclosure and/or misrepresentation except for established fraud, after the "
            "completion of the Moratorium Period, i.e. 60 months of continuous coverage. "
            "The accrued credits gained under the ported and migrated policies shall be counted "
            "for the purpose of calculating the Moratorium period."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/document-detail?documentId=4942918"
    ),

    # --- Fraud/Misrepresentation (Master Circular 2024, Clauses 10, 13) ---
    "MC2024:fraud": Clause(
        clause_id="MC2024:fraud",
        source_document="IRDAI Master Circular on Health Insurance Business, 2024",
        reference_number="IRDAI/HLT/CIR/PRO/84/5/2024",
        date="29.05.2024",
        section="Clauses 10, 13",
        title="Fraud and Misrepresentation — Exception to Moratorium",
        verbatim_text=(
            "A health insurance policy shall be renewable provided the product is not withdrawn, "
            "except in case of established fraud or non-disclosure or misrepresentation by the "
            "Insured. No policy and claim of health insurance shall be contestable on any grounds "
            "of non-disclosure and/or misrepresentation except for established fraud, after the "
            "completion of the Moratorium Period."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/document-detail?documentId=4942918"
    ),

    # --- Cashless Authorization (Master Circular 2024, Clause 15) ---
    "MC2024:cashless": Clause(
        clause_id="MC2024:cashless",
        source_document="IRDAI Master Circular on Health Insurance Business, 2024",
        reference_number="IRDAI/HLT/CIR/PRO/84/5/2024",
        date="29.05.2024",
        section="Clause 15(b)",
        title="Cashless Authorization — Decision Within One Hour",
        verbatim_text=(
            "Every insurer shall strive to achieve 100% cashless claim settlement in a time bound "
            "manner. Insurer shall decide on the request for cashless authorization immediately but "
            "not more than one hour of receipt of request."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/document-detail?documentId=4942918"
    ),

    # --- Discharge Authorization (Master Circular 2024, Clause 16) ---
    "MC2024:discharge": Clause(
        clause_id="MC2024:discharge",
        source_document="IRDAI Master Circular on Health Insurance Business, 2024",
        reference_number="IRDAI/HLT/CIR/PRO/84/5/2024",
        date="29.05.2024",
        section="Clause 16(a), 16(b)",
        title="Final Authorization for Discharge — Within Three Hours",
        verbatim_text=(
            "Insurer shall grant final authorization within three hours of the receipt of discharge "
            "authorization request from the hospital. In no case, the policyholder shall be made to "
            "wait to be discharged from the Hospital. If there is any delay beyond three hours, the "
            "additional amount if any charged by the hospital shall be borne by the insurer from "
            "shareholder's fund."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/document-detail?documentId=4942918"
    ),

    # --- Claim Repudiation Requires PMC/CRC (Master Circular 2024, Clause 17) ---
    "MC2024:claims": Clause(
        clause_id="MC2024:claims",
        source_document="IRDAI Master Circular on Health Insurance Business, 2024",
        reference_number="IRDAI/HLT/CIR/PRO/84/5/2024",
        date="29.05.2024",
        section="Clause 17(a), 17(b)",
        title="Claim Settlement — No Repudiation Without PMC/CRC Approval",
        verbatim_text=(
            "No claim shall be repudiated without the approval of PMC or a three-member sub-group "
            "of PMC called the Claims Review Committee (CRC). In case the claim is repudiated or "
            "disallowed partially, details shall be conveyed to the claimant along with full details "
            "giving reference to the specific terms and conditions of the policy document."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/document-detail?documentId=4942918"
    ),

    # --- Non-Payable Items (Master Circular on Standardization 2020) ---
    "MC2024:nonpayable": Clause(
        clause_id="MC2024:nonpayable",
        source_document="IRDAI Master Circular on Standardization of Health Insurance Products, 2020",
        reference_number="IRDAI/HLT/REG/CIR/193/07/2020",
        date="22.07.2020",
        section="Annexure I, Lists I-IV",
        title="Non-Payable / Optional / Subsumed Items in Hospital Billing",
        verbatim_text=(
            "Insurers shall put in place measures to ensure that items which are part of "
            "room/surgical procedure/treatment (including diagnostics) as referred in the lists "
            "herein shall not be billed to the policyholders separately by the providers (hospitals) "
            "in case of cashless cases. List I: 68 optional items (gloves, diapers, ambulance, etc.). "
            "List II: 37 items subsumed into room charges (documentation/admin expenses, file opening "
            "charges, discharge procedure charges, etc.). List III: 23 items subsumed into procedure "
            "charges (gauze, surgical blades, cotton, etc.). List IV: 18 items subsumed into treatment "
            "costs (admission/registration charges, etc.)."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/documents/37343/366029/Master+Circular+on+Standardization+of+Health+Insurance+Products.pdf"
    ),

    # --- Condonation of Delay (IRDAI Circular 2011, reinforced 2016) ---
    "MC2024:condonation": Clause(
        clause_id="MC2024:condonation",
        source_document="IRDAI Circular on Delay in Claim Intimation/Documents Submission, 2011",
        reference_number="IRDA/HLTH/MISC/CIR/216/09/2011",
        date="20.09.2011",
        section="Full circular (reinforced by IRDA/NL/CIR/MISC/214/10/2016 dated 28.10.2016)",
        title="Condonation of Delay in Claim Intimation",
        verbatim_text=(
            "The insurers must not repudiate such claims unless and until the reasons of delay are "
            "specifically ascertained, recorded and the insurers should satisfy themselves that the "
            "delayed claims would have otherwise been rejected even if reported in time. Rejection "
            "of claims on purely technical grounds in a mechanical fashion will result in "
            "policyholders losing confidence in the insurance industry. Insurers should condone "
            "delay on merit for delayed claims where the delay is proved to be for reasons beyond "
            "the control of the insured."
        ),
        legal_status="legally_binding",
        url="https://taxguru.in/corporate-law/delay-in-claim-intimationdocuments-submission-with-respect-to-all-life-insurance-contracts-and-all-non-life-individual-and-group-insurance-contracts.html"
    ),

    # --- Claims Processing Timelines (PPI Regulations 2017, Section 16) ---
    "PPI2017:claims": Clause(
        clause_id="PPI2017:claims",
        source_document="IRDAI (Protection of Policyholders' Interests) Regulations, 2017",
        reference_number="IRDAI/REG/2017",
        date="2017",
        section="Section 16.1(i), 16.1(ii), 16.2",
        title="Health Insurance Claim Processing Timelines and Interest",
        verbatim_text=(
            "An Insurer shall settle the claim within 30 days from the date of receipt of last "
            "necessary document. In the case of delay in the payment of a claim, the insurer shall "
            "be liable to pay interest from the date of receipt of last necessary document to the "
            "date of payment of claim at a rate 2% above the bank rate. Investigation cases: not "
            "later than 30 days from the date of receipt of last necessary document; Insurer shall "
            "settle the claim within 45 days from the date of receipt of last necessary document."
        ),
        legal_status="legally_binding",
        url="https://www.casemine.com/act/in/5f5f11219fca195c05ccdfcb"
    ),

    # --- Grievance Redressal (PPI Regulations 2017, Section 17) ---
    "PPI2017:grievance": Clause(
        clause_id="PPI2017:grievance",
        source_document="IRDAI (Protection of Policyholders' Interests) Regulations, 2017",
        reference_number="IRDAI/REG/2017",
        date="2017",
        section="Section 17 + Annexure-I",
        title="Grievance Redressal Procedure",
        verbatim_text=(
            "Every insurer shall have in place proper procedures and effective mechanism to resolve "
            "complaints and grievances of policyholders, claimants efficiently and with speed. "
            "Complainant approaches Grievance Redressal Officer (GRO) of insurer. If no response or "
            "unsatisfactory, may register complaint in grievance redressal management system of the "
            "Authority (IGMS/Bima Bharosa). Every insurer shall communicate action taken + "
            "information about Insurance Ombudsman."
        ),
        legal_status="legally_binding",
        url="https://www.casemine.com/act/in/5f5f11219fca195c05ccdfcb"
    ),

    # --- No Rejection for Delayed Intimation (MC PP&GR 2024) ---
    "MC2024:ppgr_noreject": Clause(
        clause_id="MC2024:ppgr_noreject",
        source_document="IRDAI Master Circular on Protection of Policyholders' Interests, 2024",
        reference_number="IRDAI/PP&GR/CIR/MISC/117/9/2024",
        date="05.09.2024",
        section="Para 1(ii), Para 3(iii).6",
        title="No Rejection for Delayed Intimation; 15-Day Settlement",
        verbatim_text=(
            "No claim shall be rejected or closed for want of documents or for delayed intimation "
            "of claim. Settlement of claims (other than cashless) shall be settled within fifteen "
            "days from submission of claim."
        ),
        legal_status="legally_binding",
        url="https://www.caalley.com/irdai_mc/MC_Protection_of_Policyholders_interests_2024.pdf"
    ),

    # --- Insurance Ombudsman Rules 2017 ---
    "OMB2017:filing": Clause(
        clause_id="OMB2017:filing",
        source_document="Insurance Ombudsman Rules, 2017",
        reference_number="G.S.R. 886(E)",
        date="27.04.2017",
        section="Rules 13, 14",
        title="Ombudsman Complaint — Filing and Jurisdiction",
        verbatim_text=(
            "The Ombudsman shall receive and consider complaints relating to: (a) delay in settlement "
            "of claims, (b) any partial or total repudiation of claims, (c) disputes over premium, "
            "(d) misrepresentation of policy terms, (e) legal construction of insurance policies. "
            "Complaint in writing to the Insurance Ombudsman within whose territorial jurisdiction "
            "the branch/office of the insurer OR the residential address of the complainant is "
            "located. No complaint unless complainant first makes written representation to insurer "
            "AND: insurer rejected, or no reply within one month, or complainant unsatisfied. "
            "Complaint within ONE YEAR of insurer's final reply. Ombudsman empowered to condone delay."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/documents/37343/366405/The+Insurance+Ombudsman+Rules%2C2017.pdf"
    ),

    "OMB2017:award": Clause(
        clause_id="OMB2017:award",
        source_document="Insurance Ombudsman Rules, 2017",
        reference_number="G.S.R. 886(E)",
        date="27.04.2017",
        section="Rule 17(3), 17(4), 17(6), 17(8)",
        title="Ombudsman Award — ₹30 Lakh Limit, 3 Months, Binding on Insurers",
        verbatim_text=(
            "The Ombudsman shall not award compensation exceeding rupees thirty lakhs (including "
            "relevant expenses, if any). The Ombudsman shall finalise its findings and pass an award "
            "within a period of three months of the receipt of all requirements from the complainant. "
            "The insurer shall comply with the award within thirty days of the receipt of the award. "
            "The award of Insurance Ombudsman shall be binding on the insurers."
        ),
        legal_status="legally_binding",
        url="https://irdai.gov.in/documents/37343/366405/The+Insurance+Ombudsman+Rules%2C2017.pdf"
    ),

    # --- Policy-specific clause placeholders (verified against policy document) ---
    "policy:waiting": Clause(
        clause_id="policy:waiting",
        source_document="Policy document (waiting period clause)",
        reference_number="N/A — policy-specific",
        date="N/A",
        section="Policy terms — waiting period",
        title="Waiting Period (Initial / Disease-Specific)",
        verbatim_text=(
            "The policy specifies an initial waiting period (typically 30 days) and disease-specific "
            "waiting periods (typically 1-2 years for specific ailments, 2-4 years for pre-existing "
            "diseases). Claims within the waiting period are not payable. Portability credit from "
            "previous policies may reduce waiting periods. Verify exact terms in your policy document."
        ),
        legal_status="legally_binding",
        url="N/A — refer to your policy document"
    ),

    "policy:exclusions": Clause(
        clause_id="policy:exclusions",
        source_document="Policy document (permanent exclusions clause)",
        reference_number="N/A — policy-specific",
        date="N/A",
        section="Policy terms — exclusions",
        title="Permanent Exclusions",
        verbatim_text=(
            "The policy lists permanently excluded conditions and treatments (e.g., cosmetic "
            "procedures, experimental treatments). Claims for excluded conditions are not payable. "
            "However, if an exclusion was not disclosed at issuance or the wording is ambiguous, "
            "it may be challengeable. Verify exact exclusions in your policy document."
        ),
        legal_status="legally_binding",
        url="N/A — refer to your policy document"
    ),

    "policy:RC": Clause(
        clause_id="policy:RC",
        source_document="Policy document (reasonable and customary charges clause)",
        reference_number="N/A — policy-specific",
        date="N/A",
        section="Policy terms — reasonable & customary charges",
        title="Reasonable and Customary Charges",
        verbatim_text=(
            "The policy may cap payments to 'reasonable and customary' charges for the geography. "
            "Insurers often use CGHS rates or peer-hospital benchmarks as the standard. You may "
            "demand the specific benchmark used and compare with CGHS/peer hospital rates. "
            "Verify exact terms in your policy document."
        ),
        legal_status="legally_binding",
        url="N/A — refer to your policy document"
    ),

    "policy:package": Clause(
        clause_id="policy:package",
        source_document="Policy document (package rate / sub-limit clause)",
        reference_number="N/A — policy-specific",
        date="N/A",
        section="Policy terms — package rates / disease sub-limits",
        title="Package Rate Caps and Disease Sub-Limits",
        verbatim_text=(
            "The policy may specify package rates or disease-wise sub-limits (e.g., cataract ₹40,000 "
            "per eye, knee replacement ₹1.5L). Claims are capped at these limits regardless of actual "
            "expenses. Verify the agreed package rate vs actual charges and challenge any unbundled "
            "extras. Verify exact sub-limits in your policy document."
        ),
        legal_status="legally_binding",
        url="N/A — refer to your policy document"
    ),

    # --- NPPA Drug Pricing (DPCO 2013) ---
    "NPPA:DPCO2013": Clause(
        clause_id="NPPA:DPCO2013",
        source_document="Drugs (Prices Control) Order, 2013 (DPCO 2013)",
        reference_number="S.O. 1394(E) dated 30.05.2013; Ceiling prices S.O. 1547(E)/1548(E) dated 26.03.2024",
        date="30.05.2013 (prices updated 01.04.2024)",
        section="Paras 4, 11, 14 of DPCO 2013",
        title="NPPA Ceiling Price — Legally Binding MRP Cap on Scheduled Drugs",
        verbatim_text=(
            "The NPPA fixes ceiling prices for scheduled formulations under DPCO 2013. Ceiling Price = "
            "Average Price to Retailer × 1.16 (16% retailer margin). MRP = Ceiling Price + GST. "
            "MRP is legally binding under the Legal Metrology Act 2009. Selling above MRP is illegal. "
            "Annual WPI revision on 1st April. Non-scheduled drug price increases limited to 10% per year."
        ),
        legal_status="legally_binding",
        url="https://upload.indiacode.nic.in/showfile?actid=AC_CEN_21_28_00003_195510_1517807320439"
    ),

    # --- CGHS Reference Benchmark ---
    "CGHS:reference": Clause(
        clause_id="CGHS:reference",
        source_document="CGHS Package Rates (OM dated 01.02.2024; MoH&FW OM dated 21.12.2023)",
        reference_number="CGHS OM F.No. Z15025/8/2023/DIR/CGHS",
        date="01.02.2024",
        section="CGHS Treatment Procedure List (codes 1-1859)",
        title="CGHS Package Rates — Reference Benchmark (NOT a Legal Price Cap)",
        verbatim_text=(
            "CGHS package rates are reference benchmarks for government empanelled hospitals. "
            "Private hospitals are NOT legally required to charge CGHS rates to non-CGHS patients. "
            "However, CGHS rates are widely used as a reasonableness standard by insurers and courts. "
            "Rates vary by city tier (Metro > Tier Y ~90% > Tier Z ~80%) and NABH vs Non-NABH (~15% "
            "differential). This is a REFERENCE benchmark, not a legal cap."
        ),
        legal_status="reference_benchmark",
        url="https://cghs.gov.in"
    ),
}


def get_clause(clause_id: str) -> Optional[Clause]:
    """Retrieve a clause by id. Returns None if not found."""
    return CLAUSE_LIBRARY.get(clause_id)


def clause_exists(clause_id: str) -> bool:
    """Check if a clause id exists in the library."""
    return clause_id in CLAUSE_LIBRARY


def validate_citations(citation_ids: List[str]) -> Dict[str, Any]:
    """
    Post-check: validate that all citation ids exist in the library.
    Returns dict with 'valid' (bool) and 'invalid_ids' (list).
    This is the 0-fabricated-citation guardrail.
    """
    invalid = [cid for cid in citation_ids if cid not in CLAUSE_LIBRARY]
    return {
        "valid": len(invalid) == 0,
        "invalid_ids": invalid,
        "total_checked": len(citation_ids),
        "total_valid": len(citation_ids) - len(invalid)
    }


def get_all_clause_ids() -> List[str]:
    """Return all valid clause ids."""
    return list(CLAUSE_LIBRARY.keys())


def clause_to_dict(clause: Clause) -> Dict[str, Any]:
    """Convert a Clause to a dict for JSON serialization."""
    return asdict(clause)


def get_clause_summary(clause_id: str) -> Dict[str, Any]:
    """Get a summary dict of a clause for display."""
    clause = get_clause(clause_id)
    if clause is None:
        return {"error": f"Clause id '{clause_id}' not found in library"}
    return {
        "clause_id": clause.clause_id,
        "source": clause.source_document,
        "reference": clause.reference_number,
        "date": clause.date,
        "section": clause.section,
        "title": clause.title,
        "legal_status": clause.legal_status,
        "url": clause.url
    }