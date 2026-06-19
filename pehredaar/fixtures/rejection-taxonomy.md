# ClaimBack — Rejection Reason Taxonomy + Expected Labels (golden)

The classifier maps a rejection/short-settlement letter to ONE primary `reason_code` (plus optional secondary), a `governing_clause` id from the curated library, and a default `winnability`. The scorer may downgrade but must NEVER upgrade a `red` to `green` without an explicit documented override rule.

> Clause library ids reference: IRDAI Master Circular on Health Insurance 2024 (`MC2024:§x`), Protection of Policyholders' Interests Regulations 2017 (`PPI2017:§x`), Insurance Ombudsman Rules 2017 (`OMB2017:§x`). Replace `§x` with the exact verified section when you build the library. The model may cite ONLY ids that exist in the library.

| reason_code | What insurer says | Default winnability | Governing clause | Core argument / next step |
|---|---|---|---|---|
| `ROOM_RENT_PROPORTIONATE` | Cut whole bill because room > sub-limit | **amber** | MC2024:proportionate | Valid for room-linked variable charges; **challenge if applied to medicines/implants/consumables/diagnostics** (price independent of room). Recompute, demand refund of wrong deduction. |
| `PROPORTIONATE_ON_FIXED` | Applied proportionate cut to pharmacy/implants | **green** | MC2024:proportionate | Fixed-price items must not be proportionately reduced. Strong refund case (see fixture S7). |
| `PED_NONDISCLOSURE` | Pre-existing disease not disclosed | **red→amber** | MC2024:moratorium | If policy crossed the **moratorium period (60 months continuous cover)**, claim cannot be contested for non-disclosure (except fraud). Check tenure first. |
| `WAITING_PERIOD` | Within initial/disease waiting period | **red** | policy:waiting | Usually valid. Amber only if insurer miscounted continuous coverage / portability credit. |
| `EXCLUSION_PERMANENT` | Permanently excluded condition/item | **red** | policy:exclusions | Valid unless exclusion not disclosed at issuance or ambiguous wording. |
| `NOT_MEDICALLY_NECESSARY` | Hospitalisation/procedure not warranted | **amber** | PPI2017:claims | Challengeable with treating-doctor justification + clinical notes. Strong if admission was advised in writing. |
| `DOCUMENTATION_TECHNICAL` | Missing/insufficient documents | **green** | PPI2017:claims | Almost always fixable — resubmit the named document. Cannot be a final rejection if curable. |
| `LATE_INTIMATION` | Claim intimated after deadline | **amber** | MC2024:condonation | 2024 circular: a claim **cannot be rejected solely for delay** if the delay had genuine cause. Provide reason. |
| `REASONABLE_CUSTOMARY` | Charges above reasonable & customary | **amber** | policy:RC | Demand the benchmark used; compare with CGHS/peer hospital; negotiate the disallowance. |
| `NON_PAYABLE_ITEMS` | Consumables/admin items disallowed | **green (partial)** | MC2024:nonpayable | Only those specific items are non-payable — NOT the whole claim. Ensure rest is paid. |
| `CASHLESS_DENIED` | Cashless pre-auth refused | **green** | MC2024:cashless | Denial of cashless ≠ claim rejection. File reimbursement post-discharge with full docs. |
| `TARIFF_PACKAGE_CAP` | Capped to package rate | **amber** | policy:package | Verify the agreed package vs actual; challenge unbundled extras. |
| `FRAUD_MISREP` | Alleged fraud/fabrication | **red** | MC2024:fraud | High bar for insurer to prove; needs legal counsel, not just an appeal letter. Escalate carefully. |

## Escalation ladder (router output)
1. **Insurer Grievance Redressal Officer (GRO)** — written representation; insurer must respond in **15 days** (PPI2017).
2. **IRDAI Bima Bharosa portal** (formerly IGMS) — if unresolved/unsatisfactory.
3. **Insurance Ombudsman** — jurisdiction by location; handles disputes up to **₹50 lakh** (OMB2017). File within **1 year** of insurer's final reply.
4. **Consumer Commission / civil court** — last resort.

## Winnability scorer rules (conservative)
- Never output `green` for `PED_NONDISCLOSURE`, `WAITING_PERIOD`, `EXCLUSION_PERMANENT`, `FRAUD_MISREP` without an explicit qualifying fact (e.g., moratorium crossed) present in input.
- Always attach the disclaimer: “Informational only, not legal/insurance advice.”
- If reason unclear → `amber` + request the specific clause the insurer cited.
