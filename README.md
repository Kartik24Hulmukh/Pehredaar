# Pehredaar — Discharge Defender & ClaimBack

> **One line:** A guardian that protects an Indian patient's money at the two moments it actually gets destroyed — the **discharge desk** (proportionate deduction + non-payable trap, caught *before you sign*) and the **claim rejection** (an IRDAI-grounded appeal that fights back).

## What Pehredaar Does

### 🏥 Discharge Defender (the wedge)
Real-time, pre-signature analysis that catches:
- **Proportionate deduction exposure** — if your room exceeds the policy sub-limit, the insurer slashes your ENTIRE bill (surgery, ICU, doctor) proportionally. Pehredaar calculates the exact rupee loss BEFORE you sign.
- **Non-payable items** — flags items that shouldn't be billed separately per IRDAI Master Circular on Standardization (IRDAI/HLT/REG/CIR/193/07/2020): gloves, documentation charges, admission/registration charges, etc.
- **NPPA ceiling price breaches** — checks medicine MRP against NPPA ceiling prices (legally binding under DPCO 2013).
- **CGHS benchmark comparison** — compares procedure charges against CGHS rates (reference benchmark, not a legal cap).
- **"Before You Sign" sheet** — a 1-page advisory with a polite desk-query script, what to ask in writing, and your options.

### 📋 ClaimBack (the fast-follow)
AI-drafted, IRDAI-clause-grounded appeal letter for rejected/short-settled claims:
- **Rejection classifier** — maps the rejection letter to a 13-code taxonomy with governing IRDAI clause and winnability score (green/amber/red).
- **Conservative winnability scorer** — never over-promises. Red reasons stay red without explicit qualifying facts (e.g., moratorium crossed).
- **Appeal drafter** — generates a formal representation to the insurer's Grievance Redressal Officer, citing the EXACT IRDAI clause with verbatim text. Zero fabricated citations.
- **Escalation router** — insurer GRO (15 days) → IRDAI Bima Bharosa → Insurance Ombudsman (₹30 lakh limit, 1-year deadline) → Consumer Commission.

### 📚 Citation Library
Every flag and appeal carries a real citation from verified IRDAI/Government of India source documents:
- IRDAI Master Circular on Health Insurance Business 2024 (IRDAI/HLT/CIR/PRO/84/5/2024)
- IRDAI Circular on Proportionate Deductions 2020 (IRDAI/HLT/REG/CIR/151/06/2020)
- IRDAI Master Circular on Standardization 2020 (IRDAI/HLT/REG/CIR/193/07/2020)
- IRDAI PPI Regulations 2017
- Insurance Ombudsman Rules 2017
- IRDAI Condonation of Delay Circular 2011
- NPPA DPCO 2013 ceiling prices
- CGHS package rates

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the API server
python main.py

# Open the web interface
# http://localhost:8000/app

# API docs (Swagger)
# http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/app` | Web interface |
| GET | `/health` | Detailed health status |
| GET | `/policies` | List available policy plans |
| POST | `/defender/calculate` | Calculate proportionate deduction |
| POST | `/defender/analyze` | Full bill analysis (deduction + non-payable + price check + sheet) |
| POST | `/defender/before-you-sign` | Generate Before You Sign sheet |
| POST | `/claimback/classify` | Classify a rejection letter |
| POST | `/claimback/draft-appeal` | Draft an appeal letter |
| POST | `/claimback/analyze` | Full ClaimBack analysis (classify + draft + route) |
| GET | `/claimback/escalation` | Get escalation route |
| GET | `/claimback/ombudsman` | Get Ombudsman jurisdiction |
| GET | `/claimback/deadline` | Calculate Ombudsman filing deadline |
| POST | `/ingest/bill` | Upload and parse a bill (image/PDF) |
| GET | `/citations` | List all clause library citations |
| POST | `/citations/validate` | Validate citation ids (0-fabrication guardrail) |
| POST | `/card/defender` | Generate Receipt of Justice card (Defender) |
| POST | `/card/claimback` | Generate Receipt of Justice card (ClaimBack) |

