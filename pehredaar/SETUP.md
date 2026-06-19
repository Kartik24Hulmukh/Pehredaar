# Pehredaar — Setup & Initialization Guide
## (How to stand up the 1000x forge for this project and ship end-to-end, production-ready)

This is the step-by-step to go from empty machine → a gated forge that lets Antigravity build Pehredaar (Discharge Defender first, ClaimBack fast-follow) with every phase verified. Follow in order. Do NOT skip the gates — they are the whole reason the output is production-ready instead of a demo.

---

## 0. Mental model (read once)
- **You** drive Antigravity (Gemini 3 Flash / Sonnet) as the cheap “hands.”
- **Opus 4.6 (Bedrock)** is the expensive “architect/adjudicator” — used sparingly. The SPEC/STRATEGY/BUILD-PLAN you already have mean you do NOT spend Opus on brainstorming.
- **An open-source mid model (via OpenRouter)** does bulk explain/draft work to control cost.
- **The forge verifier** is the referee. The builder NEVER writes the verifier. Golden fixtures are the green-blocking gate.
- **Five Laws** (restated in BUILD-PLAN): deterministic where law/math decides; AI only reads & explains; builder has no verifier write access; golden set blocks merges; honesty (every flag cited, weak coverage labeled).

---

## 1. Prerequisites (Windows host)
```powershell
# from PowerShell (winget)
winget install Git.Git
winget install Microsoft.WSL          # then: wsl --install -d Ubuntu
winget install Amazon.AWSCLI
winget install astral-sh.uv           # Python env/runner
winget install OpenJS.NodeJS.LTS      # node 20+/24
```
Inside **WSL Ubuntu** (where the repo is synced at `/root/test-env`):
```bash
sudo apt update && sudo apt install -y build-essential python3-pip jq ripgrep
curl -LsSf https://astral.sh/uv/install.sh | sh
# node via nvm if you prefer parity with host
```
**Sanity check:** `git --version`, `aws --version`, `uv --version`, `node -v` all return.

---

## 2. AWS Bedrock model access (already resolved — just wire it)
Account `921040036979`, region `us-east-1`. Confirmed-entitled model IDs:

Create `/root/test-env/pehredaar/.env`:
```ini
AWS_REGION=us-east-1
# Architect / hard adjudication (use sparingly)
BEDROCK_MODEL_ID_ARCH=us.anthropic.claude-opus-4-6-v1
# Builder + VISION (reads bills/policy images → JSON)
BEDROCK_MODEL_ID_BUILD=us.anthropic.claude-sonnet-4-5-20250929-v1:0
# Fast/cheap classify + short tasks
BEDROCK_MODEL_ID_FAST=us.anthropic.claude-haiku-4-5-20251001-v1:0
# Mid open-source model for bulk explain/draft (cost control)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct   # or your chosen OSS model
```
**Verify true entitlement** (do NOT trust the Playground “Open in Playground” — it drops the `us.` profile and gives a misleading AccessDenied). Use CloudShell / CLI:
```bash
aws bedrock-runtime converse --region us-east-1 \
  --model-id us.anthropic.claude-opus-4-6-v1 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]'
```
If this returns text, the architect model works. Repeat for BUILD and FAST ids.
> Gated (new-account version gating, NOT a config error): Opus 4.7 / 4.8 / Fable 5. Swap `BEDROCK_MODEL_ID_ARCH` to 4.8 only after AWS enables it. $200 Bedrock credits ≠ a direct Anthropic API key.

---

## 3. Scaffold the project repo
```
pehredaar/
  .env                      # (above; gitignored)
  .forge/
    verifier_hashes.txt     # pinned hashes of verifier + fixtures
    acceptance_v3.ps1       # the 6-check gate (SHA-pinned)
  fixtures/                 # GOLDEN — builder has NO write access
    README.md
    deduction-scenarios.json
    rejection-taxonomy.md
    rejection-samples.jsonl
  src/
    ingest/                 # bill/policy image → JSON (vision), PII redaction
    rules/                  # NPPA/CGHS/IRDAI non-payable engine (reused)
    defender/               # P3-P4: proportionate-deduction calc (PURE code)
    claimback/              # P5-P6: rejection classify + winnability + appeal
    channels/               # P7: WhatsApp (BSP) + web + vernacular + card
    citations/              # curated clause library (IRDAI § verified)
  verifier/                 # read-only to builder; mutation + golden checks
  tests/
  app.py                    # FastAPI entrypoint
```
Quick start:
```bash
cd /root/test-env/pehredaar
uv init && uv add fastapi uvicorn pydantic rapidfuzz sentence-transformers \
  pillow pdfplumber pytesseract sqlite-utils python-dotenv
mkdir -p src/{ingest,rules,defender,claimback,channels,citations} verifier tests fixtures .forge
```

---

## 4. Install the forge verifier baseline (P0)
1. Copy `acceptance_v3.ps1` into `.forge/` and pin its SHA in `verifier_hashes.txt`.
   - Reference SHA: `2399e649b2bef39bc13c13f815c2963960540e0b4b7d687fd15c0af55852578f` (branch `integrate/devbox-fable`, commit `459c075`).
