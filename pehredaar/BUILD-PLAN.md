# Pehredaar — Build Plan (v2: Discharge Defender + ClaimBack)

> Built for your 1000x forge factory: Antigravity drives, deterministic verifier gates every phase, builder NEVER writes the verifier. ~60% reuses the v1 bill-audit core.

## 0. Operating rules (the Five Laws, restated)
1. Deterministic where law/math decides (deduction calc, ceiling, non-payable match) — NO model.
2. AI only for reading bills/policies and explaining — it cannot invent a citation.
3. Builder/agent has NO write access to the verifier. Verifier hashes pinned.
4. Golden labeled test set is a green-blocking gate (the P0 canary).
5. Honesty: every flag carries a source; weak coverage is labeled, never bluffed.

## 1. Phase map
| Phase | Goal | Green-blocking gate |
|---|---|---|
| P0 | Repo + verifier baseline + golden fixtures | acceptance_v3 6 checks pass on empty scaffold |
| P1 | Shared core: bill OCR→JSON + PII redaction | 20 golden bills parse at ≥ target field precision |
| P2 | Rule engine: NPPA/CGHS/non-payable (reused) | flags match labeled expected set, 0 fabricated citations |
| P3 | **Discharge Defender**: policy parse + deduction calc | deduction math matches hand-computed golden set exactly |
| P4 | "Before You Sign" sheet + desk script | output sheet matches golden template; latency < 30s |
| P5 | **ClaimBack**: rejection classifier + winnability | classifier matches labeled rejections; scorer conservative |
| P6 | Appeal drafter + escalation router (grounded) | every draft cites only library clauses; route correct |
| P7 | WhatsApp + vernacular + Receipt-of-Justice card | end-to-end on real device; PII purge verified |

## 2. P0 — Initialization (do this first)
1. **Env / models** (Bedrock, from prior setup):
   - `AWS_REGION=us-east-1`
   - `BEDROCK_MODEL_ID_ARCH=us.anthropic.claude-opus-4-6-v1`
   - `BEDROCK_MODEL_ID_BUILD=us.anthropic.claude-sonnet-4-5-20250929-v1:0` (vision: bill/policy read)
   - `BEDROCK_MODEL_ID_FAST=us.anthropic.claude-haiku-4-5-20251001-v1:0`
   - Mid/open-source model via OpenRouter for explainer + appeal drafting (cost control).
2. **Scaffold:** FastAPI + SQLite (→ Postgres later). Modules: `ingest/`, `rules/`, `defender/`, `claimback/`, `channels/`, `verifier/` (read-only to builder).
3. **Verifier baseline:** copy acceptance_v3.ps1 (SHA pinned), write `.forge/verifier_hashes.txt`, confirm 6 checks (verifier.integrity, helicone.real, mutation.stack, openhands.real, repo.pristine, slice.real) pass on empty scaffold.
4. **Golden fixtures (the canary):** drop labeled test data BEFORE building logic:
   - 20 real itemised bills → expected line JSON + expected flags.
   - 15 policy schedules → expected room cap / sub-limits.
   - 12 deduction scenarios → hand-computed expected rupee loss.
   - 15 rejection letters → expected reason_code + winnability.
5. **Mutation wiring:** Stryker (TS) / cargo-mutants (Rust) per your stack so a stubbed matcher fails the mutation gate.

## 3. Reuse from v1 (do not rebuild)
- Bill OCR→JSON pipeline, PII redaction, NPPA/CGHS/IRDAI rule engine, citation engine, medicine normalization (brand→generic, RapidFuzz + NER + embeddings), price DB import (NPPA + 1mg/India Drug Bank).

## 4. New build (the wedge)
- **Discharge Defender (P3-P4):** policy parser, deterministic proportionate-deduction calculator (transparent formula), non-payable detector, "Before You Sign" sheet + desk-query script.
- **ClaimBack (P5-P6):** rejection classifier, conservative winnability scorer, grounded appeal drafter, escalation router (insurer → IRDAI Bima Bharosa → Ombudsman with deadlines/jurisdiction).
- **Channels (P7):** WhatsApp (BSP-compliant; OpenWA only for prototype), Hindi-first vernacular, Receipt-of-Justice card generator.

## 5. Golden-set acceptance (the integrity gate)
- Deduction calculator must match all 12 hand-computed scenarios EXACTLY (deterministic; any drift = fail).
- Rule-engine flags must match labeled expected set; **0 fabricated citations** (post-check rejects any unsourced citation).
- Winnability scorer must never score a known-weak rejection as green.
- Builder cannot edit fixtures or verifier; mutation gate catches stubs.

## 6. Prompts (drop-in for Antigravity)

### P1 — Bill ingestion
> "Implement `ingest/bill_to_json`. Input: image/PDF of an itemised Indian hospital bill. Use the vision model to extract line items into the canonical schema (canonical_name, qty, unit_price, amount, raw_text). Redact PII before any model call. Do NOT infer prices or fill gaps — extract only what is printed; mark unreadable fields null with low-confidence flag. Must pass the 20 golden-bill precision fixtures. You may not modify anything under verifier/ or fixtures/."

### P3 — Proportionate-deduction calculator
> "Implement `defender/proportionate_deduction` as PURE deterministic code (no model). Inputs: room_cap (abs ₹ or % of SI), actual_room_rent, eligible_associated_charges, sum_insured. Compute proportionate factor and rupee exposure using the standard IRDAI proportionate formula; expose every intermediate number. Must match all 12 hand-computed golden scenarios exactly. No network, no model calls. You may not edit fixtures or verifier."

### P5 — Rejection classifier + winnability
> "Implement `claimback/classify`. Input: rejection/short-settlement letter text. Output: reason_code from the fixed taxonomy + governing IRDAI clause id from the curated library + winnability (green/amber/red) + plain rationale. Be conservative: never mark a known-weak reason green. Cite ONLY clause ids that exist in the library; a post-check must reject any unknown citation. Must match the 15 labeled rejection fixtures."

### P6 — Appeal drafter
> "Implement `claimback/draft_appeal`. Input: classified rejection + policy + bills. Output: a representation letter to the insurer grievance cell citing the exact library clause, plus the escalation route (insurer 15d → IRDAI Bima Bharosa → Ombudsman with jurisdiction + deadlines). The model may cite ONLY from the clause library; reject drafts containing any unsourced citation. Tone: factual, never 'fraud'. Include the mandatory not-legal-advice disclaimer."

## 7. Timeline (realistic)
- P0-P1: ~2-3 days (scaffold + reuse wiring + fixtures).
- P2-P3: ~3 days (rules reuse + deduction engine + golden match).
- P4: ~1-2 days (sheet + script).
- P5-P6: ~3 days (claim classifier + drafter + routing).
- P7: ~2 days (WhatsApp + vernacular + card).
- **~11-13 working days** to a real, gated, end-to-end v1. Don't compress the golden-set gates — they are the whole point.

## 8. Premortem (what kills this; pre-fixed)
1. Agent stubs deduction calc → mutation + golden gate fails. ✅
2. Over-promised winnability → conservative scorer + amber/red defaults + disclaimer. ✅
3. Messy policy data → top-20 plan lookup + uploaded-schedule parse + labeled estimates. ✅
4. OCR errors → confidence threshold + user line-confirmation step. ✅
5. Fabricated citations → library-only constraint + post-check rejection. ✅
6. WhatsApp bans → BSP-compliant path; OpenWA prototype only. ✅
7. Incumbent copies wedge → speed + distribution + compounding clause/policy asset + OSS credibility. ✅
