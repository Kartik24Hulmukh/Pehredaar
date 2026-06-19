# Pehredaar — Product Specification (v2: Discharge Defender + ClaimBack)

> **One line:** A WhatsApp-first guardian that protects an Indian patient's money at the two moments it actually gets destroyed — the **discharge desk** (proportionate deduction + non-payable trap, caught *before you sign*) and the **claim rejection** (an IRDAI-grounded appeal that fights back).

---

## 0. Why this, and why not the old plan

The original "Bill Pehredaar" (post-hoc bill audit vs NPPA/CGHS) already exists in India: **Jaanch, Evaakil, NYVO**, plus the government's own Pharma Sahi Daam app, plus ChatGPT. Building it would be re-shipping a solved problem.

The deep research found that the real, unproductized money pain in India is NOT understanding the bill *after* — it is two specific moments:

1. **Proportionate Deduction at discharge.** If your room exceeds the policy sub-limit, the insurer slashes your *entire* bill (surgery, ICU, doctor) proportionally. It hits at discharge when it is too late. Documented, viral, devastating (₹2.85L claims cut to half).
2. **Claim rejection.** ~11% of Indian health claims rejected; ₹26,000 cr disallowed in a single year (IRDAI FY24). <1% of people ever appeal. No serious Indian appeal-generator exists (the US has Claimable, Counterforce, Fight Health Insurance, Aegis).

**Pehredaar v2 = catch the deduction BEFORE the signature (Discharge Defender) + win the money back AFTER a rejection (ClaimBack).** Every competitor is post-mortem and detection-only. This is pre-signature + resolution. That is the white space.

---

## 1. Scope

### In scope (v1 launch)
- **Module A — Discharge Defender (the wedge):** real-time, pre-signature deduction + non-payable estimate from policy terms + room category + running/final bill.
- **Module B — ClaimBack:** AI-drafted, IRDAI-clause-grounded appeal letter for a rejected/short-settled claim, with the escalation route (insurer grievance → IRDAI Bima Bharosa / Ombudsman) and deadlines.
- **Shared core (reused ~60% from old plan):** bill OCR → structured JSON; NPPA/CGHS/IRDAI rule engine; plain-language explainer; PII redaction; WhatsApp + web entry.

### Out of scope (v1)
- Negotiating with the hospital on the user's behalf (advisory only — we arm the user).
- Acting as an insurance broker / IRDAI-regulated advisor (we are an information + drafting tool; see Legal §8).
- Procedure/consumable price *adjudication* as legal truth (CGHS = reference benchmark, not a cap; see §8).
- Filing the claim itself into insurer portals (we generate the artifact; user submits).

---

## 2. Users & primary journeys

### Persona 1 — "At the desk" (Discharge Defender)
Family member standing at the discharge counter, or admitted and about to choose a room. Non-expert, panicked, time-pressured, often on mobile-only / WhatsApp.

**Journey A — pre-admission room choice**
1. User sends policy name + sum insured + room category being offered.
2. Pehredaar returns: "Your policy caps room at ₹X/day (or Y% of SI). The ₹Z room you're being offered triggers Proportionate Deduction — this can cut ~P% from your ENTIRE bill including surgery and ICU, not just the room. Estimated loss on a ₹L bill: ₹D. Options: (a) ask for a room at/under cap, (b) get written confirmation of no-deduction, (c) proceed knowingly."

**Journey B — at discharge, before signing**
1. User uploads the final itemised bill + names their policy.
2. Pehredaar flags, with citations: (i) proportionate-deduction exposure, (ii) IRDAI non-payable items wrongly loaded onto the patient, (iii) NPPA medicine ceiling breaches, (iv) duplicate/arithmetic errors.
3. Output: a 1-page "Before You Sign" sheet + a polite query script for the billing desk.

### Persona 2 — "Rejected" (ClaimBack)
User whose cashless was denied, claim rejected, or settlement came back far short.

**Journey C — appeal**
1. User uploads rejection/short-settlement letter + policy + bills.
2. Pehredaar classifies the rejection reason, checks it against IRDAI Master Circular / policy clauses, and tells the user honestly: *winnable / partly winnable / weak*.
3. If winnable, it drafts: (a) a representation to the insurer grievance cell, (b) the escalation path + deadlines (insurer 15 days → IRDAI Bima Bharosa → Insurance Ombudsman), citing the exact clause.

---

## 3. Functional requirements

### 3.1 Discharge Defender engine
- **F-A1 Policy parser.** Accept policy name (lookup table of common plans) OR uploaded policy schedule. Extract: room-rent limit (absolute ₹ or % of SI), ICU limit, sub-limits (disease-wise/cataract/knee), co-pay %, deductible, restoration, non-payable handling.
- **F-A2 Proportionate-deduction calculator (deterministic).** Given room cap C, actual room R, and associated charges, compute the proportionate factor and the rupee exposure. Show the formula transparently. Never hide the math.
- **F-A3 Non-payable detector.** Match line items against the IRDAI Master Circular non-payable list (gloves, syringes, admin/registration/documentation fees, etc.). Flag items that should be billed to patient vs absorbed.
- **F-A4 NPPA/CGHS line check (reused).** Medicine MRP vs NPPA ceiling (DPCO 2013); ceiling × 1.30 for in-house dispensing; procedure benchmark vs CGHS (clearly labeled "reference, not legal cap").
- **F-A5 "Before You Sign" sheet generator.** 1-page output: total exposure, top 5 flags, the desk-query script, what to ask in writing.

