# Pehredaar — Final Package (v2: Discharge Defender + ClaimBack)

The guardian that protects an Indian patient's money at the two moments it actually gets destroyed: the **discharge desk** (proportionate-deduction shield, caught *before you sign*) and the **claim rejection** (an IRDAI-grounded appeal). Built to run through your 1000x forge factory.

## Final decision (post deep-research + premortem)
**Build Discharge Defender FIRST** — it is the genuinely unoccupied wedge. The post-hoc bill-audit lane is taken (Jaanch/Evaakil/NYVO + govt apps + ChatGPT), and the **claim-appeal lane is now contested** in India (Bima Buddy indie launch May 2026 + SureClaim/ClaimBuddy). So:
- **Discharge Defender = the wedge** (real-time, pre-signature, bill-aware proportionate-deduction + non-payable shield). No product does this today.
- **ClaimBack = differentiated fast-follow** (its edge over rivals: exact deduction-math feeding the appeal + WhatsApp + vernacular + free core).
- Edge/moat: WhatsApp-native + vernacular + the compounding policy/IRDAI-clause library + open-source price-DB & rules engine + the shareable “Receipt of Justice” growth loop.

## Read in this order
1. **README.md** (this file) — decision + map.
2. **SETUP.md** — initialize the forge + env + scaffold + gates + production checklist. **Start here to build.**
3. **SPEC.md** — scope, journeys, functional/non-functional reqs, legal guardrails.
4. **STRATEGY.md** — positioning, moat, GTM, growth loop, monetization.
5. **BUILD-PLAN.md** — P0→P7 phases, gates, drop-in Antigravity prompts, timeline.
6. **PREMORTEM.md** — 17 failure modes + mitigations + the “fix-first” five.
7. **fixtures/** — the P0 golden canary:
   - `README.md` (integrity rules + the deduction formula)
   - `deduction-scenarios.json` (12 hand-computed scenarios)
   - `rejection-taxonomy.md` (13 reason codes + winnability + escalation)
   - `rejection-samples.jsonl` (15 labeled samples; paste real letters)

## Two manual steps before you build (from SETUP §5)
1. Replace every `§x` clause placeholder with the verified IRDAI section; put verified text in `src/citations/`.
2. Paste ~15 real (PII-stripped) rejection letters into `rejection-samples.jsonl` (labels already provided).

Then: run `acceptance_v3.ps1` on the empty scaffold (expect 6/6), point Antigravity at the repo, and start P0 → P1 → P2 → **P3 (Defender)**.
