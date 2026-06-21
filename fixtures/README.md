# Golden Fixtures — the P0 integrity canary

These fixtures are the **green-blocking gate** for the forge. They are labeled, hand-verified truth. The builder/agent may NOT edit anything in this folder. The verifier reads these; if the implementation's output drifts from the expected labels, the phase fails.

## Files
- `deduction-scenarios.json` — 12 proportionate-deduction scenarios with hand-computed expected rupee outputs. Tests `defender/proportionate_deduction` (pure deterministic code).
- `rejection-taxonomy.md` — the fixed rejection reason-code taxonomy + governing clause + default winnability. Tests `claimback/classify` and the winnability scorer.
- `rejection-samples.jsonl` — 15 labeled rejection-letter snippets → expected reason_code + winnability (you populate the raw text from real letters; labels given).

## Integrity rules
1. Builder/agent has NO write access here. Hash-pin this folder in `.forge/verifier_hashes.txt`.
2. The deduction calculator must match EVERY expected value EXACTLY (deterministic; any drift = fail).
3. The classifier must never score a `red` reason as `green`.
4. 0 fabricated citations: any clause id not in the curated library = fail.
5. Add real bills/letters over time; never let the model generate its own test labels.

## The proportionate-deduction formula (the one law the calculator encodes)
```
factor = min(1, room_rent_cap_per_day / actual_room_rent_per_day)

room_eligible          = min(actual_room_rent, cap) * days
variable_eligible      = sum(variable_charges) * factor          # nursing, surgeon, OT, consult, anaesthesia
fixed_eligible         = sum(fixed_charges)                      # medicines, implants, consumables, diagnostics (NOT proportionately cut)

total_eligible         = room_eligible + variable_eligible + fixed_eligible
total_bill             = room_charges + sum(variable_charges) + sum(fixed_charges)
room_excess            = room_charges - room_eligible            # the 'obvious' loss
proportionate_hit      = sum(variable_charges) - variable_eligible  # the 'hidden' shock
total_out_of_pocket    = total_bill - total_eligible             # before co-pay/deductible
```
NOTE (IRDAI 2024 direction): proportionate deduction should NOT apply to medicines, implants, consumables, and diagnostics whose price is independent of room category. The calculator treats those as `fixed_charges`. This is also a key ClaimBack argument when an insurer wrongly applies proportionate deduction to fixed items.