## Testing

```bash
# Run all tests (26 tests: golden fixtures + integration)
python -m pytest tests/ -v
```

### Test Coverage
- **P3 Deduction Calculator**: 12/12 golden scenarios match EXACTLY (deterministic math)
- **P5 Rejection Classifier**: 15/15 golden samples match (reason_code + winnability + clause)
- **P4 Before You Sign**: Sheet generation with all sections, desk script, WhatsApp format
- **P6 Appeal Drafter + Router**: All reason codes, IRDAI citations, ₹30 lakh Ombudsman limit
- **Integration**: End-to-end Defender + ClaimBack workflows, PII redaction, NPPA/CGHS checks

## Architecture

```
pehredaar/
├── main.py                          # FastAPI application with all endpoints
├── web/                             # Web interface (HTML + CSS + JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── src/
│   ├── citations/
│   │   └── clause_library.py        # Curated IRDAI clause library (19 clauses, all verified)
│   ├── core/
│   │   └── pii_redaction.py         # PII redaction (DPDP Act 2023 compliant)
│   ├── ingest/
│   │   └── bill_to_json.py          # Bill OCR → JSON (PDF + image)
│   ├── rules/
│   │   ├── non_payable_detector.py  # IRDAI non-payable item detection (4 lists, 146 items)
│   │   └── price_check_engine.py    # NPPA ceiling + CGHS benchmark checks
│   ├── defender/
│   │   ├── proportionate_deduction.py  # Pure deterministic deduction calculator
│   │   ├── policy_parser.py         # 20-plan policy lookup + uploaded schedule parser
│   │   └── before_you_sign.py       # Before You Sign sheet + desk script generator
│   ├── claimback/
│   │   ├── classify.py              # Rejection classifier + winnability scorer
│   │   ├── draft_appeal.py          # IRDAI-grounded appeal letter drafter
│   │   └── router.py                # Escalation router (GRO → Bima Bharosa → Ombudsman)
│   └── channels/
│       └── receipt_of_justice.py    # Shareable outcome card generator
├── fixtures/                        # Golden test data (DO NOT EDIT)
│   ├── deduction-scenarios.json     # 12 hand-computed deduction scenarios
│   ├── rejection-samples.jsonl      # 15 labeled rejection samples
│   └── rejection-taxonomy.md        # 13-code rejection taxonomy
└── tests/                           # 26 tests (all passing)
    ├── test_p3_deduction.py
    ├── test_p4_p6.py
    ├── test_p5_classifier.py
    └── test_integration.py
```

## Key Design Principles (the Five Laws)

1. **Deterministic where law/math decides** — deduction calc, ceiling checks, non-payable match are pure code, NO model.
2. **AI only for reading bills/policies and explaining** — it cannot invent a citation.
3. **Golden fixtures are the green-blocking gate** — 12 deduction scenarios + 15 rejection samples must match EXACTLY.
4. **Honesty: every flag carries a source** — weak coverage is labeled, never bluffed.
5. **Tone: "possible error, please review"** — never "fraud" or "the hospital cheated you."

## Legal Compliance

- **CGHS is a reference benchmark, NOT a legal price cap** — never assert a CGHS-based "overcharge" as illegal.
- **Medicine MRP is legally binding** (Legal Metrology Act 2009) — NPPA ceiling caps the MRP (DPCO 2013).
- **Not insurance advice** — Pehredaar is an information + document-drafting tool, not an IRDAI-regulated intermediary.
- **DPDP Act 2023** — PII redacted pre-model, no training on user data.
- **Insurance Ombudsman limit is ₹30 lakh** (NOT ₹50 lakh) per Insurance Ombudsman Rules 2017, Rule 17(3)(ii).

## License

Open source. See repository for details.