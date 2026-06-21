# Pehredaar v2 — Premortem (Discharge Defender + ClaimBack)

> Method: assume it's 12 months out and the product FAILED or got zero traction. Why? Each failure mode below has a likelihood, impact, and a concrete pre-mitigation baked into SPEC/BUILD-PLAN.

## A. Market / “someone already built it” failures

### A1. ClaimBack got cloned first — **Bima Buddy** (HIGH likelihood, HIGH impact) 🔴
A May 2026 Reddit launch (r/IndiaBusiness, r/indianstartups) describes an indie product, **Bima Buddy**, doing *exactly* the ClaimBack half: upload rejection + policy + bills → AI checks against IRDAI Master Circular 2024 + Ombudsman case law → 60-sec verdict (winnable? which clause? GRO→Bima Bharosa→Ombudsman). Pricing ₹199 + success fee. Plus established human-assisted players (SureClaim — raised $633K, now deadpooled; ClaimBuddy; ABI Health; Healspan; Care.fi).
- **Implication:** the claim-appeal generator is NO LONGER greenfield in India. It is being occupied right now.
- **Mitigation:** Do NOT lead with ClaimBack. Lead with **Discharge Defender** (still empty). Treat ClaimBack as a fast-follow module, and differentiate it via (a) WhatsApp-native + vernacular, (b) the deduction-recompute engine feeding the appeal with exact rupee math (Bima Buddy is text-only), (c) free core. Watch Bima Buddy's trajectory.

### A2. Discharge Defender turns out to exist (LOW likelihood, HIGH impact) 🟢→🟡
Searches found tons of *awareness content* (Beshak formula explainer, ACKO/insurer Instagram “check room rent before admission,” insurer premium calculators) but **NO real-time, pre-signature, bill-aware proportionate-deduction defender product.** This is the genuine wedge.
- **Risk:** an incumbent (Jaanch/Evaakil) bolts on a deduction calculator.
- **Mitigation:** speed + distribution + the WhatsApp at-desk flow (operationally hard) + compounding policy/clause library. The feature is copyable; the distribution + data asset is not (overnight).

### A3. ChatGPT/Gemini is “good enough” (MED likelihood, MED impact) 🟡
Users paste the bill into a free general chatbot.
- **Mitigation:** the moat is the *deterministic* deduction math + the *exact policy sub-limit + IRDAI clause* grounding a general chatbot won't reliably get right, plus the WhatsApp zero-friction flow for non-technical victims. Position as “the one that gets the number and the clause right, in your language, where you already chat.”

## B. Trust / correctness failures

### B4. A wrong number at the desk destroys trust (HIGH impact) 🔴
If the deduction estimate is wrong while the user is at the counter, we cause harm and lose all credibility.
- **Mitigation:** deterministic calculator gated by the 12 golden scenarios (exact match); show the formula + assumptions; label every estimate's confidence; “verify with the billing desk” framing; never present an estimate as final adjudication.

### B5. Over-promising winnability → user harm + legal exposure (HIGH impact) 🔴
- **Mitigation:** conservative scorer (red/amber defaults); never upgrade red→green without a qualifying fact; mandatory not-legal-advice disclaimer; honest “weak case” outputs.

### B6. The agent stubs the matcher/calculator and claims success (HIGH likelihood in a forge) 🔴
The plan's original Risk #5.
- **Mitigation:** builder has NO write access to verifier/fixtures; golden-set is green-blocking; mutation testing (Stryker/cargo-mutants) catches stubs; 0-fabricated-citation post-check.

### B7. Fabricated legal citations (HIGH impact) 🔴
- **Mitigation:** model may cite ONLY ids in the curated clause library; post-check rejects any unknown id; deterministic where law decides.

## C. Data failures

### C8. Policy sub-limits are messy / per-plan (HIGH likelihood, MED impact) 🟡
Every insurer words room caps differently (abs ₹ vs % of SI vs room-category bands; ICU separate; disease sub-limits).
- **Mitigation:** start with top ~20 plans as a curated lookup; accept uploaded policy schedule + parse; clearly label “estimate — confirm your policy.” The library compounds into the moat.

### C9. The IRDAI clause library is the bottleneck (MED) 🟡
Winnability quality = clause-library quality. Wrong section references = wrong advice.
- **Mitigation:** hand-curate + verify each clause id before launch; version + date it; never let the model invent sections (taxonomy ships with `§x` placeholders to force verification).

### C10. OCR errors on photographed bills (MED) 🟡
- **Mitigation:** confidence threshold + a “confirm these lines” step before computing; vision model + Surya/Qwen fallback.

## D. Distribution / channel failures

### D11. WhatsApp number bans / BSP ToS (MED likelihood, HIGH impact) 🔴
Unofficial automation (OpenWA) gets numbers banned; can kill the channel.
- **Mitigation:** OpenWA for prototype ONLY; migrate to a compliant BSP (official WhatsApp Business API) before scale; have web fallback.

### D12. The growth loop doesn't loop (MED) 🟡
If the “Receipt of Justice” card isn't share-worthy, CAC stays high.
- **Mitigation:** make the artifact emotional + specific (“stopped ₹82,000 being taken before signing”); seed in the exact Reddit/Insta threads where deduction stories already go viral; co-brand with finance creators who already explain this.

## E. Legal / regulatory failures

### E13. “You're giving insurance advice” (MED likelihood, HIGH impact) 🔴
IRDAI regulates intermediaries; positioning as an advisor invites trouble.
- **Mitigation:** strictly an information + document-drafting tool; disclaimers; point to ombudsman/licensed advisor; don't take a cut of insurance sales.

### E14. Defamation — calling a hospital a cheat (MED impact) 🟡
- **Mitigation:** never “fraud”; “possible error, please review”; CGHS = reference benchmark, not a legal cap; only assert legally-binding facts (NPPA/MRP) with citation.

### E15. DPDP Act 2023 — health PII (HIGH impact) 🔴
- **Mitigation:** consent; PII redaction pre-model; 30-day purge; no training on user data; encryption at rest.

## F. Business-model failures

### F16. Free core + no revenue (MED) 🟡
- **Mitigation:** Discharge Defender free (acquisition + impact); monetize ClaimBack full packet (pay-what-you-want, proven by US tools) + B2B (TPA/employer/NGO white-label). Grants (ACT/Omidyar/Mozilla) fund the OSS core.

### F17. Mission drift toward insurer-side money (LOW likelihood, HIGH mission impact) 🟡
- **Mitigation:** explicit rule — never build for the insurer/hospital side; conflict with the patient mission. Stay patient-aligned.

## Top 5 to fix FIRST (ranked)
1. **Re-sequence: lead with Discharge Defender, not ClaimBack** (A1 — Bima Buddy is racing the appeal niche).
2. **Deterministic deduction calculator + 12 golden scenarios as the hard gate** (B4/B6).
3. **Curated, date-verified IRDAI clause library + 0-fabrication post-check** (B7/C9).
4. **Conservative winnability + disclaimers** (B5/E13).
5. **BSP-compliant WhatsApp path before scale** (D11).

## Net verdict carried into the build
The FUSED product still has a genuine white space — but it has SHIFTED: the **Discharge Defender (pre-signature deduction shield) is the real, unoccupied wedge**; the **ClaimBack appeal generator is now contested** (Bima Buddy + incumbents). Build Defender-first, bolt ClaimBack on as a differentiated fast-follow, and let the deduction-math + WhatsApp + vernacular + free-core be the edge.