### 3.2 ClaimBack engine
- **F-B1 Rejection classifier.** Map the rejection letter to a taxonomy: room-rent/proportionate, non-disclosure/PED, waiting-period, exclusion, documentation/technical, "not medically necessary," tariff/reasonable-customary.
- **F-B2 Winnability scorer (honest).** Each reason → rules-based winnability with the governing IRDAI clause and known precedent/ombudsman pattern. Output green/amber/red + plain reasoning. NEVER over-promise.
- **F-B3 Appeal drafter (AI, grounded).** Draft representation citing the exact clause; AI may only cite from the curated clause library — it cannot invent a citation (same guardrail as the bill engine).
- **F-B4 Escalation router.** Insurer grievance → IRDAI Bima Bharosa portal → Insurance Ombudsman, with the correct jurisdiction, monetary limits, and statutory deadlines.

### 3.3 Shared core (reused from v1)
- **F-C1 Bill ingestion + OCR → JSON** (vision model for bill reading; Surya/Qwen2.5-VL fallback).
- **F-C2 Medicine normalization:** brand→generic, strength/pack matching (RapidFuzz + drug NER + embeddings), price DB (NPPA + 1mg/India Drug Bank).
- **F-C3 Citation engine:** every flag carries verbatim source + source date. AI cannot fabricate a citation.
- **F-C4 PII redaction** before any model call (DPDP Act 2023): name, UHID, policy no., phone, Aadhaar.
- **F-C5 Channels:** WhatsApp (primary) + lightweight web upload. Vernacular output (Hindi first, then regional).
- **F-C6 Shareable artifact:** a "Receipt of Justice" card (anonymized) for the growth loop.

---

## 4. Non-functional requirements
- **Latency:** Discharge Defender first response < 30s (people are literally at the desk).
- **Availability:** 24/7 (emergencies/discharges are not 9-5). VPS + queue + idempotency.
- **Privacy:** PII scrubbed pre-model; originals purged after 30 days; no training on user docs.
- **Cost:** target < ₹3 per full analysis (vision read is the main cost driver).
- **Trust:** never the word "fraud"; always "possible error / review with the desk." Show the math and the source.

---

## 5. Data sources & coverage honesty
| Layer | Source | Confidence |
|---|---|---|
| Medicine ceiling | NPPA DPCO 2013 + S.O. notifications | High (legally binding MRP cap) |
| Medicine MRP | 1mg / India Drug Bank (Kaggle) | High for matched brands |
| Non-payables | IRDAI Master Circular list | High |
| Proportionate deduction | Policy schedule terms | High when policy parsed; estimate otherwise |
| Procedure rate | CGHS schedule (2,584 procedures) | Medium — reference benchmark, NOT a legal cap |
| Consumables | partial | Low — flag as "verify" |
| Policy sub-limits | plan lookup table + uploaded schedule | Medium → High |

**Honesty rule:** the product states its own confidence per flag. Weak coverage is labeled, never bluffed.

---

## 6. Canonical data schema
```
medicine/procedure record:
  canonical_name, generic, strength, pack, price, mrp,
  kind (drug|procedure|consumable), source, source_date

policy record:
  plan_name, insurer, room_cap_type (abs|pct), room_cap_value,
  icu_cap, copay_pct, deductible, sublimits[], non_payable_policy,
  source (lookup|uploaded), source_date

rejection record:
  reason_code, governing_clause, winnability (green|amber|red),
  rationale, escalation_path[], deadline_days
```

---

## 7. AI / model routing
- **Bill/policy vision read:** Sonnet 4.5 (vision) → JSON. Local Qwen2.5-VL / Surya OCR fallback for cost.
- **Explainer + appeal drafting:** mid model (open-source via OpenRouter) for cost; Opus 4.6 reserved for hard adjudication only.
- **Deterministic core (deduction math, ceiling checks, non-payable match):** pure code, NO model. The model never decides a number that law decides.
- **Guardrail:** model output is constrained to the curated citation library; a post-check rejects any answer containing an unsourced citation.

---

## 8. Legal / compliance guardrails
- **CGHS is a reference benchmark, not a legal price cap** — never assert a CGHS-based "overcharge" as illegal. Defamation risk.
- **Medicine MRP is legally binding** (Legal Metrology Act 2009); NPPA ceiling caps the MRP (DPCO). These CAN be asserted with citation.
- **Not insurance advice:** Pehredaar is an information + document-drafting tool, not an IRDAI-regulated intermediary. Clear disclaimer; "consult a licensed advisor / ombudsman."
- **DPDP Act 2023:** consent, PII redaction, 30-day purge, no model training on user data.
- **Tone:** "possible error," "you may ask the desk to review," never "the hospital cheated you."

---

## 9. Success metrics
- **North star:** total rupees protected (deduction avoided + claim recovered), self-reported + verified sample.
- Activation: % of users who get a flag with a rupee number.
- Traction loop: shares of the "Receipt of Justice" card → new sessions.
- ClaimBack: appeal-drafted → user-reported reversal rate.
- Honesty integrity: % of flags carrying a valid citation (target 100%; 0 fabricated).

---

## 10. Risks (carried into BUILD-PLAN premortem)
1. **Policy data is messy** — sub-limits vary per plan. Mitigation: start with top ~20 plans lookup + uploaded-schedule parsing; label estimates.
2. **Agents will stub the matcher/calculator and claim it works.** Mitigation: labeled golden test set as a green-blocking gate; builder NEVER writes the verifier.
3. **Over-promising winnability** → user harm + legal exposure. Mitigation: conservative scorer, honest red/amber, disclaimers.
4. **Vision OCR errors on photographed bills.** Mitigation: confidence threshold + ask-user-to-confirm extracted lines.
5. **WhatsApp provider ToS / number bans.** Mitigation: compliant BSP path planned; OpenWA only for prototype.