2. The 6 checks that must pass: `verifier.integrity`, `helicone.real`, `mutation.stack`, `openhands.real`, `repo.pristine`, `slice.real`.
3. Hash-pin the `fixtures/` folder too — so the builder can’t silently edit the golden set.
4. **Wire mutation testing** per stack so a stubbed matcher fails: Stryker (TS) or `cargo-mutants` (Rust); for Python use `mutmut` or `cosmic-ray`.
5. Run the gate on the EMPTY scaffold — all 6 must pass before any feature code.
```powershell
pwsh ./.forge/acceptance_v3.ps1   # expect: 6/6 green on empty scaffold
```

---

## 5. Drop in the golden fixtures (the canary) — BEFORE logic
The `fixtures/` files are already written for you. Two manual steps make them “live”:
1. **Verify clause ids:** in `rejection-taxonomy.md` and `rejection-samples.jsonl`, replace each `§x` placeholder with the exact verified IRDAI Master Circular 2024 / PPI 2017 / Ombudsman Rules section. Put the verified text in `src/citations/`. (The model may cite ONLY ids that exist there.)
2. **Paste real letters:** fill the `<PASTE ...>` raw_text in `rejection-samples.jsonl` with ~15 real (PII-stripped) rejection letters. Keep the provided expected labels.
The deduction scenarios are already fully computed — nothing to fill.

---

## 6. Point Antigravity at the project
- Open the repo in Antigravity; set the system/context to load `SPEC.md`, `BUILD-PLAN.md`, and `fixtures/README.md`.
- Give it the **phase prompts** from BUILD-PLAN §6, one phase at a time.
- Hard rule in the agent’s instructions: *“You may not modify anything under `verifier/`, `.forge/`, or `fixtures/`. Every phase must pass `acceptance_v3.ps1` and the golden gate before you proceed.”*

---

## 7. Build order (Defender-first — the updated sequence)
| Phase | Build | Gate to pass |
|---|---|---|
| P0 | scaffold + verifier baseline + fixtures | 6/6 acceptance on empty repo |
| P1 | `ingest`: bill/policy → JSON + PII redaction | 20 golden bills ≥ precision target |
| P2 | `rules`: NPPA/CGHS/non-payable (reused) | flags match labels, 0 fabricated citations |
| **P3** | **`defender`: proportionate-deduction calc (PURE code)** | **all 12 scenarios match EXACTLY** |
| **P4** | **“Before You Sign” sheet + desk script** | golden template match, < 30s latency |
| P5 | `claimback`: rejection classify + winnability | matches 15 labeled samples; never red→green |
| P6 | `claimback`: grounded appeal + escalation router | library-only citations; correct route/deadlines |
| P7 | `channels`: WhatsApp (BSP) + vernacular + card | end-to-end on real device; PII purge verified |

> Why Defender-first: the premortem found ClaimBack now has a live India clone (Bima Buddy) — the deduction shield is the unoccupied wedge. Ship it first.

---

## 8. Production-readiness checklist (the “end-to-end, fully functional” bar)
A phase is NOT “done” until ALL of these hold:
- [ ] Green on `acceptance_v3.ps1` (6/6) AND the golden gate.
- [ ] Mutation score above threshold (no stubbed matchers survive).
- [ ] Deterministic calc matches fixtures exactly; no model in the math path.
- [ ] 0 fabricated citations (post-check passes on a fuzz set).
- [ ] PII redaction verified on real docs; 30-day purge job runs; nothing logged in clear.
- [ ] Latency budget met (Defender first response < 30s).
- [ ] 24/7 path: VPS + queue + idempotency keys; restart-safe.
- [ ] WhatsApp on a compliant BSP (OpenWA only in dev); web fallback works.
- [ ] Disclaimers present (not legal/insurance advice); tone never says “fraud.”
- [ ] Observability: request tracing (Helicone), error alerting, golden-set regression in CI.
- [ ] Rollback: pinned verifier hashes; CI blocks merge on any gate failure.

---

## 9. Daily loop (how you actually operate the factory)
1. Pick the next phase → paste its prompt into Antigravity.
2. Let it build; it runs the verifier locally.
3. If red → it iterates (it cannot touch verifier/fixtures).
4. If green → you review the diff, run `acceptance_v3.ps1`, merge.
5. Escalate to Opus 4.6 ONLY for a genuinely hard design/adjudication call.
6. Repeat. Each green phase is a real, shippable slice — not a mock.

---

## 10. First commands to run right now
```bash
# 1) clone/sync repo in WSL
cd /root/test-env && mkdir -p pehredaar && cd pehredaar
# 2) drop in the files from this package (SPEC/STRATEGY/BUILD-PLAN/PREMORTEM/fixtures/SETUP)
# 3) create .env (section 2) and verify Bedrock
aws bedrock-runtime converse --region us-east-1 --model-id us.anthropic.claude-opus-4-6-v1 --messages '[{"role":"user","content":[{"text":"ping"}]}]'
# 4) scaffold (section 3) + install verifier baseline (section 4)
# 5) run the empty-repo gate
pwsh ./.forge/acceptance_v3.ps1
# 6) point Antigravity at the repo, start P0 → P1 → P2 → P3 ...
```
When P0 is 6/6 green and the fixtures are live (clauses verified + letters pasted), you are ready to build.
